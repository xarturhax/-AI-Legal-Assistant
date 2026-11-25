$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $project '.env'
if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
    throw 'Run setup.bat before configuring mail.'
}

$sender = (Read-Host 'Адрес нового Gmail-ящика Themis').Trim().ToLowerInvariant()
if ($sender -notmatch '^[a-z0-9.]+@(gmail\.com|googlemail\.com)$') {
    throw 'Укажите полный адрес Gmail.'
}
$securePassword = Read-Host 'Пароль приложения Google' -AsSecureString
$passwordBuffer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordBuffer) -replace '\s', ''
    if ($appPassword -notmatch '^[a-zA-Z0-9]{16}$') {
        throw 'Ожидается пароль приложения из 16 символов.'
    }
    $lines = [IO.File]::ReadAllLines($envFile) | Where-Object {
        $_ -notmatch '^\s*(SMTP_HOST|SMTP_PORT|SMTP_USERNAME|SMTP_PASSWORD|GMAIL_OAUTH_FILE|GMAIL_SENDER|DEV_LOCAL_MAIL)\s*='
    }
    $lines += @('SMTP_HOST=smtp.gmail.com', 'SMTP_PORT=587', "SMTP_USERNAME=$sender",
                "SMTP_PASSWORD=$appPassword", 'DEV_LOCAL_MAIL=0')
    [IO.File]::WriteAllLines($envFile, [string[]]$lines, [Text.UTF8Encoding]::new($false))
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordBuffer)
}
Write-Host 'Настройки Gmail сохранены в локальном .env.'
