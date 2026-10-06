#requires -Version 5.1

[CmdletBinding()]
param(
    [switch]$IncludeIllustrator,
    [string]$OutputReport = (Join-Path ([IO.Path]::GetTempPath()) 'medfig-illustrator-quality-gates.json')
)

$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'resolve_python.ps1')
$python = Get-CellLctPython
$stages = [ordered]@{}

function Invoke-QualityStage {
    param([string]$Name, [string]$Executable, [string[]]$Arguments)
    $stdoutPath = Join-Path ([IO.Path]::GetTempPath()) ("medfig-illustrator-gate-stdout-" + [Guid]::NewGuid().ToString('N') + '.txt')
    $stderrPath = Join-Path ([IO.Path]::GetTempPath()) ("medfig-illustrator-gate-stderr-" + [Guid]::NewGuid().ToString('N') + '.txt')
    try {
        # unittest writes progress to stderr even when it succeeds. Redirect
        # native streams through Start-Process so Windows PowerShell does not
        # wrap them as NativeCommandError records.
        $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -Wait -PassThru -NoNewWindow `
            -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $exitCode = $process.ExitCode
        [string]$stdout = $(if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw } else { '' })
        [string]$stderr = $(if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw } else { '' })
        $chunks = @()
        if (-not [string]::IsNullOrWhiteSpace($stdout)) { $chunks += $stdout.Trim() }
        if (-not [string]::IsNullOrWhiteSpace($stderr)) { $chunks += $stderr.Trim() }
        $output = $chunks -join "`n"
    }
    finally {
        if (Test-Path -LiteralPath $stdoutPath) { Remove-Item -LiteralPath $stdoutPath -Force }
        if (Test-Path -LiteralPath $stderrPath) { Remove-Item -LiteralPath $stderrPath -Force }
    }
    $script:stages[$Name] = [ordered]@{
        status = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }
        exit_code = $exitCode
        output = $output
    }
    if ($exitCode -ne 0) { throw "QUALITY_GATE_FAILED:$Name" }
}

$status = 'PASS'
$failure = $null
try {
    Invoke-QualityStage -Name 'python_layout' -Executable $python -Arguments (Get-CellLctPythonArguments @(
        '-3', '-X', 'utf8', (Join-Path $skillRoot 'tests\test_layout_guard.py'), '-v'
    ))
    Invoke-QualityStage -Name 'python_canvas_text' -Executable $python -Arguments (Get-CellLctPythonArguments @(
        '-3', '-X', 'utf8', (Join-Path $skillRoot 'tests\test_canvas_and_text.py'), '-v'
    ))
    Invoke-QualityStage -Name 'skill_validation' -Executable $python -Arguments (Get-CellLctPythonArguments @(
        '-3', '-X', 'utf8',
        (Join-Path $PSScriptRoot 'validate_skill.py'),
        $skillRoot
    ))
    if ($IncludeIllustrator) {
        Invoke-QualityStage -Name 'illustrator_layout' -Executable 'powershell.exe' -Arguments @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $skillRoot 'tests\test_illustrator_layout.ps1')
        )
        Invoke-QualityStage -Name 'canonical_bundle' -Executable 'powershell.exe' -Arguments @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $skillRoot 'tests\test_canonical_bundle.ps1')
        )
        Invoke-QualityStage -Name 'artboard_resize' -Executable 'powershell.exe' -Arguments @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $skillRoot 'tests\test_artboard_resize.ps1')
        )
    }
}
catch {
    $status = 'FAIL'
    $failure = $_.Exception.Message
}

$report = [ordered]@{
    schema_version = '1.0'
    status = $status
    include_illustrator = [bool]$IncludeIllustrator
    stages = $stages
    failure = $failure
}
$reportDirectory = Split-Path -Parent ([IO.Path]::GetFullPath($OutputReport))
if ($reportDirectory) { New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null }
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputReport -Encoding UTF8
Write-Output ("QUALITY_GATES|status={0}|stages={1}|report={2}" -f $status, $stages.Count, ([IO.Path]::GetFullPath($OutputReport)))
if ($status -ne 'PASS') { exit 2 }
exit 0
