param(
    [Parameter(Mandatory = $true)]
    [string]$FmRoot,

    [switch]$Install
)

$ErrorActionPreference = "Stop"
$project = Join-Path $PSScriptRoot "FMFaceStudioBridge\FMFaceStudioBridge.csproj"
$fmExe = Join-Path $FmRoot "fm.exe"

if (-not (Test-Path $fmExe)) {
    throw "fm.exe was not found beneath: $FmRoot"
}

$env:FM26_ROOT = (Resolve-Path $FmRoot).Path
Write-Host "Building FM FaceStudio Bridge against $env:FM26_ROOT"
dotnet build $project -c Release

$dll = Join-Path $PSScriptRoot "FMFaceStudioBridge\bin\Release\net6.0\FMFaceStudioBridge.dll"
if (-not (Test-Path $dll)) {
    throw "Build completed without producing $dll"
}

Write-Host "Built: $dll"

if ($Install) {
    $destination = Join-Path $FmRoot "BepInEx\plugins\FMFaceStudioBridge"
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Force $dll (Join-Path $destination "FMFaceStudioBridge.dll")
    Write-Host "Installed to: $destination"
    Write-Host "Restart Football Manager and look for 'FM FaceStudio Bridge 0.1.0 loading' in LogOutput.log."
}
