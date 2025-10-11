# curl-dataset.ps1
# This script downloads a specified dataset from OneDrive and unzips it into the datasets/
# Usage: .\curl-dataset.ps1 [-h] [-d <dataset-name>]

param(
    [string[]]$args
)

# Parse command line arguments
$showHelp = $false
$datasetName = ""
$datasetProvided = $false

# Handle case when no arguments provided
if ($args.Length -eq 0) {
    Write-Host "Error: -d option is required."
    exit 1
}

for ($i = 0; $i -lt $args.Length; $i++) {
    switch ($args[$i]) {
        "-h" { $showHelp = $true }
        "-d" { 
            $datasetProvided = $true
            if ($i + 1 -lt $args.Length) {
                $datasetName = $args[$i + 1]
                $i++
            } else {
                Write-Host "Error: -d option requires a dataset name argument."
                exit 1
            }
        }
        default {
            Write-Host "Unknown option: $($args[$i])"
            exit 1
        }
    }
}

# Create datasets directory if it doesn't exist
if (!(Test-Path "datasets")) {
    New-Item -ItemType Directory -Path "datasets" | Out-Null
}

# Check for help FIRST, before any validation
if ($showHelp) {
    Write-Host "Usage: .\curl-dataset.ps1 [--help|-h] [-d <dataset-name>]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -h            Show this help message and exit"
    Write-Host "  -d <dataset-name>     Specify the dataset to download"
    exit 0
}

# Then do validation only if help wasn't requested
if ($datasetProvided -and $datasetName -eq "") {
    Write-Host "Error: -d option requires a dataset name argument."
    exit 1
}

if (-not $datasetProvided) {
    Write-Host "Error: -d option is required."
    exit 1
}

if ($datasetName) {
    # Download datasets.yaml
    $headers = @{
        'accept' = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        'accept-language' = 'en-US,en;q=0.9'
        'cookie' = 'MSFPC=GUID=018d8352266641bfa8680659823058c3&HASH=018d&LV=202501&V=4&LU=1738235237094; rtFa=WO9c+3n+GWh27WpR1MWAc691lwh75C0QMpZdz6W4lmImNzdlMThiODctNTFkMy00OWUxLWIyODEtZGZkYTVhOTI2MDYxIzEzNDA0NjI3NTY2MDM0NDc3MyM2ZTM4Y2VhMS0zMGQ5LTUwMDAtZWVhOS1hMzJhNWQ2N2VkOGUjY29uY2VwY2lvbi50aW1vdGh5amFtZXMlNDB1ZS5lZHUucGgjMTk2MDEwI2dmYktidWJ6dXRzZ0NseGZpOV9rQ0g0TndYYyNnZmJLYnVienV0c2dDbHhmaTlfa0NINE53WGN12hbsUFZcwVe4kt9Y+KbLDkAxhxEbdXqV77f/cTgWi0mpPfzdODhX2u6rcSyQkn+SLa0yPz9Vbrr5K7utj0ExKH5JNMXftq5gIv9GXhqhmZNLjpj/ICo4hiZ6+J5TnsvjukbDVMRR8dinZscww4yVEvQFii5teYxCvjQTMLRijOXmROavqVtkS7xeWRLNGFHhfRpC1UqaVN2UFGN2OE1jkK+WWxcmNtpa1gHjyPa/Ilhc/4tbRPzmix4RDZfeuFH+yUHjb1wlk+csky0va4ZwzDwNSTFu8Gm+MoPc1xFaH9wQ9No0W1byJB9vh1Uh4y9iHQWHc5W84Mwdyb7YO+hg4AAAAA==; SIMI=eyJzdCI6MH0=; FedAuth=77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjE0LDBoLmZ8bWVtYmVyc2hpcHwxMDAzMjAwMmNmYWFmOTFlQGxpdmUuY29tLDAjLmZ8bWVtYmVyc2hpcHxjb25jZXBjaW9uLnRpbW90aHlqYW1lc0B1ZS5lZHUucGgsMTM0MDA2OTQ2MjcwMDAwMDAwLDEzMzM1NjAyNDQxMDAwMDAwMCwxMzQwNTA1OTU2NjAxODc4ODMsMTM2LjE1OC42MS4xOTgsNjcsNzdlMThiODctNTFkMy00OWUxLWIyODEtZGZkYTVhOTI2MDYxLCwwMDdiYzc5OS03YmZmLThjOWQtMTA1Zi04ODIyMTE3NWE5MGEsNmUzOGNlYTEtMzBkOS01MDAwLWVlYTktYTMyYTVkNjdlZDhlLDZlMzhjZWExLTMwZDktNTAwMC1lZWE5LWEzMmE1ZDY3ZWQ4ZSwsMCwxMzQwNDcxMzk2NjAwMzE1OTYsMTM0MDQ4ODY3NjYwMDMxNTk2LCwsZXlKNGJYTmZZMk1pT2lKYlhDSkRVREZjSWwwaUxDSjRiWE5mYzNOdElqb2lNU0lzSW5CeVpXWmxjbkpsWkY5MWMyVnlibUZ0WlNJNkltTnZibU5sY0dOcGIyNHVkR2x0YjNSb2VXcGhiV1Z6UUhWbExtVmtkUzV3YUNJc0luVjBhU0k2SW1FMVVqRjBVbXQwTjJ0eE9GOWhOMGMyTUVoVFFVRWlMQ0poZFhSb1gzUnBiV1VpT2lJeE16UXdNRFk1TkRZeU56QXdNREF3TURBaWZRPT0sMjY1MDQ2Nzc0Mzk5OTk5OTk5OSwxMzQwNDYyNzU2NTAwMDAwMDAsNjgxOGY5ZGYtM2I3Ny00NTI5LWIzMmEtZWI5OTE2M2FmYTU4LCwsLCwsMTE1MjkyMTUwNDYwNjg0Njk3NiwsMTk2MDEwLHJMSFBYbWZOcnlzVVBfZ3hrbzd1VzJoSnRaMCwsTEhodVpoU01FaGNMN0x6WkhyRDZNa2k3TG53YkgvMHllSGRFTmZ2dks5ckhkQlBDdGF6U0ZiOXgxRWJCNkhkWnlPVE4ydldjQVRNY3Fkb0NRYlJ1UWVZMDdUQUhubENzaDdObE40RGhPMWJVSGh5WEphbzNuTEhNMEhPZnhUWmZkYUVqQ1l0bmZIbTdIYzZxTlR6RUJRYS9QcEJKdnBWcHpycHNHU3VoeUZSazc5ZVdFdUlwRWpjWkRLRitJVThaRndqMkdWZEFuSDV2alY2dTJNNmY4enZ6K1FUak02MXIvV3cweVVxTTRvdEpHdDMwdlVZV1ZBSnlrUS9ZMlpZSk9OZ1RMRHg3bzE4ZXcvT2txSTRIaUUwSDY0bEJVRWcvd2wyNlRGemNIQkRxQmNzNEVqZ1U0NitqTnBEbTdVemwydWtKL3o0bTBtbFpTQmlJQzFpdWdnPT08L1NQPg==; FeatureOverrides_experiments=[]; msal.cache.encryption=%7B%22id%22%3A%220199d1b4-f122-7fbc-9428-e22afa0e1d92%22%2C%22key%22%3A%22EtQ4ugS0fVUhLlA3mw3rd8vB__NRXSrXm23fpr4ZZmI%22%7D; MicrosoftApplicationsTelemetryDeviceId=1fcfbe4b-a76f-464a-8c36-a0b2e9904a86; SPA_RT=; ai_session=u7e6fZP0ZRdoS/DI85uvyY|1760159917922|1760160416999'
        'dnt' = '1'
        'if-none-match' = '"{C2BABEED-5EEC-479A-A8DF-318C9EB7200D},12"'
        'priority' = 'u=0, i'
        'referer' = 'https://ueeduph-my.sharepoint.com/my?id=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets%2Fdatasets%2Eyaml&parent=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets&ga=1'
        'sec-ch-ua' = '"Not?A_Brand";v="99", "Chromium";v="130"'
        'sec-ch-ua-mobile' = '?0'
        'sec-ch-ua-platform' = '"Windows"'
        'sec-fetch-dest' = 'iframe'
        'sec-fetch-mode' = 'navigate'
        'sec-fetch-site' = 'same-origin'
        'sec-fetch-user' = '?1'
        'sec-gpc' = '1'
        'service-worker-navigation-preload' = '{"supportsFeatures":[1855,61313,62475]}'
        'upgrade-insecure-requests' = '1'
        'user-agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }

    $url = 'https://ueeduph-my.sharepoint.com/personal/concepcion_timothyjames_ue_edu_ph/_layouts/15/download.aspx?SourceUrl=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets%2Fdatasets%2Eyaml'
    
    try {
        $datasetsYaml = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing
        $yamlContent = [System.Text.Encoding]::UTF8.GetString($datasetsYaml.Content)
    }
    catch {
        Write-Host "Error downloading datasets.yaml: $_"
        exit 1
    }

    # Alternative: Parse YAML manually using string operations to get curl_pwsh
    $lines = $yamlContent -split '\r?\n'
    $curlPwshCmd = ""
    $inCurlPwshBlock = $false
    $inTargetDataset = $false
    
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        
        # Check if we found our dataset
        if ($line -match "^\s*- name:\s+$([regex]::Escape($datasetName))") {
            $inTargetDataset = $true
            continue
        }
        
        # If we're in the target dataset and find curl_pwsh block
        if ($inTargetDataset -and $line -match "^\s*curl_pwsh:\s*\|") {
            $inCurlPwshBlock = $true
            continue
        }
        
        # If we're in curl_pwsh block, collect lines until we hit next key or dataset
        if ($inCurlPwshBlock) {
            if ($line -match "^\s{4}\w" -or $line -match "^\s{2}-") {
                # Hit next key or dataset, stop collecting
                break
            }
            if ($line -match "^\s{6}") {
                # This is a PowerShell command line, add it
                $curlPwshCmd += ($line -replace "^\s{6}", "") + "`n"
            }
        }
    }
    
    $curlPwshCmd = $curlPwshCmd.Trim()
    
    if ([string]::IsNullOrWhiteSpace($curlPwshCmd)) {
        Write-Host "Error: Dataset '$datasetName' not found or does not have a curl_pwsh command."
        exit 1
    }

    # Add -OutFile parameter to the PowerShell command
    $outputFile = "datasets\$datasetName"
    $curlPwshCmd += " -OutFile `"$outputFile`""

    Write-Host "Downloading dataset '$datasetName'..."
    
    # Execute the PowerShell command
    try {
        Invoke-Expression $curlPwshCmd
        Write-Host "Download completed successfully."
    }
    catch {
        Write-Host "Error downloading dataset: $_"
        exit 1
    }

    # Unzip and cleanup
    if (Test-Path $outputFile) {
        $extractPath = "datasets"
        Write-Host "Extracting to: $extractPath"
        
        Expand-Archive -Path $outputFile -DestinationPath $extractPath -Force
        Remove-Item $outputFile
        Write-Host "Dataset '$datasetName' downloaded and extracted successfully."
    }
    else {
        Write-Host "Error: Dataset file was not downloaded to expected location: $outputFile"
        exit 1
    }

    exit 0
}