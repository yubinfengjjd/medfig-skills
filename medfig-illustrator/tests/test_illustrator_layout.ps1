$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $skillRoot 'scripts\resolve_python.ps1')
$auditScript = Join-Path $skillRoot 'scripts\audit_illustrator_layout.ps1'
if (-not (Test-Path -LiteralPath $auditScript -PathType Leaf)) {
    throw 'EXPECTED_FAIL: Illustrator layout auditor is missing.'
}

. (Join-Path $skillRoot 'scripts\illustrator_com.ps1')
$temporary = Join-Path ([IO.Path]::GetTempPath()) ("medfig-illustrator-layout-test-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $temporary | Out-Null
$approvedSvg = Join-Path $temporary 'approved.svg'
$cacheDir = Join-Path $temporary 'cache'
$reportPath = Join-Path $temporary 'postflight.json'
$svg = @'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect id="box" x="10" y="10" width="100" height="70" fill="#eeeeee" data-collision-role="container"/>
  <text id="label" x="60" y="35" text-anchor="middle" font-family="Arial" font-size="16" font-weight="700"
        data-container-id="box" data-collision-role="text">Target</text>
  <text id="subtitle" x="60" y="58" text-anchor="middle" font-family="Arial" font-size="12"
        data-container-id="box" data-collision-role="text">Encoder</text>
  <rect id="safe-box" x="120" y="55" width="75" height="40" fill="#ffffff" fill-opacity="0.001"
        data-collision-role="container"/>
  <text id="free-label" x="157.5" y="80" text-anchor="middle" font-family="Arial" font-size="12"
        data-container-id="safe-box" data-collision-role="text">Classifier</text>
  <line id="free-label-connector" x1="120" y1="75" x2="195" y2="75"
        stroke="#111111" data-collision-role="connector"/>
</svg>
'@
[IO.File]::WriteAllText($approvedSvg, $svg, [Text.UTF8Encoding]::new($false))
& py -3 -X utf8 (Join-Path $skillRoot 'scripts\prepare_geometry_cache.py') --input $approvedSvg --output-dir $cacheDir --job-id layout_test | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the test cache.' }

$app = $null
$root = $null
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
    $root = $document.GroupItems.Add()
    $root.Name = 'CELL_LCT_LAYOUT_TEST_' + [Guid]::NewGuid().ToString('N')
    $box = $root.PathItems.Rectangle(500, 100, 100, 70)
    $box.Name = 'CELL_LCT_CACHE_ATOM_000000'
    $box.Filled = $false
    $box.Stroked = $true
    $label = $root.TextFrames.PointText(@(150, 480))
    $label.Name = 'CELL_LCT_CACHE_ATOM_000001'
    # Simulate an earlier preflight that inserted an unnecessary hard line
    # break. The native audit must restore the approved one-line content.
    $label.Contents = "Tar`rget"
    $label.TextRange.CharacterAttributes.Size = 24
    $label.TextRange.CharacterAttributes.TextFont = $app.TextFonts.GetByName('Arial-Black')
    $subtitle = $root.TextFrames.PointText(@(150, 455))
    $subtitle.Name = 'CELL_LCT_CACHE_ATOM_000002'
    $subtitle.Contents = 'Encoder'
    $subtitle.TextRange.CharacterAttributes.Size = 12
    $subtitle.TextRange.CharacterAttributes.TextFont = $app.TextFonts.GetByName('Arial-Black')
    $safeBox = $root.PathItems.Rectangle(430, 360, 120, 50)
    $safeBox.Name = 'CELL_LCT_CACHE_ATOM_000003'
    $safeBox.Filled = $true
    $safeBox.Stroked = $false
    $safeBox.Opacity = 0.1
    $freeLabel = $root.TextFrames.PointText(@(420, 400))
    $freeLabel.Name = 'CELL_LCT_CACHE_ATOM_000004'
    $freeLabel.Contents = 'Classifier'
    $freeLabel.TextRange.CharacterAttributes.Size = 12
    $connector = $root.PathItems.Add()
    $connector.Name = 'CELL_LCT_CACHE_ATOM_000005'
    $connector.SetEntirePath(@(@(360, 405), @(480, 405)))
    $connector.Filled = $false
    $connector.Stroked = $true
    $connector.StrokeWidth = 1

    & $auditScript -Illustrator $app -RootGroupName $root.Name -CachePath (Join-Path $cacheDir 'geometry-cache.json') -ApprovedSvg $approvedSvg -OutputReport $reportPath -RepairText
    if ($LASTEXITCODE -ne 0) { throw 'The live Illustrator layout audit failed.' }
    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($report.status -ne 'PASS') { throw "Expected PASS, got $($report.status)." }
    if ($null -eq $report.diagnostics) { throw 'Expected structured diagnostics in the native report.' }
    if ([int]$report.unresolved_count -ne 0) { throw 'Expected zero unresolved layout issues.' }
    if ([int]$report.checked_text_count -ne 3) { throw 'Expected stacked boxed text and containerless text to be checked.' }
    if ([string]$label.TextRange.CharacterAttributes.TextFont.Name -ne 'Arial-BoldMT') {
        throw "Expected Arial-BoldMT for SVG weight 700, got $($label.TextRange.CharacterAttributes.TextFont.Name)."
    }
    if ([string]$subtitle.TextRange.CharacterAttributes.TextFont.Name -ne 'ArialMT') {
        throw "Expected ArialMT for SVG normal weight, got $($subtitle.TextRange.CharacterAttributes.TextFont.Name)."
    }
    if ([string]$label.Contents -ne 'Target') {
        throw "Expected approved one-line content Target, got $($label.Contents)."
    }
    $freeBounds = @($freeLabel.VisibleBounds)
    if (405 -le [double]$freeBounds[1] -and 405 -ge [double]$freeBounds[3]) {
        throw 'Expected the boxed free label to move clear of its connector.'
    }
    "PASS|repairs=$($report.repair_count)|unresolved=$($report.unresolved_count)"
}
finally {
    if ($null -ne $root) { try { $root.Remove() } catch { } }
    if ($testDocumentCreated -and $null -ne $document) { try { $document.Close(2) } catch { } }
    if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
    if (Test-Path -LiteralPath $temporary) {
        foreach ($file in @(
            $approvedSvg,
            $reportPath,
            (Join-Path $cacheDir 'geometry-cache.json'),
            (Join-Path $cacheDir 'playback.json')
        )) {
            if (Test-Path -LiteralPath $file -PathType Leaf) { Remove-Item -LiteralPath $file -Force }
        }
        if (Test-Path -LiteralPath $cacheDir -PathType Container) { Remove-Item -LiteralPath $cacheDir -Force }
        Remove-Item -LiteralPath $temporary -Force
    }
}
