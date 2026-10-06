$ErrorActionPreference = 'Stop'
# Live test for the runtime's resizeArtboard operation. It works only on a
# temporary document it creates and closes, so the user's open documents and
# artboards are never touched.
$skillRoot = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $skillRoot 'scripts\cell_lct_cached_runtime.jsx'
. (Join-Path $skillRoot 'scripts\illustrator_com.ps1')

$app = $null
$document = $null
$previous = $null
try {
    $app = Connect-RunningIllustrator
    if ([int]$app.Documents.Count -gt 0) { $previous = $app.ActiveDocument }
    $document = $app.Documents.Add()
    $documentName = [string]$document.Name
    $rootName = 'CELL_LCT_RESIZE_TEST_' + [Guid]::NewGuid().ToString('N')
    $runtimeJson = (($runtimePath -replace '\\', '/') | ConvertTo-Json -Compress)

    function Invoke-Resize([double]$width, [double]$height) {
        $configuration = [ordered]@{
            operation = 'resizeArtboard'
            targetDocumentName = $documentName
            rootGroupName = $rootName
            width = $width
            height = $height
        }
        $configJson = ConvertTo-Json $configuration -Compress
        return [string]$app.DoJavaScript("var CELL_LCT_CACHED_CONFIG = $configJson; `$`.evalFile(new File($runtimeJson));")
    }
    function Get-Rect {
        return @($document.Artboards.Item($document.Artboards.GetActiveArtboardIndex() + 1).ArtboardRect | ForEach-Object { [double]$_ })
    }

    $start = Get-Rect
    $startWidth = $start[2] - $start[0]
    $startHeight = $start[1] - $start[3]

    # 1. Enlarging keeps the top-left corner and reaches the requested size.
    $result = Invoke-Resize ($startWidth + 300) ($startHeight + 200)
    if (-not $result.StartsWith('OK|')) { throw "EXPECTED_OK:$result" }
    $grown = Get-Rect
    if ([math]::Abs($grown[0] - $start[0]) -gt 0.01 -or [math]::Abs($grown[1] - $start[1]) -gt 0.01) {
        throw "TOP_LEFT_MOVED:$($start -join ',')->$($grown -join ',')"
    }
    if ([math]::Abs(($grown[2] - $grown[0]) - ($startWidth + 300)) -gt 0.5) { throw "WIDTH_NOT_APPLIED:$($grown -join ',')" }
    if ([math]::Abs(($grown[1] - $grown[3]) - ($startHeight + 200)) -gt 0.5) { throw "HEIGHT_NOT_APPLIED:$($grown -join ',')" }

    # 2. Shrinking is refused and leaves the artboard unchanged.
    $result = Invoke-Resize ($startWidth) ($startHeight + 200)
    if ($result -notmatch 'ARTBOARD_SHRINK_REFUSED') { throw "EXPECTED_SHRINK_REFUSED:$result" }
    if (((Get-Rect) -join ',') -ne ($grown -join ',')) { throw 'ARTBOARD_CHANGED_AFTER_REFUSED_SHRINK' }

    # 3. Invalid sizes are refused.
    $result = Invoke-Resize 0 ($startHeight + 200)
    if ($result -notmatch 'ARTBOARD_SIZE_INVALID') { throw "EXPECTED_SIZE_INVALID:$result" }

    # 4. Once this job's root group exists, resizing is refused so drawn artwork never shifts.
    $rootJson = $rootName | ConvertTo-Json -Compress
    $setup = "(function(){var d=app.activeDocument,r=d.groupItems.add();r.name=$rootJson;r.pathItems.rectangle(-10,10,20,20);return 'OK';}());"
    if ([string]$app.DoJavaScript($setup) -ne 'OK') { throw 'SETUP_FAILED' }
    $result = Invoke-Resize ($startWidth + 600) ($startHeight + 400)
    if ($result -notmatch 'ARTBOARD_RESIZE_REFUSED_ROOT_EXISTS') { throw "EXPECTED_ROOT_EXISTS_REFUSED:$result" }
    if (((Get-Rect) -join ',') -ne ($grown -join ',')) { throw 'ARTBOARD_CHANGED_AFTER_ROOT_REFUSAL' }

    'PASS|artboard_resize=4'
}
finally {
    if ($null -ne $document) { try { $document.Close(2) } catch { } }
    if ($null -ne $previous) { try { $previous.Activate() } catch { } }
    if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
}
