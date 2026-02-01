<#
.SYNOPSIS
    Transfers scripts to the target VM using SCP.
.DESCRIPTION
    Equivalent to scp-scripts-to-vm.sh.
    Transfers .env.hef-conversion-hyperv and install-dxgkrnl.sh to the target's home directory.
.EXAMPLE
    .\scp-scripts-to-vm.ps1 user@192.168.1.10
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target
)

$ErrorActionPreference = "Stop"

# Set directory to the script's location
$ScriptDir = $PSScriptRoot

$FilesToTransfer = @(
    ".env.hef-conversion-hyperv",
    "install-dxgkrnl.sh"
)

# Build full paths for the source files
$SourceFiles = $FilesToTransfer | ForEach-Object { Join-Path -Path $ScriptDir -ChildPath $_ }

Write-Host "Transferring files to $Target..."

# scp uses the files and target. 
# PowerShell passes the array $SourceFiles as separate arguments.
& scp.exe -r $SourceFiles "$($Target):~/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Transfer completed successfully." -ForegroundColor Green
}
else {
    Write-Error "Transfer failed with exit code $LASTEXITCODE"
}
