$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $skillRoot 'scripts\cell_lct_cached_runtime.jsx'
$verifyScript = Join-Path $skillRoot 'scripts\verify_delivery_bundle.ps1'
. (Join-Path $skillRoot 'scripts\illustrator_com.ps1')

$temporary = Join-Path ([IO.Path]::GetTempPath()) ("medfig-illustrator-bundle-test-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $temporary | Out-Null
$outputAi = Join-Path $temporary 'canonical.ai'
$outputSvg = Join-Path $temporary 'canonical.svg'
$outputPng = Join-Path $temporary 'canonical.png'
$reportPath = Join-Path $temporary 'bundle-report.json'
$app = $null
$rootName = $null
$opened = $null
$document = $null
$testDocumentCreated = $false
try {
    $app = Connect-RunningIllustrator
    if ([int]$app.Documents.Count -eq 0) {
        $document = $app.Documents.Add()
        $testDocumentCreated = $true
    }
    else {
        $document = $app.ActiveDocument
    }
    $originalDocumentName = [string]$document.Name
    $activeIndex = [int]$document.Artboards.GetActiveArtboardIndex()
    $rootName = 'CELL_LCT_BUNDLE_TEST_' + [Guid]::NewGuid().ToString('N')
    $rootJson = $rootName | ConvertTo-Json -Compress
    $setup = "(function(){var d=app.activeDocument,a=d.artboards[d.artboards.getActiveArtboardIndex()].artboardRect,r=d.groupItems.add();r.name=$rootJson;var b=r.pathItems.rectangle(a[1]-20,a[0]+20,120,50);b.filled=false;b.stroked=true;var t=r.textFrames.pointText([a[0]+40,a[1]-45]);t.contents='Canonical';t.textRange.characterAttributes.size=12;return 'OK';}());"
    if ([string]$app.DoJavaScript($setup) -ne 'OK') { throw 'SETUP_FAILED' }

    $configuration = [ordered]@{
        operation = 'exportBundle'
        targetDocumentName = $originalDocumentName
        rootGroupName = $rootName
        artboardIndex = $activeIndex
        outputAi = ($outputAi -replace '\\', '/')
        outputSvg = ($outputSvg -replace '\\', '/')
        outputPng = ($outputPng -replace '\\', '/')
    }
    $configJson = ConvertTo-Json $configuration -Compress -Depth 10
    $runtimeJson = (($runtimePath -replace '\\', '/') | ConvertTo-Json -Compress)
    $bootstrap = "var CELL_LCT_CACHED_CONFIG = $configJson; `$`.evalFile(new File($runtimeJson));"
    $result = [string]$app.DoJavaScript($bootstrap)
    if (-not $result.StartsWith('OK|')) { throw "EXPECTED_OK:$result" }
    foreach ($path in @($outputAi, $outputSvg, $outputPng)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "MISSING_OUTPUT:$path" }
    }
    if (-not (Test-Path -LiteralPath $verifyScript -PathType Leaf)) { throw 'BUNDLE_VERIFIER_MISSING' }
    $verifyOutput = & $verifyScript -Illustrator $app -AiPath $outputAi -SvgPath $outputSvg -PngPath $outputPng -OutputReport $reportPath
    if ($LASTEXITCODE -ne 0) {
        $detail = if (Test-Path -LiteralPath $reportPath) { Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 } else { [string]$verifyOutput }
        throw "BUNDLE_VERIFIER_FAILED:$detail"
    }
    $bundleReport = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $bundleReport.svg_render_mean_difference) { throw 'SVG_RENDER_COMPARISON_MISSING' }
    if ([double]$bundleReport.svg_render_mean_difference -gt 3.0) { throw "SVG_RENDER_DIFFERENCE:$($bundleReport.svg_render_mean_difference)" }
    Add-Type -AssemblyName System.Drawing
    $bitmap = [Drawing.Bitmap]::FromFile($outputPng)
    try {
        $nonWhite = $false
        for ($x = 0; $x -lt $bitmap.Width -and -not $nonWhite; $x += 4) {
            for ($y = 0; $y -lt $bitmap.Height; $y += 4) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.R -lt 250 -or $pixel.G -lt 250 -or $pixel.B -lt 250) { $nonWhite = $true; break }
            }
        }
        if (-not $nonWhite) { throw 'PNG_IS_BLANK' }
    }
    finally { $bitmap.Dispose() }
    [xml]$svg = Get-Content -LiteralPath $outputSvg -Raw -Encoding UTF8
    if ($svg.SelectNodes("//*[local-name()='image']").Count -ne 0) { throw 'SVG_CONTAINS_RASTER_IMAGE' }
    if ($svg.SelectNodes("//*[local-name()='text']").Count -lt 1) { throw 'SVG_HAS_NO_LIVE_TEXT' }
    $opened = $app.Open($outputAi)
    if ([int]$opened.Artboards.Count -ne 1) { throw "AI_ARTBOARD_COUNT:$($opened.Artboards.Count)" }
    $opened.Close(2)
    $opened = $null
    $document.Activate()
    'PASS|bundle=3|ai_artboards=1|svg_live_text=true'
}
finally {
    if ($null -ne $opened) { try { $opened.Close(2) } catch { } }
    if ($null -ne $rootName -and $null -ne $app) {
        try {
            $rootJson = $rootName | ConvertTo-Json -Compress
            [void]$app.DoJavaScript("(function(){var d=app.activeDocument;for(var i=d.groupItems.length-1;i>=0;i--){if(d.groupItems[i].name===$rootJson){d.groupItems[i].remove();}}return 'OK';}());")
        } catch { }
    }
    if ($testDocumentCreated -and $null -ne $document) { try { $document.Close(2) } catch { } }
    if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
    foreach ($path in @($outputAi, $outputSvg, $outputPng, $reportPath)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) { Remove-Item -LiteralPath $path -Force }
    }
    if (Test-Path -LiteralPath $temporary -PathType Container) { Remove-Item -LiteralPath $temporary -Force }
}
