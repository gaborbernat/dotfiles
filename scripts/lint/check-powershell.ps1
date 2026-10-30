# Formats each script in place with PSScriptAnalyzer and fails when formatting changed it or the analyzer reports.
if (-not (Get-Module -ListAvailable PSScriptAnalyzer)) {
    Install-Module PSScriptAnalyzer -Scope CurrentUser -Force
}
$failed = $false
foreach ($path in $args) {
    $source = Get-Content -Raw $path
    $formatted = Invoke-Formatter -ScriptDefinition $source
    if ($formatted -ne $source) {
        Set-Content -NoNewline $path $formatted
        $failed = $true
    }
    if ($findings = Invoke-ScriptAnalyzer -Path $path -Severity Information) {
        $findings | Format-Table -AutoSize
        $failed = $true
    }
}
if ($failed) {
    exit 1
}
