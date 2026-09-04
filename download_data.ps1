$ProgressPreference = 'SilentlyContinue'
$url = "https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php"
$outPath = ".\data"

if (!(Test-Path $outPath)) {
    New-Item -ItemType Directory -Force -Path $outPath | Out-Null
}

for ($year = 2001; $year -le 2025; $year++) {
    $body = @{
        rain = $year.ToString()
    }
    Write-Host "Downloading data for $year..."
    try {
        $response = Invoke-WebRequest -Uri $url -Method Post -Body $body
        $filename = "ind$year`_rfp25.grd"
        
        # Try to get filename from Content-Disposition if it exists
        if ($response.Headers.Contains("Content-Disposition")) {
            $cd = $response.Headers["Content-Disposition"]
            if ($cd -match 'filename="?([^"]+)"?') {
                $filename = $matches[1]
            }
        }
        
        $filePath = Join-Path $outPath $filename
        
        # Write bytes to file
        [System.IO.File]::WriteAllBytes($filePath, $response.Content)
        
        Write-Host "Successfully saved $filename"
    } catch {
        Write-Host "Failed to download $year`: $_"
    }
}
Write-Host "Download complete."
