#!/usr/bin/env pwsh

# Configuration defaults
$VenvDir = ".venv.gdrive-get"
$EnvFile = ".env.gdrive-get"
$ModelsYamlDriveId = ""
$DatasetsYamlDriveId = ""

# Load Environment Variables from .env.gdrive-get
if (Test-Path $EnvFile) {
    foreach ($line in Get-Content $EnvFile) {
        $line = $line.Trim()
        # Ignore comments and empty lines
        if ($line -match '^\s*#' -or $line -eq '') { continue }

        $parts = $line -split '=', 2
        if ($parts.Count -lt 2) { continue }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim() -replace '^["'']' -replace '["'']$'

        switch ($key) {
            'VENV_DIR'              { $VenvDir = $value }
            'MODELS_YAML_DRIVE_ID'  { $ModelsYamlDriveId = $value }
            'DATASETS_YAML_DRIVE_ID'{ $DatasetsYamlDriveId = $value }
        }
    }
} else {
    Write-Host "Error: Environment file $EnvFile not found, generating one..."
    Write-Host "Please edit the generated file to set your environment variables."
    "VENV_DIR=$VenvDir"           | Out-File -FilePath $EnvFile -Encoding utf8
    "MODELS_YAML_DRIVE_ID="      | Out-File -FilePath $EnvFile -Encoding utf8 -Append
    "DATASETS_YAML_DRIVE_ID="    | Out-File -FilePath $EnvFile -Encoding utf8 -Append
    exit 1
}

# Locate Python / pip in venv
$PipExeWin    = Join-Path $VenvDir "Scripts\pip.exe"
$PythonExeWin = Join-Path $VenvDir "Scripts\python.exe"
$PipExeUnix   = Join-Path $VenvDir "bin/pip"
$PythonExeUnix= Join-Path $VenvDir "bin/python"

if (-not (Test-Path $VenvDir)) {
    Write-Host "Error: Virtual environment $VenvDir does not exist."
    Write-Host "Please create it first via: python -m venv $VenvDir (or using third-party tools)"
    exit 1
}

if ((Test-Path $PythonExeWin) -and (Test-Path $PipExeWin)) {
    $PythonExe = $PythonExeWin
    $PipExe    = $PipExeWin
} elseif ((Test-Path $PythonExeUnix) -and (Test-Path $PipExeUnix)) {
    $PythonExe = $PythonExeUnix
    $PipExe    = $PipExeUnix
} else {
    Write-Host "Error: Python executable not found in $VenvDir."
    exit 1
}

# Ensure dependencies
$null = & $PipExe show gdown 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "gdown not found. Installing..."
    & $PipExe install gdown -q
}
$null = & $PipExe show PyYAML 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyYAML not found. Installing..."
    & $PipExe install PyYAML -q
}

# Usage function
function Show-Usage {
    $scriptName = $MyInvocation.ScriptName
    if (-not $scriptName) { $scriptName = "gdrive-get.ps1" }
    Write-Host "Usage: $scriptName [OPTIONS] [name]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -m, --model       Operate on Models"
    Write-Host "  -d, --dataset     Operate on Datasets"
    Write-Host "  -ls, --list       List available files"
    Write-Host "  -o, --output DIR  Specify output file or directory"
    Write-Host "  -x, --extract     Extract the downloaded file automatically"
    Write-Host "  -h, --help        Show this help message and exit"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  $scriptName -m -ls"
    Write-Host "  $scriptName --dataset my-dataset --output data/datasets/ --extract"
}

if ($args.Count -eq 0) {
    Show-Usage
    exit 0
}

# Parse Arguments
$Mode       = ""
$List       = $false
$TargetName = ""
$OutputArg  = ""
$Extract    = $false

$i = 0
while ($i -lt $args.Count) {
    switch ($args[$i]) {
        { $_ -in '-h', '--help' } {
            Show-Usage
            exit 0
        }
        { $_ -in '-m', '--model' } {
            $Mode = "model"
        }
        { $_ -in '-d', '--dataset' } {
            $Mode = "dataset"
        }
        { $_ -in '-ls', '--list' } {
            $List = $true
        }
        { $_ -in '-o', '--output' } {
            $i++
            $OutputArg = $args[$i]
        }
        { $_ -in '-x', '--extract' } {
            $Extract = $true
        }
        default {
            if ($args[$i] -like '-*') {
                Write-Host "Error: Unknown option: $($args[$i])"
                Show-Usage
                exit 1
            }
            $TargetName = $args[$i]
        }
    }
    $i++
}

if ($Mode -eq "") {
    Write-Host "Error: You must specify a mode (-m or -d)."
    Show-Usage
    exit 1
}

if (-not $List -and $TargetName -eq "") {
    Write-Host "Error: No target name specified."
    Show-Usage
    exit 1
}

# Determine Drive ID
$DriveId = ""
if ($Mode -eq "model") {
    $DriveId = $ModelsYamlDriveId
} elseif ($Mode -eq "dataset") {
    $DriveId = $DatasetsYamlDriveId
}

if ($DriveId -eq "") {
    Write-Host "Error: Values for $Mode Drive ID not found in $EnvFile"
    exit 1
}

# Temp file for Python to write the final output path to
$OutputPathFile = ".last_dl_path"

# Python script to Fetch Config, Parse, and Print/Download
$PythonScript = @"
import sys
import tempfile
import os
import gdown
import yaml

drive_id = '$DriveId'
mode = '$Mode'
do_list = '$($List.ToString().ToLower())'
target_name = '$TargetName'
output_arg = '$($OutputArg -replace '\\', '/')'
output_path_file = '$OutputPathFile'

def get_metadata_entries(metadata):
    for key in ['models', 'datasets', 'files']:
        if key in metadata:
            return metadata[key]
    return None

try:
    # 1. Download metadata to temp
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as tmp:
        temp_path = tmp.name

    print(f'Fetching {mode} metadata...')
    url = f'https://drive.google.com/uc?id={drive_id}'
    gdown.download(url, temp_path, quiet=True, fuzzy=True)

    with open(temp_path, 'r') as f:
        metadata = yaml.safe_load(f)

    if os.path.exists(temp_path):
        os.remove(temp_path)

    entries = get_metadata_entries(metadata)
    if not entries:
        print('Error: no entries found in metadata')
        sys.exit(1)

    # Convert dict to list if needed
    if isinstance(entries, dict):
        new_entries = []
        for k, v in entries.items():
            v['name'] = k
            new_entries.append(v)
        entries = new_entries

    # 2. Execute Action
    if do_list == 'true':
        print(f'\nAvailable {mode}s:')
        for e in entries:
            name = e.get('name', 'Unknown')
            desc = e.get('description', e.get('desc', ''))
            print(f' - {name}: {desc}')

    elif target_name:
        found = None
        for e in entries:
            if e.get('name') == target_name:
                found = e
                break

        if not found:
            print(f'Error: {target_name} not found in metadata.')
            sys.exit(1)

        file_id = found.get('id')
        default_output = found.get('output', found.get('name', target_name))

        final_output = default_output
        if output_arg:
            if os.path.isdir(output_arg) or output_arg.endswith('/') or output_arg.endswith('\\\\'):
                os.makedirs(output_arg, exist_ok=True)
                final_output = os.path.join(output_arg, default_output)
            else:
                parent_dir = os.path.dirname(os.path.abspath(output_arg))
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                final_output = output_arg

        if not file_id:
             print('Error: ID missing for item.')
             sys.exit(1)

        print(f'Downloading {target_name} -> {final_output}...')
        dl_url = f'https://drive.google.com/uc?id={file_id}'
        gdown.download(dl_url, final_output, quiet=False, fuzzy=True)

        with open(output_path_file, 'w') as f:
            f.write(os.path.abspath(final_output))

except Exception as e:
    print(f'An error occurred: {e}')
    sys.exit(1)
"@

# Execute the python logic
& $PythonExe -c $PythonScript
$PyExitCode = $LASTEXITCODE

# If Python succeeded and Extract is requested
if ($PyExitCode -eq 0 -and $Extract -and -not $List) {
    if (Test-Path $OutputPathFile) {
        $DownloadedFile = (Get-Content $OutputPathFile).Trim()

        if (Test-Path $DownloadedFile) {
            $DirName = Split-Path $DownloadedFile -Parent
            $Extension = [System.IO.Path]::GetExtension($DownloadedFile).ToLower()

            switch -Regex ($Extension) {
                '\.zip$' {
                    Write-Host "Unzipping $DownloadedFile..."
                    Expand-Archive -Path $DownloadedFile -DestinationPath $DirName -Force
                }
                '\.(tar\.gz|tgz|tar)$' {
                    Write-Host "Extracting tarball $DownloadedFile..."
                    tar -xf $DownloadedFile -C $DirName
                }
                '\.(gz)$' {
                    # Single .gz file (not .tar.gz, already handled above)
                    Write-Host "Extracting gzip $DownloadedFile..."
                    tar -xf $DownloadedFile -C $DirName
                }
                default {
                    Write-Host "Warning: extension '$Extension' not supported for auto-extraction."
                }
            }
        }
    }
}

# Cleanup temp file
if (Test-Path $OutputPathFile) {
    Remove-Item $OutputPathFile
}

exit $PyExitCode
