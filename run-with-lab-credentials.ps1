function Read-LabValue([string]$Prompt) {
    $secureValue = Read-Host $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$aws = Join-Path $env:ProgramFiles 'Amazon\AWSCLIV2\aws.exe'
$python = Join-Path $PSScriptRoot '.venv312\Scripts\python.exe'

if (-not (Test-Path $aws)) {
    throw 'AWS CLI was not found at its expected install path.'
}
if (-not (Test-Path $python)) {
    throw 'Python environment .venv312 was not found. Install requirements into it first.'
}

$env:AWS_ACCESS_KEY_ID = Read-LabValue 'Lab access key ID'
$env:AWS_SECRET_ACCESS_KEY = Read-LabValue 'Lab secret access key'
$env:AWS_SESSION_TOKEN = Read-LabValue 'Lab session token'
$env:AWS_REGION = 'us-east-1'
$env:AWS_DEFAULT_REGION = 'us-east-1'
$env:LAMBDA_FUNCTION = 'CHAOS-KILL-SWITCH'

try {
    & $aws sts get-caller-identity
    if ($LASTEXITCODE -ne 0) {
        throw 'Sign-in check failed. Check that all three lab values are current and copied correctly.'
    }

    Set-Location $PSScriptRoot
    & $python -m uvicorn app:app --host 127.0.0.1 --port 8001
} finally {
    Remove-Item Env:AWS_ACCESS_KEY_ID, Env:AWS_SECRET_ACCESS_KEY, Env:AWS_SESSION_TOKEN, Env:AWS_REGION, Env:AWS_DEFAULT_REGION, Env:LAMBDA_FUNCTION -ErrorAction SilentlyContinue
}