$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$UvVersion = "0.11.31"
$SourceUrl = "https://github.com/matteodante/therapist/archive/refs/heads/main.zip"

if ($env:OS -ne "Windows_NT") {
    throw "This installer is for Windows. Use install.sh on macOS or Linux."
}
if (-not [Environment]::UserInteractive) {
    throw "Therapist setup requires an interactive terminal."
}

$UvCommand = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
if ($null -eq $UvCommand) {
    Write-Host "Installing uv $UvVersion..."
    Invoke-RestMethod "https://astral.sh/uv/$UvVersion/install.ps1" | Invoke-Expression
    $Uv = Join-Path $HOME ".local\bin\uv.exe"
    if (-not (Test-Path -LiteralPath $Uv -PathType Leaf)) {
        throw "uv was installed but could not be found at $Uv."
    }
} else {
    $Uv = $UvCommand.Source
}

$TemporaryDirectory = Join-Path ([IO.Path]::GetTempPath()) (
    "therapist-install-" + [Guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $TemporaryDirectory | Out-Null

try {
    $Archive = Join-Path $TemporaryDirectory "therapist.zip"
    $SourceDirectory = Join-Path $TemporaryDirectory "source"

    Write-Host "Downloading Therapist from main..."
    Invoke-WebRequest -Uri $SourceUrl -OutFile $Archive
    Expand-Archive -LiteralPath $Archive -DestinationPath $SourceDirectory
    $ProjectDirectory = Get-ChildItem -LiteralPath $SourceDirectory -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "pyproject.toml") } |
        Select-Object -First 1
    if ($null -eq $ProjectDirectory) {
        throw "The downloaded Therapist source is incomplete."
    }

    Write-Host "Installing Therapist..."
    & $Uv tool install --python 3.12 $ProjectDirectory.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "uv could not install Therapist."
    }
    & $Uv tool update-shell
    if ($LASTEXITCODE -ne 0) {
        throw "uv could not add its tool directory to PATH."
    }

    $ToolBin = (& $Uv tool dir --bin | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "uv could not locate its tool directory."
    }
    $Thera = Join-Path $ToolBin "thera.exe"
    if (-not (Test-Path -LiteralPath $Thera -PathType Leaf)) {
        throw "Therapist was installed but $Thera is unavailable."
    }

    & $Thera setup
    if ($LASTEXITCODE -ne 0) {
        throw "Therapist setup did not complete."
    }
    & $Thera doctor
    if ($LASTEXITCODE -ne 0) {
        throw "Therapist doctor reported an error."
    }

    Write-Host ""
    Write-Host "Therapist is ready. Start it with: thera chat"
    Write-Host "If thera is not found in a new command, restart PowerShell."
} finally {
    Remove-Item -LiteralPath $TemporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue
}
