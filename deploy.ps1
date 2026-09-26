<#
Builds the images on this computer, sends them to the server over scp and
restarts the service. No image registry is involved. Instructions: DEPLOY.md.

Usage (from the repository root):  .\deploy.ps1

Settings: .env.deploy next to this script (not committed, matched by .env.* in .gitignore):
    SERVER=deploy@203.0.113.10
    REMOTE_DIR=/home/deploy/cubing

The server runs `git pull` to get the same code the images were built from,
so everything must be committed and pushed to origin/master first.
#>

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Native commands do not stop the script on failure by themselves.
function Invoke-Checked {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: $File $($Arguments -join ' ') (exit code $LASTEXITCODE)"
    }
}

# Settings
if (-not (Test-Path .env.deploy)) {
    throw '.env.deploy not found. Create it with SERVER=user@host and REMOTE_DIR=/path/on/server.'
}
$config = @{}
foreach ($line in Get-Content .env.deploy) {
    if ($line -match '^\s*([A-Z_]+)\s*=\s*(.*?)\s*$') {
        $config[$Matches[1]] = $Matches[2]
    }
}
$server = $config['SERVER']
$remoteDir = $config['REMOTE_DIR']
if (-not $server -or -not $remoteDir) {
    throw '.env.deploy must set SERVER and REMOTE_DIR.'
}

# The code on the server must match the images.
if (git status --porcelain) {
    throw 'There are uncommitted changes. Commit and push them first.'
}
Invoke-Checked git @('fetch', '--quiet', 'origin')
$head = git rev-parse HEAD
$published = git rev-parse origin/master
if ($head -ne $published) {
    throw "HEAD ($head) is not origin/master ($published). Push to master (or switch to it) first."
}

# Third-party images (certbot) are sent only if the server does not have that
# version yet: the server never needs Docker Hub.
$thirdParty = Select-String -Path docker-compose.prod.yml -Pattern '^\s*image:\s*(\S+)' |
    ForEach-Object { $_.Matches[0].Groups[1].Value } |
    Where-Object { $_ -notlike 'cubing-*' }
$missing = @()
if ($thirdParty) {
    $check = ($thirdParty | ForEach-Object { "docker image inspect $_ >/dev/null 2>&1 || echo $_" }) -join '; '
    $missing = @(ssh $server $check)
    if ($LASTEXITCODE -ne 0) { throw "Cannot connect to $server over ssh." }
}

Write-Host "== Building images for $head" -ForegroundColor Cyan
Invoke-Checked docker @('build', '--platform', 'linux/amd64', '-t', 'cubing-backend:latest', 'backend')
Invoke-Checked docker @('build', '--platform', 'linux/amd64', '-t', 'cubing-web:latest', 'frontend')
foreach ($image in $missing) {
    Invoke-Checked docker @('pull', '--platform', 'linux/amd64', $image)
}

$tar = Join-Path $env:TEMP 'cubing-images.tar'
Write-Host '== Saving images' -ForegroundColor Cyan
Invoke-Checked docker (@('save', '-o', $tar, 'cubing-backend:latest', 'cubing-web:latest') + $missing)

try {
    Write-Host "== Sending to $server" -ForegroundColor Cyan
    Invoke-Checked scp @('-C', $tar, "$($server):/tmp/cubing-images.tar")

    Write-Host '== Updating the server' -ForegroundColor Cyan
    Invoke-Checked ssh @($server, "cd '$remoteDir' && git pull --ff-only && sh deploy/update.sh /tmp/cubing-images.tar")
}
finally {
    Remove-Item $tar -ErrorAction SilentlyContinue
}

Write-Host '== Done' -ForegroundColor Green
