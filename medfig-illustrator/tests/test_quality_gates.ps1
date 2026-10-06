$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $skillRoot 'scripts\run_quality_gates.ps1'
$diagnosticHelpers = Join-Path $skillRoot 'scripts\layout_diagnostics.ps1'
if (-not (Test-Path -LiteralPath $diagnosticHelpers -PathType Leaf)) {
    throw 'EXPECTED_FAIL: layout diagnostic helpers are missing.'
}
. $diagnosticHelpers
$parsed = ConvertTo-CellLctLayoutDiagnostic -Issue 'TEXT_GRAPHIC_OVERLAP:label-1:edge-2'
if ($parsed.code -ne 'TEXT_GRAPHIC_OVERLAP' -or $parsed.element_id -ne 'label-1' -or $parsed.other_id -ne 'edge-2') {
    throw 'Layout diagnostic parsing is incorrect.'
}
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw 'EXPECTED_FAIL: unified quality runner is missing.'
}

$report = Join-Path ([IO.Path]::GetTempPath()) ("medfig-illustrator-quality-" + [Guid]::NewGuid().ToString('N') + '.json')
try {
    & $runner -OutputReport $report
    if ($LASTEXITCODE -ne 0) { throw 'Quality runner returned a failure exit code.' }
    $result = Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($result.status -ne 'PASS') { throw "Expected PASS, got $($result.status)." }
    if ($null -eq $result.stages.python_layout) { throw 'python_layout stage is missing.' }
    if ($null -eq $result.stages.skill_validation) { throw 'skill_validation stage is missing.' }
    if ($result.stages.python_layout.status -ne 'PASS') { throw 'Python layout stage did not pass.' }
    if ($result.stages.skill_validation.status -ne 'PASS') { throw 'Skill validation stage did not pass.' }
    'PASS|quality_gates=2|illustrator=skipped'
}
finally {
    if (Test-Path -LiteralPath $report -PathType Leaf) { Remove-Item -LiteralPath $report -Force }
}
