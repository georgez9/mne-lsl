param(
    [string]$Python = "python",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Executable = Join-Path $ProjectRoot "dist\LSLRecorder.exe"
$Checksum = "$Executable.sha256"
$ThirdPartyLicenses = Join-Path $ProjectRoot "dist\THIRD_PARTY_LICENSES.txt"
$ProjectLicense = Join-Path $ProjectRoot "dist\PROJECT_LICENSE.txt"

Push-Location $ProjectRoot
try {
    if (-not $SkipTests) {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed."
        }
    }

    & $Python -m PyInstaller --clean --noconfirm build_tools\lsl_recorder.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }
    if (-not (Test-Path -LiteralPath $Executable)) {
        throw "Expected executable was not created: $Executable"
    }

    $PreviousDataDirectory = $env:LSL_RECORDER_DATA_DIR
    try {
        $env:LSL_RECORDER_DATA_DIR = Join-Path $ProjectRoot "build\smoke-data"
        & $Executable --smoke-test
        if ($LASTEXITCODE -ne 0) {
            throw "Packaged application smoke test failed."
        }
    }
    finally {
        $env:LSL_RECORDER_DATA_DIR = $PreviousDataDirectory
    }

    & $Python scripts\generate_third_party_licenses.py $ThirdPartyLicenses
    if ($LASTEXITCODE -ne 0) {
        throw "Third-party license collection failed."
    }
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination $ProjectLicense -Force
    $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Executable).Hash.ToLowerInvariant()
    "$Hash  LSLRecorder.exe" | Set-Content -LiteralPath $Checksum -Encoding ascii
    Write-Host "Release build ready: $Executable"
    Write-Host "License bundle: $ThirdPartyLicenses"
    Write-Host "Project license: $ProjectLicense"
    Write-Host "SHA256: $Hash"
}
finally {
    Pop-Location
}
