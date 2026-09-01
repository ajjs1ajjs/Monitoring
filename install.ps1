# PyMon NOC (Go) - one-line installer/updater (Windows)
# The SAME command installs on first run and safely UPDATES on subsequent runs:
#   - keeps config (%ProgramData%\PyMon\config.yml), database, users and admin password
#   - replaces only the binary and restarts the Windows Service
# Usage (elevated PowerShell / "Run as Administrator"):
#   irm https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1 | iex
# Install a specific version:
#   $env:PYMON_VERSION = "v3.1.1"; irm .../install.ps1 | iex

$ErrorActionPreference = "Stop"

$ServiceName = "PyMonNOC"
$Repo        = "ajjs1ajjs/Monitoring"
$InstallDir  = Join-Path $env:ProgramFiles "PyMon"
$DataDir     = Join-Path $env:ProgramData "PyMon"
$ConfigFile  = Join-Path $DataDir "config.yml"
$DbFile      = Join-Path $DataDir "pymon.db"
$LogDir      = Join-Path $DataDir "logs"
$BinaryPath  = Join-Path $InstallDir "pymon.exe"
$Version     = if ($env:PYMON_VERSION) { $env:PYMON_VERSION } else { "latest" }

# --- Must run elevated -------------------------------------------------------
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: this script must be run from an elevated PowerShell (Run as Administrator)." -ForegroundColor Red
    exit 1
}

# --- Detect existing installation -------------------------------------------
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
$IsUpdate = [bool]($existingService -or (Test-Path $BinaryPath) -or (Test-Path $DbFile))

if ($IsUpdate) { $Mode = "Оновлення (update)" } else { $Mode = "Встановлення (install)" }
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   PyMon NOC - $Mode" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$OldVersion = ""
if (Test-Path $BinaryPath) {
    try { $OldVersion = (& $BinaryPath --version) 2>$null } catch { $OldVersion = "" }
}

# --- Architecture detection ---------------------------------------------------
$archRaw = $env:PROCESSOR_ARCHITECTURE
if ($env:PROCESSOR_ARCHITEW6432) { $archRaw = $env:PROCESSOR_ARCHITEW6432 }
switch ($archRaw) {
    "AMD64" { $Arch = "amd64" }
    "ARM64" { $Arch = "arm64" }
    default {
        Write-Host "ERROR: unsupported architecture: $archRaw" -ForegroundColor Red
        Write-Host "Supported: AMD64, ARM64"
        exit 1
    }
}
$BinaryName = "pymon-windows-$Arch.exe"

if ($Version -eq "latest") {
    $DownloadUrl = "https://github.com/$Repo/releases/latest/download/$BinaryName"
    $ChecksumUrl = "https://github.com/$Repo/releases/latest/download/checksums.txt"
} else {
    $DownloadUrl = "https://github.com/$Repo/releases/download/$Version/$BinaryName"
    $ChecksumUrl = "https://github.com/$Repo/releases/download/$Version/checksums.txt"
}

# --- Download ------------------------------------------------------------------
Write-Host "[1/5] Downloading PyMon $Version ($BinaryName)..." -ForegroundColor Yellow
$tmpBin = Join-Path $env:TEMP "$BinaryName.$(Get-Random)"
try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $tmpBin -UseBasicParsing
} catch {
    Write-Host "ERROR: download failed. Is release '$Version' published for Windows/$Arch?" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

# --- Verify SHA-256 checksum ----------------------------------------------------
Write-Host "Verifying checksum..." -ForegroundColor Yellow
$tmpSum = Join-Path $env:TEMP "pymon-checksums.$(Get-Random).txt"
$checksumOk = $false
try {
    Invoke-WebRequest -Uri $ChecksumUrl -OutFile $tmpSum -UseBasicParsing -ErrorAction Stop
    $checksumOk = $true
} catch {
    Write-Host "Warning: could not download checksums.txt, skipping verification." -ForegroundColor Yellow
}
if ($checksumOk) {
    $line = Select-String -Path $tmpSum -Pattern ([regex]::Escape($BinaryName)) -SimpleMatch:$false | Select-Object -First 1
    if ($line) {
        $expected = ($line.Line -split '\s+')[0].Trim().ToLower()
        $actual = (Get-FileHash -Path $tmpBin -Algorithm SHA256).Hash.ToLower()
        if ($expected -ne $actual) {
            Write-Host "ERROR: checksum mismatch for $BinaryName." -ForegroundColor Red
            Write-Host "  expected: $expected"
            Write-Host "  actual:   $actual"
            Remove-Item $tmpBin, $tmpSum -ErrorAction SilentlyContinue
            exit 1
        }
        Write-Host "Checksum OK." -ForegroundColor Green
    } else {
        Write-Host "Warning: no checksum entry for $BinaryName, skipping verification." -ForegroundColor Yellow
    }
    Remove-Item $tmpSum -ErrorAction SilentlyContinue
}

# Verify it's a valid PE binary and actually runs.
$bytes = [System.IO.File]::ReadAllBytes($tmpBin) | Select-Object -First 2
if (-not ($bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A)) {
    Write-Host "ERROR: downloaded file is not a valid PE binary." -ForegroundColor Red
    Remove-Item $tmpBin -ErrorAction SilentlyContinue
    exit 1
}
try {
    $NewVersion = (& $tmpBin --version) 2>$null
    if (-not $NewVersion) { throw "empty version output" }
} catch {
    Write-Host "ERROR: downloaded file is not a valid PyMon binary." -ForegroundColor Red
    Remove-Item $tmpBin -ErrorAction SilentlyContinue
    exit 1
}

# --- Install binary --------------------------------------------------------
Write-Host "[2/5] Installing binary to $BinaryPath..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

if ($existingService -and $existingService.Status -eq "Running") {
    Write-Host "Stopping service $ServiceName..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    # Give the process a moment to release the binary file handle.
    Start-Sleep -Seconds 2
}

# On update, keep a rollback copy of the previous binary.
if ($IsUpdate -and (Test-Path $BinaryPath)) {
    Copy-Item -Path $BinaryPath -Destination "$BinaryPath.old" -Force -ErrorAction SilentlyContinue
}

Move-Item -LiteralPath $tmpBin -Destination $BinaryPath -Force

try {
    & $BinaryPath --version | Out-Null
} catch {
    Write-Host "ERROR: installed binary at $BinaryPath is not runnable." -ForegroundColor Red
    if (Test-Path "$BinaryPath.old") {
        Write-Host "Restoring previous version..." -ForegroundColor Yellow
        Copy-Item -Path "$BinaryPath.old" -Destination $BinaryPath -Force
    }
    exit 1
}

# --- Config (kept on update, only created on first install) -----------------
if (-not (Test-Path $ConfigFile)) {
    Write-Host "Creating default config at $ConfigFile ..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/$Repo/main/config.example.yml" `
            -OutFile $ConfigFile -UseBasicParsing
    } catch {
        Write-Host "Note: config.example.yml download skipped ($($_.Exception.Message))." -ForegroundColor Yellow
    }
}

# --- Windows Service ----------------------------------------------------------
Write-Host "[3/5] Configuring Windows Service..." -ForegroundColor Yellow

# NetworkService needs write access to DataDir/LogDir; it does not need any
# rights in ProgramFiles beyond read+execute, which are inherited by default.
$acl = Get-Acl $DataDir
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "NT AUTHORITY\NetworkService", "Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($rule)
Set-Acl -Path $DataDir -AclObject $acl

$binPathArg = '"' + $BinaryPath + '" service --config "' + $ConfigFile + '"'

if (-not $existingService) {
    New-Service -Name $ServiceName `
        -BinaryPathName $binPathArg `
        -DisplayName "PyMon NOC Monitoring" `
        -Description "PyMon NOC infrastructure monitoring server (https://github.com/$Repo)" `
        -StartupType Automatic | Out-Null
    # New-Service always runs as LocalSystem; drop privileges to NetworkService.
    & sc.exe config $ServiceName obj= "NT AUTHORITY\NetworkService" password= "" | Out-Null
    & sc.exe failure $ServiceName reset= 86400 actions= "restart/5000/restart/5000/restart/5000" | Out-Null
} else {
    # Binary path may change between versions/architectures; keep it in sync.
    & sc.exe config $ServiceName binPath= $binPathArg | Out-Null
}

# --- Admin password (fresh install only, unless PYMON_ADMIN_PASSWORD is set) -
$AdminSet = $false
$AdminPw = $null
if ($IsUpdate -and -not $env:PYMON_ADMIN_PASSWORD) {
    # update: keep existing credentials
} else {
    $env:DB_PATH = $DbFile
    $hasAdmin = "no"
    try { $hasAdmin = (& $BinaryPath has-admin --config $ConfigFile) 2>$null } catch { $hasAdmin = "no" }
    if ($hasAdmin -ne "yes" -or $env:PYMON_ADMIN_PASSWORD) {
        if ($env:PYMON_ADMIN_PASSWORD) {
            $AdminPw = $env:PYMON_ADMIN_PASSWORD
        } else {
            $bytes = New-Object byte[] 18
            [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
            $AdminPw = ([Convert]::ToBase64String($bytes) -replace '[^A-Za-z0-9]', '').Substring(0, 18)
        }
        $env:PYMON_ADMIN_PASSWORD = $AdminPw
        & $BinaryPath reset-admin --config $ConfigFile
        Set-Content -Path (Join-Path $DataDir "admin_password.txt") -Value $AdminPw -Encoding utf8
        $AdminSet = $true
    }
    Remove-Item Env:\DB_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:\PYMON_ADMIN_PASSWORD -ErrorAction SilentlyContinue
}

Write-Host "[4/5] Starting service..." -ForegroundColor Yellow
Start-Service -Name $ServiceName

# --- Health check -----------------------------------------------------------
Write-Host -NoNewline "Waiting for the service to become healthy..."
$healthy = $false
for ($i = 1; $i -le 15; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:10000/api/v1/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
}
if ($healthy) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "Check the service status: Get-Service $ServiceName"
    Write-Host "Check Windows Event Log (Application) for '$ServiceName' errors."
}

# --- Summary ------------------------------------------------------------------
Write-Host "[5/5] Done." -ForegroundColor Green
Write-Host ""
if ($IsUpdate) {
    Write-Host "PyMon NOC updated successfully." -ForegroundColor Green
    Write-Host "  Version: $(if ($OldVersion) { $OldVersion } else { '?' }) -> $NewVersion"
    Write-Host "  Config, database and users were preserved."
    if (Test-Path "$BinaryPath.old") { Write-Host "  Previous binary kept at: $BinaryPath.old" }
} else {
    Write-Host "PyMon NOC installed successfully." -ForegroundColor Green
    Write-Host "  Version: $NewVersion"
    Write-Host "  Config:   $ConfigFile"
    Write-Host "  Database: $DbFile"
    Write-Host "  Service:  Get-Service $ServiceName"
}
Write-Host ""
Write-Host "Dashboard: http://localhost:10000/"
Write-Host ""
if ($AdminSet) {
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "  Логін:    admin"
    Write-Host "  Пароль:   $AdminPw"
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "При вході дашборд попросить змінити пароль."
    Write-Host "Пароль також збережено: $(Join-Path $DataDir 'admin_password.txt') (видаліть після входу)"
    Write-Host "  Remove-Item '$(Join-Path $DataDir "admin_password.txt")'"
} elseif ($IsUpdate) {
    Write-Host "Існуючі облікові дані збережено (пароль не змінювався)."
    Write-Host "Якщо треба скинути пароль адміна:"
    Write-Host "  `$env:PYMON_ADMIN_PASSWORD = 'YourStrongPass123'; & '$BinaryPath' reset-admin --config '$ConfigFile'"
    Write-Host "  Restart-Service $ServiceName"
    Write-Host "  Логін: admin / YourStrongPass123"
}
Write-Host ""
Write-Host "Installed version: $(& $BinaryPath --version)"
