#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [object]$Illustrator,
    [Parameter(Mandatory = $true)] [string]$AiPath,
    [Parameter(Mandatory = $true)] [string]$SvgPath,
    [Parameter(Mandatory = $true)] [string]$PngPath,
    [Parameter(Mandatory = $true)] [string]$OutputReport,
    # Number of explicitly requested raster panels; 0 keeps the pure-vector contract.
    [ValidateRange(0, 10000)] [int]$ExpectedRasterCount = 0
)

$ErrorActionPreference = 'Stop'
$aiFile = (Resolve-Path -LiteralPath $AiPath).Path
$svgFile = (Resolve-Path -LiteralPath $SvgPath).Path
$pngFile = (Resolve-Path -LiteralPath $PngPath).Path
$reportFile = [IO.Path]::GetFullPath($OutputReport)
$issues = [Collections.Generic.List[string]]::new()

[xml]$svg = Get-Content -LiteralPath $svgFile -Raw -Encoding UTF8
$svgRoot = $svg.DocumentElement
$viewBoxValues = @([regex]::Matches([string]$svgRoot.GetAttribute('viewBox'), '[-+]?(?:\d*\.\d+|\d+)') | ForEach-Object {
    [double]::Parse($_.Value, [Globalization.CultureInfo]::InvariantCulture)
})
if ($viewBoxValues.Count -ne 4) { $issues.Add('SVG_VIEWBOX_INVALID') }
$svgWidth = if ($viewBoxValues.Count -eq 4) { $viewBoxValues[2] } else { 0.0 }
$svgHeight = if ($viewBoxValues.Count -eq 4) { $viewBoxValues[3] } else { 0.0 }
$svgTextNodes = @($svg.SelectNodes("//*[local-name()='text']"))
$svgImageNodes = @($svg.SelectNodes("//*[local-name()='image']"))
if ($svgTextNodes.Count -lt 1) { $issues.Add('SVG_HAS_NO_LIVE_TEXT') }
if ($ExpectedRasterCount -eq 0 -and $svgImageNodes.Count -ne 0) { $issues.Add('SVG_CONTAINS_RASTER_IMAGE') }
if ($ExpectedRasterCount -gt 0) {
    if ($svgImageNodes.Count -ne $ExpectedRasterCount) { $issues.Add("SVG_RASTER_COUNT_MISMATCH:$($svgImageNodes.Count):$ExpectedRasterCount") }
    foreach ($imageNode in $svgImageNodes) {
        $href = [string]$imageNode.GetAttribute('href')
        if (-not $href) { $href = [string]$imageNode.GetAttribute('href', 'http://www.w3.org/1999/xlink') }
        if (-not $href.StartsWith('data:image/')) { $issues.Add('SVG_RASTER_NOT_EMBEDDED') }
    }
}
if ((Get-Content -LiteralPath $svgFile -Raw -Encoding UTF8).Contains([char]0xFFFD)) { $issues.Add('SVG_CONTAINS_REPLACEMENT_CHARACTER') }
# Text must be real font text: embedded <font>/<glyph> outlines are anchor-point
# vector shapes, not fonts, and are never an acceptable delivery form.
$svgGlyphNodes = @($svg.SelectNodes("//*[local-name()='font' or local-name()='glyph' or local-name()='font-face']"))
if ($svgGlyphNodes.Count -gt 0) { $issues.Add("SVG_EMBEDS_GLYPH_OUTLINES:$($svgGlyphNodes.Count)") }

Add-Type -AssemblyName System.Drawing
$bitmap = [Drawing.Bitmap]::FromFile($pngFile)
try {
    $pngWidth = [int]$bitmap.Width
    $pngHeight = [int]$bitmap.Height
    $nonWhite = $false
    for ($x = 0; $x -lt $pngWidth -and -not $nonWhite; $x += 2) {
        for ($y = 0; $y -lt $pngHeight; $y += 2) {
            $pixel = $bitmap.GetPixel($x, $y)
            if ($pixel.R -lt 250 -or $pixel.G -lt 250 -or $pixel.B -lt 250) { $nonWhite = $true; break }
        }
    }
    if (-not $nonWhite) { $issues.Add('PNG_IS_BLANK') }
}
finally { $bitmap.Dispose() }

$originalDocument = $Illustrator.ActiveDocument
$openedDocument = $null
try {
    $openedDocument = $Illustrator.Open($aiFile)
    $documentNameJson = ([string]$openedDocument.Name | ConvertTo-Json -Compress)
    $inspection = [string]$Illustrator.DoJavaScript(@"
(function(){
  var name=$documentNameJson,d=null;
  for(var i=0;i<app.documents.length;i++){if(app.documents[i].name===name){d=app.documents[i];break;}}
  if(d===null)return 'ERROR|AI_NOT_OPEN';
  var a=d.artboards[0].artboardRect,text=[];
  for(var t=0;t<d.textFrames.length;t++)text.push(encodeURIComponent(String(d.textFrames[t].contents)));
  return ['OK',d.artboards.length,a[2]-a[0],a[1]-a[3],d.textFrames.length,d.rasterItems.length,d.placedItems.length,text.join('~')].join('|');
}());
"@)
    if (-not $inspection.StartsWith('OK|')) { $issues.Add($inspection) }
    else {
        $parts = $inspection -split '\|', 8
        $aiArtboards = [int]$parts[1]
        $aiWidth = [double]::Parse($parts[2], [Globalization.CultureInfo]::InvariantCulture)
        $aiHeight = [double]::Parse($parts[3], [Globalization.CultureInfo]::InvariantCulture)
        $aiTextCount = [int]$parts[4]
        $aiRasterCount = [int]$parts[5]
        $aiPlacedCount = [int]$parts[6]
        $aiTexts = if ($parts.Count -ge 8 -and $parts[7]) {
            @($parts[7] -split '~' | ForEach-Object { ([regex]::Replace([Uri]::UnescapeDataString($_), '\s+', ' ')).Trim() } | Sort-Object)
        } else { @() }
        if ($aiArtboards -ne 1) { $issues.Add("AI_ARTBOARD_COUNT:$aiArtboards") }
        if ($aiPlacedCount -ne 0) { $issues.Add("AI_CONTAINS_LINKED_PLACED:$aiPlacedCount") }
        if ($aiRasterCount -ne $ExpectedRasterCount) {
            $code = if ($ExpectedRasterCount -eq 0) { 'AI_CONTAINS_RASTER_OR_PLACED' } else { 'AI_RASTER_COUNT_MISMATCH' }
            $issues.Add("${code}:${aiRasterCount}:$ExpectedRasterCount")
        }
        if ($aiTextCount -ne $svgTextNodes.Count) { $issues.Add("TEXT_COUNT_MISMATCH:${aiTextCount}:$($svgTextNodes.Count)") }
        $svgTexts = @($svgTextNodes | ForEach-Object {
            $elementChildren = @($_.ChildNodes | Where-Object { $_.NodeType -eq [Xml.XmlNodeType]::Element })
            $rawText = if ($elementChildren.Count -gt 1) { ($elementChildren | ForEach-Object { $_.InnerText }) -join ' ' } else { [string]$_.InnerText }
            ([regex]::Replace($rawText, '\s+', ' ')).Trim()
        } | Sort-Object)
        if (($aiTexts -join "`n") -ne ($svgTexts -join "`n")) { $issues.Add('TEXT_CONTENT_MISMATCH') }
        if ([Math]::Abs($aiWidth - $svgWidth) -gt 0.51 -or [Math]::Abs($aiHeight - $svgHeight) -gt 0.51) { $issues.Add('AI_SVG_CANVAS_MISMATCH') }
        if ([Math]::Abs($pngWidth - $svgWidth) -gt 1.0 -or [Math]::Abs($pngHeight - $svgHeight) -gt 1.0) { $issues.Add('PNG_SVG_CANVAS_MISMATCH') }
    }
}
finally {
    if ($null -ne $openedDocument) { try { $openedDocument.Close(2) } catch { } }
    try { $originalDocument.Activate() } catch { }
}

# Reopen the exported SVG in Illustrator and compare its rasterization with the
# PNG exported from the canonical AI document. Small antialiasing differences
# are expected; structural or font-layout drift is not.
$svgRenderPath = Join-Path ([IO.Path]::GetTempPath()) ("medfig-illustrator-svg-render-" + [Guid]::NewGuid().ToString('N') + '.png')
$svgDocument = $null
$svgRenderMeanDifference = $null
try {
    $svgDocument = $Illustrator.Open($svgFile)
    $renderPathJson = (($svgRenderPath -replace '\\', '/') | ConvertTo-Json -Compress)
    $renderResult = [string]$Illustrator.DoJavaScript(@"
(function(){var d=app.activeDocument,o=new ExportOptionsPNG24();o.antiAliasing=true;o.transparency=false;o.artBoardClipping=true;o.horizontalScale=100;o.verticalScale=100;d.exportFile(new File($renderPathJson),ExportType.PNG24,o);return 'OK';}());
"@)
    if ($renderResult -ne 'OK' -or -not (Test-Path -LiteralPath $svgRenderPath -PathType Leaf)) { $issues.Add('SVG_RENDER_FAILED') }
    else {
        $referenceBitmap = [Drawing.Bitmap]::FromFile($pngFile)
        $renderedBitmap = [Drawing.Bitmap]::FromFile($svgRenderPath)
        try {
            if ($referenceBitmap.Width -ne $renderedBitmap.Width -or $referenceBitmap.Height -ne $renderedBitmap.Height) {
                $issues.Add('SVG_RENDER_CANVAS_MISMATCH')
            } else {
                [double]$differenceSum = 0.0
                [long]$sampleCount = 0
                for ($x = 0; $x -lt $referenceBitmap.Width; $x += 2) {
                    for ($y = 0; $y -lt $referenceBitmap.Height; $y += 2) {
                        $first = $referenceBitmap.GetPixel($x, $y)
                        $second = $renderedBitmap.GetPixel($x, $y)
                        $differenceSum += [Math]::Abs([int]$first.R - [int]$second.R)
                        $differenceSum += [Math]::Abs([int]$first.G - [int]$second.G)
                        $differenceSum += [Math]::Abs([int]$first.B - [int]$second.B)
                        $sampleCount += 3
                    }
                }
                $svgRenderMeanDifference = if ($sampleCount -gt 0) { $differenceSum / $sampleCount } else { 255.0 }
                if ($svgRenderMeanDifference -gt 3.0) { $issues.Add("SVG_RENDER_DIFFERENCE:$svgRenderMeanDifference") }
            }
        }
        finally {
            $referenceBitmap.Dispose()
            $renderedBitmap.Dispose()
        }
    }
}
finally {
    if ($null -ne $svgDocument) { try { $svgDocument.Close(2) } catch { } }
    try { $originalDocument.Activate() } catch { }
    if (Test-Path -LiteralPath $svgRenderPath -PathType Leaf) { Remove-Item -LiteralPath $svgRenderPath -Force }
}

$status = if ($issues.Count -eq 0) { 'PASS' } else { 'FAIL' }
$report = [ordered]@{
    schema_version = '1.0'
    status = $status
    ai = $aiFile
    svg = $svgFile
    png = $pngFile
    ai_artboards = $aiArtboards
    ai_canvas = @($aiWidth, $aiHeight)
    svg_canvas = @($svgWidth, $svgHeight)
    png_canvas = @($pngWidth, $pngHeight)
    ai_text_count = $aiTextCount
    expected_raster_count = $ExpectedRasterCount
    ai_raster_count = $aiRasterCount
    svg_raster_count = $svgImageNodes.Count
    svg_text_count = $svgTextNodes.Count
    svg_glyph_outline_count = $svgGlyphNodes.Count
    svg_render_mean_difference = $svgRenderMeanDifference
    unresolved_count = $issues.Count
    issues = @($issues)
}
$reportDirectory = Split-Path -Parent $reportFile
if ($reportDirectory) { New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null }
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportFile -Encoding UTF8
Write-Output "BUNDLE_VERIFY|status=$status|texts=$aiTextCount|artboards=$aiArtboards|unresolved=$($issues.Count)|report=$reportFile"
if ($status -ne 'PASS') { exit 2 }
exit 0
