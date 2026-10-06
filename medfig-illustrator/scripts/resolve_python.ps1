# Resolve a Python 3 interpreter that has Pillow and fontTools.
# Order: $env:CELL_LCT_PYTHON -> real py launcher -> known local installs -> python on PATH.
# Dot-source this file; it defines a `py` function that shadows a missing py.exe
# and drops the launcher-only `-3` flag when forwarding to python.exe.

function Get-CellLctPython {
    if ($script:CellLctPython) { return $script:CellLctPython }
    $candidates = @()
    if ($env:CELL_LCT_PYTHON) { $candidates += $env:CELL_LCT_PYTHON }
    $launcher = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($launcher) { $script:CellLctPython = $launcher.Source; $script:CellLctIsLauncher = $true; return $script:CellLctPython }
    $candidates += @('D:\anaconda\python.exe', 'D:\python\python.exe')
    $onPath = Get-Command python.exe -CommandType Application -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notmatch '\\WindowsApps\\' } | ForEach-Object { $_.Source }
    $candidates += $onPath
    foreach ($candidate in $candidates) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate)) { continue }
        & $candidate -c "import PIL, fontTools" 2>$null
        if ($LASTEXITCODE -eq 0) { $script:CellLctPython = $candidate; $script:CellLctIsLauncher = $false; return $candidate }
    }
    throw 'PYTHON_NOT_FOUND|Install Python 3 with Pillow and fontTools, or set CELL_LCT_PYTHON.'
}

function Get-CellLctPythonArguments {
    param([object[]]$Arguments)
    $null = Get-CellLctPython
    if (-not $script:CellLctIsLauncher -and $Arguments.Count -gt 0 -and "$($Arguments[0])" -eq '-3') {
        if ($Arguments.Count -eq 1) { return @() }
        return $Arguments[1..($Arguments.Count - 1)]
    }
    return $Arguments
}

function py {
    $exe = Get-CellLctPython
    $forward = Get-CellLctPythonArguments $args
    & $exe @forward
}
