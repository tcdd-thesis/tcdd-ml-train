# Check if .env file exists
$env_file = ".env.hef-conversion-hyperv"
if (-not (Test-Path $env_file)) {
    Write-Host "Missing env file, creating..."
    Write-Host "Please edit $env_file file with VM name and try again"
    "VM_NAME=your-vm-name-here" | Out-File -FilePath $env_file -Encoding utf8
    "WSL2_BRANCH=linux-msft-wsl-5.15.y" | Add-Content -Path $env_file -Encoding utf8
    exit
}

# Get VM name from .env file
$vm = Get-Content -Path $env_file | Select-String -Pattern "VM_NAME=" | ForEach-Object { $_.Line.Split('=')[1].Trim() }

if (Get-VMGpuPartitionAdapter -VMName $vm -ErrorAction SilentlyContinue) {
        Remove-VMGpuPartitionAdapter -VMName $vm
}

Set-VM -GuestControlledCacheTypes $true -VMName $vm
Set-VM -LowMemoryMappedIoSpace 1Gb -VMName $vm
Set-VM -HighMemoryMappedIoSpace 8Gb -VMName $vm

Add-VMGpuPartitionAdapter -VMName $vm
