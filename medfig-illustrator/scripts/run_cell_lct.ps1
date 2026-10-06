param(
    [Parameter(Mandatory = $true)]
    [string]$InputSvg,
    [Parameter(Mandatory = $true)]
    [string]$WorkDir,
    [string]$OutputAi,
    [string]$OutputSvg,
    [string]$OutputPng,
    [ValidateRange(1, 50)]
    [int]$MinBatchSize = 20,
    [ValidateRange(1, 50)]
    [int]$MaxBatchSize = 50,
    [ValidateRange(20, 100000)]
    [int]$ComplexPointThreshold = 320,
    [ValidateRange(100, 100000)]
    [int]$MaxBatchPoints = 2200,
    [ValidateRange(0, 1000)]
    [int]$DelayMs = 0,
    [string]$TargetLayerName = '',
    [ValidateSet('center', 'top-center', 'left-center', 'bottom-center', 'bottom-right', 'top-right', 'bottom-left', 'top-left')]
    [string]$Placement = 'center',
    [ValidateRange(0.01, 1.0)]
    [double]$MaxWidthFraction = 0.72,
    [ValidateRange(0.01, 1.0)]
    [double]$MaxHeightFraction = 0.78,
    [ValidateRange(5, 3600)]
    [int]$CheckpointSeconds = 30,
    [ValidateRange(1, 50)]
    [int]$InSessionRetryLimit = 12,
    [switch]$DryRun,
    # Embed explicitly requested local raster panels (<image data-raster-source="user-asset">).
    [switch]$AllowRaster,
    # Keep the user's artboard even when placed text would drop below the
    # 8 pt floor. Default behaviour enlarges the active artboard before drawing.
    [switch]$NoArtboardResize,
    [switch]$QuietExistingGroups
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'resolve_python.ps1')
if ($MinBatchSize -gt $MaxBatchSize) { throw 'MinBatchSize must not exceed MaxBatchSize.' }

$inputPath = (Resolve-Path -LiteralPath $InputSvg).Path
$originalInputPath = $inputPath
$assetBaseDir = [IO.Path]::GetDirectoryName($originalInputPath)
$workPath = [IO.Path]::GetFullPath($WorkDir)
New-Item -ItemType Directory -Force -Path $workPath | Out-Null
$stem = [IO.Path]::GetFileNameWithoutExtension($inputPath)
if ([string]::IsNullOrWhiteSpace($OutputAi)) {
    $OutputAi = Join-Path ([IO.Path]::GetDirectoryName($inputPath)) "${stem}.ai"
}
if ([string]::IsNullOrWhiteSpace($OutputSvg)) {
    $OutputSvg = Join-Path ([IO.Path]::GetDirectoryName($originalInputPath)) "${stem}.svg"
}
if ([string]::IsNullOrWhiteSpace($OutputPng)) {
    $OutputPng = Join-Path ([IO.Path]::GetDirectoryName($inputPath)) "${stem}.png"
}
$OutputAi = [IO.Path]::GetFullPath($OutputAi)
$OutputSvg = [IO.Path]::GetFullPath($OutputSvg)
$OutputPng = [IO.Path]::GetFullPath($OutputPng)
foreach ($outputPath in @($OutputAi, $OutputSvg, $OutputPng)) {
    $directory = [IO.Path]::GetDirectoryName($outputPath)
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
}

# Keep the authored input as a reproducible work artifact. The public SVG is
# replaced only at completion by the native postflight-approved export.
$masterSourcePath = Join-Path $workPath 'master-source.svg'
Copy-Item -LiteralPath $originalInputPath -Destination $masterSourcePath -Force
$inputPath = (Resolve-Path -LiteralPath $masterSourcePath).Path

$existingCachePath = Join-Path $workPath 'geometry-cache.json'
if (Test-Path -LiteralPath $existingCachePath -PathType Leaf) {
    $existingCacheHeader = Get-Content -LiteralPath $existingCachePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $jobSeed = [string]$existingCacheHeader.job_id
} else {
    # The sequential user-facing stem is globally unique. The work-directory
    # leaf is often the shared name "cached-playback" and must never identify
    # an Illustrator root group across separate drawing jobs.
    $jobSeed = $stem
}
$jobId = ($jobSeed -replace '[^A-Za-z0-9_-]', '_').Trim('_')
if ([string]::IsNullOrWhiteSpace($jobId)) { $jobId = 'job' }
if ($jobId.Length -gt 48) { $jobId = $jobId.Substring(0, 48) }

$prepareScript = Join-Path $PSScriptRoot 'prepare_geometry_cache.py'
$runtimePath = Join-Path $PSScriptRoot 'cell_lct_cached_runtime.jsx'
$comHelper = Join-Path $PSScriptRoot 'illustrator_com.ps1'
$layoutGuard = Join-Path $PSScriptRoot 'layout_guard.py'
$illustratorLayoutAudit = Join-Path $PSScriptRoot 'audit_illustrator_layout.ps1'
$bundleVerifier = Join-Path $PSScriptRoot 'verify_delivery_bundle.ps1'
foreach ($required in @($prepareScript, $runtimePath, $comHelper, $layoutGuard, $illustratorLayoutAudit, $bundleVerifier)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing required file: $required" }
}
. $comHelper

$layoutApprovedPath = Join-Path $workPath 'layout-approved.svg'
$layoutReportPath = Join-Path $workPath 'layout-preflight.json'
$layoutOutput = & py -3 -X utf8 $layoutGuard --input $inputPath --output $layoutApprovedPath --report $layoutReportPath --repair
if ($LASTEXITCODE -ne 0) {
    throw "LAYOUT_PREFLIGHT_FAILED|$layoutOutput"
}
$layoutReport = Get-Content -LiteralPath $layoutReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$layoutReport.status -ne 'PASS' -or [int]$layoutReport.unresolved_count -ne 0) {
    throw "LAYOUT_PREFLIGHT_FAILED|report=$layoutReportPath"
}
$inputPath = (Resolve-Path -LiteralPath $layoutApprovedPath).Path

$prepareArguments = @(
    '-3', '-X', 'utf8', $prepareScript,
    '--input', $inputPath,
    '--output-dir', $workPath,
    '--job-id', $jobId,
    '--min-batch-size', $MinBatchSize,
    '--max-batch-size', $MaxBatchSize,
    '--complex-point-threshold', $ComplexPointThreshold,
    '--max-batch-points', $MaxBatchPoints,
    '--asset-base-dir', $assetBaseDir
)
if ($AllowRaster) { $prepareArguments += '--allow-raster' }
$prepareOutput = & py @prepareArguments
if ($LASTEXITCODE -ne 0) { throw "Geometry cache preparation failed: $prepareOutput" }

$cachePath = Join-Path $workPath 'geometry-cache.json'
$statePath = Join-Path $workPath 'playback.json'
$cache = Get-Content -LiteralPath $cachePath -Raw -Encoding UTF8 | ConvertFrom-Json
$state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
$expectedRasterCount = [int]$cache.raster_count
if (-not $AllowRaster -and $expectedRasterCount -ne 0) { throw 'RASTER_NOT_ALLOWED|Rerun with -AllowRaster for explicitly requested image panels.' }

if ($DryRun) {
    Write-Output $prepareOutput
    Write-Output "DRY_RUN|cache=$cachePath|state=$statePath|atoms=$($cache.total_atoms)|batches=$($state.batches.Count)|illustrator_untouched=true"
    exit 0
}

function Save-State([object]$value) {
    $value.updated_at = [DateTime]::UtcNow.ToString('o')
    $temporary = "$statePath.tmp"
    $value | ConvertTo-Json -Depth 12 -Compress | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $statePath -Force
}

function Assert-IllustratorAlreadyOpen {
    $visible = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0 -and ($_.ProcessName -match 'Illustrator' -or $_.MainWindowTitle -match 'Illustrator')
    } | Select-Object -First 1
    if ($null -eq $visible) {
        throw 'AI_NOT_RUNNING|Open Illustrator and the target document yourself; this Skill never starts or controls the Illustrator window.'
    }
}

function ConvertTo-JsJson([object]$value) {
    return ConvertTo-Json -InputObject $value -Compress -Depth 20
}

function Invoke-CachedRuntime([object]$illustrator, [object]$configuration) {
    $configJson = ConvertTo-JsJson $configuration
    $runtimeJson = (($runtimePath -replace '\\', '/') | ConvertTo-Json -Compress)
    $bootstrap = "var CELL_LCT_CACHED_CONFIG = $configJson; `$`.evalFile(new File($runtimeJson));"
    return [string]$illustrator.DoJavaScript($bootstrap)
}

function Read-ResultValue([string]$result, [string]$key) {
    foreach ($part in ($result -split '\|')) {
        if ($part.StartsWith("$key=")) { return $part.Substring($key.Length + 1) }
    }
    return $null
}

function Get-ExistingBatchGroups([object]$illustrator, [string]$documentName) {
    $configuration = [ordered]@{
        documentName = $documentName
        rootGroupName = [string]$state.root_group_name
        groupNames = @($state.batches | ForEach-Object { [string]$_.group_name })
    }
    $payload = ConvertTo-JsJson $configuration
    $script = @"
(function(){
  var c=$payload;
  function namedGroup(container,name){
    for(var i=0;i<container.groupItems.length;i+=1){
      try{var item=container.groupItems[i];if(item&&item.name===name){return item;}}catch(ignore){}
    }
    return null;
  }
  var doc=null;
  for(var d=0;d<app.documents.length;d+=1){if(app.documents[d].name===c.documentName){doc=app.documents[d];break;}}
  if(doc===null){return 'ERROR|TARGET_DOCUMENT_MISSING';}
  var root=namedGroup(doc,c.rootGroupName);
  if(root===null){return '';}
  var found=[];
  for(var i=0;i<c.groupNames.length;i+=1){
    if(namedGroup(root,c.groupNames[i])!==null){found.push(c.groupNames[i]);}
  }
  return found.join('|LCTSEP|');
}());
"@
    $result = [string]$illustrator.DoJavaScript($script)
    if ($result.StartsWith('ERROR|')) { throw $result }
    if ([string]::IsNullOrWhiteSpace($result)) { return @() }
    return @($result -split '\|LCTSEP\|' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Save-WorkspaceCheckpoint([object]$illustrator, [string]$documentName) {
    $configuration = [ordered]@{
        operation = 'saveWorkspace'
        targetDocumentName = $documentName
    }
    $result = Invoke-CachedRuntime $illustrator $configuration
    if (-not $result.StartsWith('OK|')) { throw "AI checkpoint failed: $result" }
    $updatedName = Read-ResultValue $result 'documentName'
    return $(if ([string]::IsNullOrWhiteSpace($updatedName)) { $documentName } else { $updatedName })
}

function Export-FinalBundle([object]$illustrator, [string]$documentName, [int]$artboardIndex) {
    $configuration = [ordered]@{
        operation = 'exportBundle'
        targetDocumentName = $documentName
        rootGroupName = [string]$state.root_group_name
        artboardIndex = $artboardIndex
        outputAi = ($OutputAi -replace '\\', '/')
        outputSvg = ($OutputSvg -replace '\\', '/')
        outputPng = ($OutputPng -replace '\\', '/')
        expectedRasterCount = $expectedRasterCount
    }
    $result = Invoke-CachedRuntime $illustrator $configuration
    if (-not $result.StartsWith('OK|documentName=') -or $result -notmatch '\|artboards=1(?:\||$)') {
        throw "Canonical bundle export failed: $result"
    }
}

function Normalize-RootStackAndRemoveOrphans([object]$illustrator, [string]$documentName) {
    $configuration = [ordered]@{
        documentName = $documentName
        rootGroupName = [string]$state.root_group_name
        targetLayerName = $TargetLayerName
        batchGroupNames = @($state.batches | ForEach-Object { [string]$_.group_name })
    }
    $payload = ConvertTo-JsJson $configuration
    $script = @"
(function(){
  var c=$payload;
  function namedGroup(container,name){
    for(var i=0;i<container.groupItems.length;i+=1){
      try{var item=container.groupItems[i];if(item&&item.name===name){return item;}}catch(ignore){}
    }
    return null;
  }
  var doc=null;
  for(var d=0;d<app.documents.length;d+=1){if(app.documents[d].name===c.documentName){doc=app.documents[d];break;}}
  if(doc===null){return 'ERROR|TARGET_DOCUMENT_MISSING';}
  var root=namedGroup(doc,c.rootGroupName);
  if(root===null){return 'ERROR|ROOT_GROUP_MISSING';}
  var layer=null;
  if(c.targetLayerName){
    try{layer=doc.layers.getByName(c.targetLayerName);}catch(ignoreLayer){}
  }
  if(layer===null&&root.parent&&root.parent.typename==='Layer'){layer=root.parent;}
  if(layer===null){return 'ERROR|TARGET_LAYER_MISSING';}

  // Later source batches must remain above earlier batches. Rebuilding this
  // order also repairs any batch moved during a retry or a visual QA check.
  for(var b=0;b<c.batchGroupNames.length;b+=1){
    var batch=namedGroup(root,c.batchGroupNames[b]);
    if(batch!==null&&batch.parent===root){batch.zOrder(ZOrderMethod.BRINGTOFRONT);}
  }

  // Existing artwork is immutable. Never remove, hide, rename, or replace
  // any page item outside this job's root group.
  app.redraw();
  return 'OK|removed=0|existing_artwork_preserved=true';
}());
"@
    $result = [string]$illustrator.DoJavaScript($script)
    if (-not $result.StartsWith('OK|')) { throw "Final stack normalization failed: $result" }
}

function Assert-CompleteArtwork([object]$illustrator, [string]$documentName) {
    $batchExpectations = @()
    foreach ($batchState in $state.batches) {
        $paintNames = @()
        foreach ($atomIndex in $batchState.atom_indices) {
            $atom = $cache.atoms[[int]$atomIndex]
            if (@($atom.paintParts).Count -le 1) {
                $paintNames += [string]$atom.objectName
            } else {
                for ($paintIndex = 0; $paintIndex -lt @($atom.paintParts).Count; $paintIndex++) {
                    $paintNames += "$([string]$atom.objectName)_P$paintIndex"
                }
            }
        }
        $batchExpectations += [ordered]@{
            groupName = [string]$batchState.group_name
            paintNames = $paintNames
        }
    }
    $configuration = [ordered]@{
        documentName = $documentName
        rootGroupName = [string]$state.root_group_name
        batches = $batchExpectations
    }
    $payload = ConvertTo-JsJson $configuration
    $script = @"
(function(){
  var c=$payload;
  function namedGroup(container,name){
    for(var i=0;i<container.groupItems.length;i+=1){
      try{var item=container.groupItems[i];if(item&&item.name===name){return item;}}catch(ignore){}
    }
    return null;
  }
  function namedArtwork(container,name){
    var group=namedGroup(container,name);if(group!==null){return group;}
    var collections=[container.pathItems,container.compoundPathItems,container.textFrames];
    for(var q=0;q<collections.length;q+=1){
      for(var i=0;i<collections[q].length;i+=1){
        try{var item=collections[q][i];if(item&&item.name===name){return item;}}catch(ignore){}
      }
    }
    return null;
  }
  var doc=null;
  for(var d=0;d<app.documents.length;d+=1){if(app.documents[d].name===c.documentName){doc=app.documents[d];break;}}
  if(doc===null){return 'ERROR|TARGET_DOCUMENT_MISSING';}
  var root=namedGroup(doc,c.rootGroupName);
  if(root===null){return 'ERROR|ROOT_GROUP_MISSING';}
  var missing=0;
  for(var b=0;b<c.batches.length;b+=1){
    var batch=namedGroup(root,c.batches[b].groupName);
    if(batch===null){missing+=c.batches[b].paintNames.length;continue;}
    for(var a=0;a<c.batches[b].paintNames.length;a+=1){
      if(namedArtwork(batch,c.batches[b].paintNames[a])===null){missing+=1;}
    }
  }
  var doc2=root.parent;while(doc2&&doc2.typename!=='Document'){doc2=doc2.parent;}
  var placed=0,raster=0;
  function inRoot(item){var p=item.parent;while(p){if(p===root)return true;if(p.typename==='Document'||p.typename==='Layer')return false;p=p.parent;}return false;}
  for(var r=0;r<doc2.rasterItems.length;r+=1){if(inRoot(doc2.rasterItems[r]))raster+=1;}
  for(var q=0;q<doc2.placedItems.length;q+=1){if(inRoot(doc2.placedItems[q]))placed+=1;}
  return 'OK|missing='+missing+'|placed='+placed+'|raster='+raster;
}());
"@
    $result = [string]$illustrator.DoJavaScript($script)
    if ($result -ne "OK|missing=0|placed=0|raster=$expectedRasterCount") {
        throw "QA_FAILED|$result"
    }
}

$illustrator = $null
$batchPayloadPath = Join-Path $workPath 'current-batch.json'
try {
    # The process check prevents COM from being used as an Illustrator launcher.
    # Keep this one COM proxy for the complete drawing session.
    $illustrator = Connect-RunningIllustrator
    if ($illustrator.Documents.Count -lt 1) {
        throw 'AI_DOCUMENT_REQUIRED|Open the target Illustrator document yourself before drawing.'
    }

    $targetDocumentName = [string]$illustrator.ActiveDocument.Name
    $targetArtboardIndex = [int]$illustrator.ActiveDocument.Artboards.GetActiveArtboardIndex()
    $existingGroups = @(Get-ExistingBatchGroups $illustrator $targetDocumentName)

    # Canvas rule: before the first batch, size the artboard so the smallest
    # placed text stays at or above the 8 pt floor. Only enlarge, only while
    # this job has drawn nothing, and keep the artboard's top-left corner.
    if ($existingGroups.Count -eq 0) {
        $artboardRect = @($illustrator.ActiveDocument.Artboards.Item($targetArtboardIndex + 1).ArtboardRect)
        $artboardWidth = [double]$artboardRect[2] - [double]$artboardRect[0]
        $artboardHeight = [double]$artboardRect[1] - [double]$artboardRect[3]
        $fitReportPath = Join-Path $workPath 'artboard-fit.json'
        $fitArguments = @(
            '-3', '-X', 'utf8', (Join-Path $PSScriptRoot 'artboard_fit.py'),
            '--cache', $cachePath,
            '--artboard-width', $artboardWidth.ToString([Globalization.CultureInfo]::InvariantCulture),
            '--artboard-height', $artboardHeight.ToString([Globalization.CultureInfo]::InvariantCulture),
            '--max-width-fraction', $MaxWidthFraction.ToString([Globalization.CultureInfo]::InvariantCulture),
            '--max-height-fraction', $MaxHeightFraction.ToString([Globalization.CultureInfo]::InvariantCulture),
            '--report', $fitReportPath)
        $fitOutput = & py @fitArguments
        if ($LASTEXITCODE -ne 0) { throw "ARTBOARD_FIT_FAILED|$fitOutput" }
        $fitLine = [string](@($fitOutput) | Where-Object { $_ -like 'FIT|*' } | Select-Object -Last 1)
        Write-Output $fitLine
        if ($fitLine -match 'action=resize\|width=([0-9.]+)\|height=([0-9.]+)') {
            if ($NoArtboardResize) {
                Write-Output 'ARTBOARD_RESIZE_SKIPPED|reason=NoArtboardResize|native_font_floor_will_fail=true'
            } else {
                $resizeResult = Invoke-CachedRuntime $illustrator ([ordered]@{
                    operation = 'resizeArtboard'
                    targetDocumentName = $targetDocumentName
                    rootGroupName = [string]$state.root_group_name
                    width = [double]$Matches[1]
                    height = [double]$Matches[2]
                })
                if (-not $resizeResult.StartsWith('OK|')) { throw "ARTBOARD_RESIZE_FAILED|$resizeResult" }
                Write-Output "ARTBOARD_RESIZED|$resizeResult"
            }
        }
    }
    $lastCheckpoint = [DateTime]::UtcNow
    $hasCheckpoint = Test-Path -LiteralPath $OutputAi
    $continued = $false

    foreach ($batchState in $state.batches) {
        $groupExists = $existingGroups -contains [string]$batchState.group_name
        if ([bool]$batchState.completed -and $groupExists) {
            $continued = $true
            if (-not $QuietExistingGroups) {
                Write-Output "SKIP|batch=$($batchState.index)|group=$($batchState.group_name)|reason=completed_group_is_immutable"
            }
            continue
        }
        if ([bool]$batchState.completed -and -not $groupExists) {
            $batchState.completed = $false
            $batchState.completed_at = $null
            $batchState.last_error = 'Recorded complete but the immutable batch group is missing.'
            Save-State $state
        }

        $atoms = @()
        foreach ($atomIndex in $batchState.atom_indices) {
            $atoms += $cache.atoms[[int]$atomIndex]
        }
        $payload = [ordered]@{ viewBox = $cache.view_box; atoms = $atoms }
        $utf8NoBom = New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($batchPayloadPath, (ConvertTo-JsJson $payload), $utf8NoBom)

        $configuration = [ordered]@{
            operation = 'draw'
            batchJsonPath = ($batchPayloadPath -replace '\\', '/')
            targetDocumentName = $targetDocumentName
            rootGroupName = [string]$state.root_group_name
            batchGroupName = [string]$batchState.group_name
            placement = $Placement
            maxWidthFraction = $MaxWidthFraction
            maxHeightFraction = $MaxHeightFraction
            delayMs = $DelayMs
            targetLayerName = $TargetLayerName
        }
        $result = $null
        for ($sessionAttempt = 1; $sessionAttempt -le $InSessionRetryLimit; $sessionAttempt++) {
            $batchState.attempts = [int]$batchState.attempts + 1
            $batchState.last_error = $null
            Save-State $state
            $result = Invoke-CachedRuntime $illustrator $configuration
            if ($result.StartsWith('OK|')) { break }

            $batchState.last_error = $result
            Save-State $state
            $unrecoverable = $result -match 'TARGET_DOCUMENT_MISSING|AI_DOCUMENT_REQUIRED|Unsupported operation'
            if ($unrecoverable -or $sessionAttempt -ge $InSessionRetryLimit) { break }
            Start-Sleep -Milliseconds 80
        }
        if (-not $result.StartsWith('OK|')) {
            $completed = @($state.batches | Where-Object { $_.completed }).Count
            Write-Output "RESUME_REQUIRED|failed_batch=$($batchState.index)|completed=$completed/$($state.batches.Count)|state=$statePath|existing_artwork_preserved=true"
            exit 2
        }

        $batchState.completed = $true
        $batchState.completed_at = [DateTime]::UtcNow.ToString('o')
        $batchState.last_error = $null
        Save-State $state
        $existingGroups += [string]$batchState.group_name
        Write-Output "DONE|batch=$($batchState.index)|group=$($batchState.group_name)|$result"

        $checkpointDue = -not $hasCheckpoint -or ([DateTime]::UtcNow - $lastCheckpoint).TotalSeconds -ge $CheckpointSeconds
        if ($checkpointDue) {
            $targetDocumentName = Save-WorkspaceCheckpoint $illustrator $targetDocumentName
            $lastCheckpoint = [DateTime]::UtcNow
            $hasCheckpoint = $true
        }
    }

    $completedCount = @($state.batches | Where-Object { $_.completed }).Count
    if ($completedCount -ne $state.batches.Count) { throw "QA_FAILED|completed=$completedCount/$($state.batches.Count)" }
    Normalize-RootStackAndRemoveOrphans $illustrator $targetDocumentName
    Assert-CompleteArtwork $illustrator $targetDocumentName
    $layoutPostflightPath = Join-Path $workPath 'layout-postflight.json'
    & $illustratorLayoutAudit -Illustrator $illustrator -RootGroupName ([string]$state.root_group_name) -CachePath $cachePath -ApprovedSvg $inputPath -OutputReport $layoutPostflightPath -RepairText | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "LAYOUT_POSTFLIGHT_FAILED|report=$layoutPostflightPath"
    }
    $layoutPostflight = Get-Content -LiteralPath $layoutPostflightPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$layoutPostflight.status -ne 'PASS' -or [int]$layoutPostflight.unresolved_count -ne 0) {
        throw "LAYOUT_POSTFLIGHT_FAILED|report=$layoutPostflightPath"
    }
    Export-FinalBundle $illustrator $targetDocumentName $targetArtboardIndex
    if (-not (Test-Path -LiteralPath $OutputAi) -or -not (Test-Path -LiteralPath $OutputSvg) -or -not (Test-Path -LiteralPath $OutputPng)) {
        throw 'QA_FAILED|The expected canonical AI, SVG, or PNG file is missing.'
    }
    $liveTextScript = Join-Path $PSScriptRoot 'svg_live_text.py'
    $liveFix = & py -3 -X utf8 $liveTextScript fix --svg $OutputSvg
    if ($LASTEXITCODE -ne 0) { throw "LIVE_TEXT_FIX_FAILED|$liveFix" }
    $liveAudit = & py -3 -X utf8 $liveTextScript audit --svg $OutputSvg --report (Join-Path $workPath 'live-text-audit.json')
    if ($LASTEXITCODE -ne 0) { throw "LIVE_TEXT_AUDIT_FAILED|$liveAudit" }
    Write-Output ([string](@($liveAudit) | Select-Object -Last 1))
    $bundleReportPath = Join-Path $workPath 'bundle-verification.json'
    & $bundleVerifier -Illustrator $illustrator -AiPath $OutputAi -SvgPath $OutputSvg -PngPath $OutputPng -OutputReport $bundleReportPath -ExpectedRasterCount $expectedRasterCount | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "BUNDLE_VERIFICATION_FAILED|report=$bundleReportPath" }
    $bundleReport = Get-Content -LiteralPath $bundleReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$bundleReport.status -ne 'PASS' -or [int]$bundleReport.unresolved_count -ne 0) {
        throw "BUNDLE_VERIFICATION_FAILED|report=$bundleReportPath"
    }
    $mode = if ($continued) { 'continued' } else { 'fresh' }
    Write-Output "CELL_LCT_COMPLETE|cache=$cachePath|ai=$OutputAi|svg=$OutputSvg|png=$OutputPng|batches=$completedCount/$($state.batches.Count)|mode=$mode|illustrator_window_untouched=true"
} finally {
    if (Test-Path -LiteralPath $batchPayloadPath) {
        Remove-Item -LiteralPath $batchPayloadPath -Force -ErrorAction SilentlyContinue
    }
    if ($null -ne $illustrator) {
        [Runtime.InteropServices.Marshal]::ReleaseComObject($illustrator) | Out-Null
    }
}
