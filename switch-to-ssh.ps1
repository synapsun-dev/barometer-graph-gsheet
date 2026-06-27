# Switch Git Remote from HTTPS to SSH
# Usage: .\switch-to-ssh.ps1
# Prerequisites: SSH public key must be added to GitHub account

param(
    [switch]$DryRun = $false,
    [switch]$ForceHTTPS = $false
)

$ErrorActionPreference = "Stop"
$repoPath = "C:\Claude\Synapsun\Barometer"
$httpUrl = "https://github.com/synapsun-dev/barometer-graph-gsheet.git"
$sshUrl = "git@github.com:synapsun-dev/barometer-graph-gsheet.git"

Write-Host "🔐 Git SSH Configuration Tool" -ForegroundColor Cyan
Write-Host "=" * 50
Write-Host ""

# Check if we're in the repo
if (-not (Test-Path "$repoPath\.git")) {
    Write-Host "❌ Not a git repository: $repoPath" -ForegroundColor Red
    exit 1
}

Push-Location $repoPath

# Current remote
$currentRemote = git config --get remote.origin.url
Write-Host "Current Remote:"
Write-Host "  $currentRemote" -ForegroundColor Yellow
Write-Host ""

if ($ForceHTTPS) {
    Write-Host "🔗 Switching to HTTPS..." -ForegroundColor Cyan
    $newUrl = $httpUrl
    $newProto = "HTTPS"
} else {
    Write-Host "🔗 Switching to SSH..." -ForegroundColor Cyan
    $newUrl = $sshUrl
    $newProto = "SSH"
}

Write-Host "New Remote:"
Write-Host "  $newUrl" -ForegroundColor Green
Write-Host ""

# Dry run?
if ($DryRun) {
    Write-Host "📋 [DRY RUN] Would execute:" -ForegroundColor Yellow
    Write-Host "  git remote set-url origin $newUrl"
    Write-Host ""
    Write-Host "To apply, run: .\switch-to-ssh.ps1 [-ForceHTTPS]"
    Pop-Location
    exit 0
}

# Test SSH key if switching to SSH
if (-not $ForceHTTPS) {
    Write-Host "🔑 Testing SSH configuration..." -ForegroundColor Cyan

    $sshTest = ssh -T git@github.com 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ($sshTest -like "*Permission denied*") {
            Write-Host "❌ SSH Key not authorized on GitHub" -ForegroundColor Red
            Write-Host ""
            Write-Host "Steps to fix:" -ForegroundColor Yellow
            Write-Host "1. Copy your public key:"
            Write-Host "   cat ~/.ssh/id_rsa.pub"
            Write-Host "2. Add it to GitHub:"
            Write-Host "   https://github.com/settings/keys → New SSH key"
            Write-Host "3. Paste the key and save"
            Write-Host "4. Then run this script again"
            Write-Host ""
            Pop-Location
            exit 1
        } elseif ($sshTest -like "*Hi *!*") {
            Write-Host "✅ SSH authentication successful!" -ForegroundColor Green
        }
    }

    Write-Host "✅ SSH Key configured" -ForegroundColor Green
    Write-Host ""
}

# Update remote
Write-Host "⚙️  Updating git remote..." -ForegroundColor Cyan
git remote set-url origin $newUrl

# Verify
$verifyUrl = git config --get remote.origin.url
if ($verifyUrl -eq $newUrl) {
    Write-Host "✅ Remote updated successfully!" -ForegroundColor Green
    Write-Host "   $verifyUrl"
} else {
    Write-Host "❌ Failed to update remote" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "🧪 Testing $newProto connection..." -ForegroundColor Cyan

if ($ForceHTTPS) {
    git fetch origin 2>&1 | Write-Host
} else {
    # SSH test via git ls-remote (non-destructive)
    $remoteTest = git ls-remote --heads origin 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Connection test successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Connection test failed:" -ForegroundColor Red
        Write-Host $remoteTest
        Pop-Location
        exit 1
    }
}

Write-Host ""
Write-Host "=" * 50
Write-Host "✅ Git remote switched to $newProto" -ForegroundColor Green
Write-Host "You can now use: git push, git pull, git fetch" -ForegroundColor Green
Write-Host ""

Pop-Location
