# startup.ps1 — CoupleFight startup script for Windows (PowerShell)
# Idempotent: safe to re-run. Creates venv, installs deps, sets up .env,
# runs migrations, then starts the Flask dev server.

$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

# $Host is a PowerShell reserved automatic variable; use distinct names.
$PythonExe = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
$VenvDir   = '.venv'
$FlaskHost = if ($env:HOST)   { $env:HOST }   else { '0.0.0.0' }
$FlaskPort = if ($env:PORT)   { $env:PORT }   else { '5000' }

Write-Host '[1/5] Checking Python...'
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: '$PythonExe' not found. Install Python 3.11+ and re-run."
    exit 1
}

Write-Host '[2/5] Creating virtualenv (if missing)...'
if (-not (Test-Path $VenvDir)) {
    & $PythonExe -m venv $VenvDir
}
& "$VenvDir\Scripts\Activate.ps1"

Write-Host '[3/5] Installing dependencies...'
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

Write-Host '[4/5] Preparing .env and database...'
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    # Generate a strong SECRET_KEY and replace the placeholder in .env.
    # Done entirely in PowerShell to avoid heredoc portability issues.
    $secret     = & $PythonExe -c 'import secrets; print(secrets.token_urlsafe(64))'
    $envContent = Get-Content '.env' -Raw
    $envContent = $envContent -replace 'change-me-to-a-long-random-string', $secret
    Set-Content '.env' $envContent -Encoding utf8 -NoNewline
    Write-Host '    .env created with a fresh SECRET_KEY.'
}

$env:FLASK_APP = 'run.py'

# Initialize migrations directory only if not present.
if (-not (Test-Path 'migrations')) {
    flask db init | Out-Null
}

# Generate a migration if there are model changes with no revision yet.
$versions = Get-ChildItem 'migrations\versions' -ErrorAction SilentlyContinue
if (-not $versions) {
    flask db migrate -m 'init' | Out-Null
}

flask db upgrade | Out-Null

Write-Host "[5/5] Starting server on http://${FlaskHost}:${FlaskPort}  (Ctrl-C to stop)"
flask run --host $FlaskHost --port $FlaskPort
