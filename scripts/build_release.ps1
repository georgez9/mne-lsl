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
$SmokeReport = Join-Path $ProjectRoot "build\smoke-test.txt"

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
    $PreviousSmokeReport = $env:LSL_RECORDER_SMOKE_REPORT
    try {
        $env:LSL_RECORDER_DATA_DIR = Join-Path $ProjectRoot "build\smoke-data"
        $env:LSL_RECORDER_SMOKE_REPORT = $SmokeReport
        if (Test-Path -LiteralPath $SmokeReport) {
            Remove-Item -LiteralPath $SmokeReport -Force
        }
        $Process = Start-Process -FilePath $Executable -ArgumentList "--smoke-test" -PassThru
        if (-not $Process.WaitForExit(60000)) {
            $Process.Kill()
            $Process.WaitForExit()
            $Progress = if (Test-Path -LiteralPath $SmokeReport) {
                Get-Content -LiteralPath $SmokeReport -Raw
            } else {
                "No smoke-test progress report was created."
            }
            throw "Packaged application smoke test timed out after: $Progress"
        }
        $Report = if (Test-Path -LiteralPath $SmokeReport) {
            Get-Content -LiteralPath $SmokeReport -Raw
        } else {
            "Smoke test did not create a diagnostic report."
        }
        if ($Process.ExitCode -ne 0 -or $Report.Trim() -ne "OK") {
            throw "Packaged application smoke test failed:`n$Report"
        }
    }
    finally {
        $env:LSL_RECORDER_DATA_DIR = $PreviousDataDirectory
        $env:LSL_RECORDER_SMOKE_REPORT = $PreviousSmokeReport
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
