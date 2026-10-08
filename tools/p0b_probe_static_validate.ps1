# CI-only validation: parse the P0-B PowerShell script and compile embedded
# C# using Windows PowerShell/.NET Framework. Does NOT connect to Visio.
param([string]$ProbePath = (Join-Path $PSScriptRoot 'p0b_live_overlay_probe.ps1'))
$ErrorActionPreference = 'Stop'
$tokens = $null
$syntaxErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
    $ProbePath, [ref]$tokens, [ref]$syntaxErrors
)
if ($syntaxErrors.Count -gt 0) {
    throw ('PowerShell parser reported ' + $syntaxErrors.Count + ': ' + ($syntaxErrors | Out-String))
}
$source = [IO.File]::ReadAllText($ProbePath)
$match = [regex]::Match($source, '(?s)\$source\s*=\s*@''\r?\n(.*?)\r?\n''@')
if (-not $match.Success) {
    throw 'Embedded C# source here-string was not found'
}
if ($source -notmatch 'CellsU\(''LocPinX''\)' -or
    $source -notmatch 'busStartX\s*=\s*\$cx\s*-\s*\$busLocX' -or
    $source -match 'halfW' -or
    $match.Groups[1].Value -match 'CaptionText' -or
    $source -notmatch 'GetCursorPos' -or
    $source -notmatch 'two-cursor-points-calibrated' -or
    $source -notmatch 'calibrationExpired') {
    throw 'P0-B bus anchor or diagnostic label regression'
}
Add-Type -TypeDefinition $match.Groups[1].Value -Language CSharp -ReferencedAssemblies @(
    'System.Windows.Forms.dll', 'System.Drawing.dll'
)
Write-Output 'P0B_POWERSHELL_PARSER_PASS'
Write-Output 'P0B_EMBEDDED_CSHARP_COMPILE_PASS'
