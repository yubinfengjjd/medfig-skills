function Connect-RunningIllustrator {
    $visible = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0 -and ($_.ProcessName -match 'Illustrator' -or $_.MainWindowTitle -match 'Illustrator')
    } | Select-Object -First 1
    if ($null -eq $visible) {
        throw 'AI_NOT_RUNNING|Open Illustrator and the target document yourself; this Skill never starts or controls the Illustrator window.'
    }

    # The unversioned ProgID resolves to the currently registered Illustrator
    # and attaches to the process already verified above instead of requiring
    # a hard-coded yearly COM registration such as Application.30.
    $illustrator = New-Object -ComObject 'Illustrator.Application'
    # Lowered from 24.0 (2020) to 23.0 (CC 2019) for this machine; untested upstream.
    if ([version]$illustrator.Version -lt [version]'23.0') {
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($illustrator)
        throw "Illustrator CC 2019 or newer is required; connected version is $($illustrator.Version)."
    }
    return $illustrator
}
