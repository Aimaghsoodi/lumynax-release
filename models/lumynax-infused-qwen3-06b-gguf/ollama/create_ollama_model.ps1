param(
    [string]$ModelName = "lumynax-infused-qwen3-06b-gguf"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelfilePath = Join-Path $scriptDir "Modelfile"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "The `ollama` CLI is not installed. Install Ollama first."
}

& ollama create $ModelName -f $modelfilePath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Output "Created Ollama model: $ModelName"
Write-Output "Run it with: ollama run $ModelName"
