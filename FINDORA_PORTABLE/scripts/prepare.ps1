$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root 'runtime'
$PythonDir = Join-Path $Runtime 'python'
$LlamaDir = Join-Path $Runtime 'llama'
$ModelDir = Join-Path $Root 'models'
$Downloads = Join-Path $Runtime 'downloads'
foreach ($d in @($PythonDir,$LlamaDir,$ModelDir,$Downloads,(Join-Path $Root 'logs'),(Join-Path $Root 'data'))) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
function Download-Resume([string]$Url,[string]$Path,[long]$MinBytes) {
 if ((Test-Path $Path) -and ((Get-Item $Path).Length -ge $MinBytes)) { Write-Host "Verified by size threshold: $Path"; return }
 if (!(Test-Path $Path)) { New-Item -ItemType File -Path $Path -Force | Out-Null }
 if (Test-Path $Path) { Write-Host "Resuming incomplete file if possible: $Path" }
 # Probe final response headers when available so a partial multi-GB file is not
 # mistaken for a completed model simply because it crossed a minimum threshold.
 $expected = 0L
 try {
   $headers = & curl.exe -sIL --max-time 45 $Url
   foreach ($line in $headers) { if ($line -match '(?i)^(content-length|x-linked-size):\s*(\d+)\s*$') { $expected = [long]$Matches[2] } }
 } catch { $expected = 0L }
 Write-Host "Downloading: $Url"
 & curl.exe -L --fail --retry 5 --retry-delay 2 -C - -o $Path $Url
 if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
 $actual = if (Test-Path $Path) { (Get-Item $Path).Length } else { 0L }
 if ($actual -lt $MinBytes) { throw "Download file is incomplete or too small: $Path ($actual bytes)" }
 if ($expected -gt 0 -and $actual -ne $expected) { throw "Download incomplete: $Path ($actual of $expected bytes)" }
}
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB,1)
Write-Host "Detected RAM: $ramGB GB"
if ($ramGB -lt 12) { Write-Warning 'AI model may be slow or unavailable on systems with less than 12 GB RAM.' }
$pyZip = Join-Path $Downloads 'python-3.12.10-embed-amd64.zip'
Download-Resume 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' $pyZip 10000000
if (!(Test-Path (Join-Path $PythonDir 'python.exe'))) {
 Expand-Archive -Path $pyZip -DestinationPath $PythonDir -Force
 $pth = Join-Path $PythonDir 'python312._pth'
 if (Test-Path $pth) { $lines = Get-Content $pth; $lines = $lines -replace '^#import site','import site'; Set-Content $pth $lines }
}
# Fixed versioned mirror URL: no latest-release API scraping. Asset URL is still
# validated by HTTP status and size on the user's PC before extraction.
$llamaUrl = 'https://github.com/cloudlnkcn/llama.cpp/releases/download/v0.9.0/llama-v0.9.0-bin-win-cpu-x64.zip'
$llamaZip = Join-Path $Downloads 'llama-cpu-win-x64.zip'
Download-Resume $llamaUrl $llamaZip 15000000
if (!(Test-Path (Join-Path $LlamaDir 'llama-server.exe'))) {
 $extractTmp = Join-Path $Runtime 'llama_extract'
 if (Test-Path $extractTmp) { Remove-Item $extractTmp -Recurse -Force }
 New-Item -ItemType Directory -Force -Path $extractTmp | Out-Null
 Expand-Archive -Path $llamaZip -DestinationPath $extractTmp -Force
 $exe = Get-ChildItem $extractTmp -Recurse -Filter 'llama-server.exe' | Select-Object -First 1
 if (!$exe) { throw 'llama-server.exe not found inside the runtime ZIP.' }
 Copy-Item $exe.FullName $LlamaDir -Force
 Get-ChildItem $exe.DirectoryName -Filter '*.dll' | Copy-Item -Destination $LlamaDir -Force
 Remove-Item $extractTmp -Recurse -Force
}
# Optional model install: Qwen 2.5 7B Instruct Q5_K_M, ~5-6GB.
$modelPath = Join-Path $ModelDir 'qwen-7b-q5.gguf'
if (!(Test-Path $modelPath) -or ((Get-Item $modelPath).Length -lt 4500000000)) {
 $modelUrl = 'https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q5_K_M.gguf'
 Download-Resume $modelUrl $modelPath 5100000000
}
# Initialize persistent database and run lightweight checks
& (Join-Path $PythonDir 'python.exe') (Join-Path $Root 'app\server.py') --init-only
if ($LASTEXITCODE -ne 0) { throw 'Findora database initialization failed.' }
Write-Host 'Setup completed. Launch with START.bat.'
