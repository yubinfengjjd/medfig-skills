function ConvertTo-CellLctLayoutDiagnostic {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Issue)

    $parts = $Issue -split ':', 3
    [pscustomobject][ordered]@{
        code = if ($parts.Count -ge 1) { $parts[0] } else { '' }
        element_id = if ($parts.Count -ge 2) { $parts[1] } else { $null }
        other_id = if ($parts.Count -ge 3) { $parts[2] } else { $null }
        raw = $Issue
    }
}
