param([ValidateSet('setup', 'start', 'stop', 'rebuild')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    Get-Command $Program -ErrorAction Stop | Out-Null
    $previousPreference = $ErrorActionPreference
    try {
        # Git и Docker пишут обычный прогресс в stderr. В Windows PowerShell 5.1
        # такой вывод не должен останавливать установку при успешном exit code.
        $ErrorActionPreference = 'Continue'
        & $Program @Arguments 2>&1 | ForEach-Object { Write-Host ([string]$_) }
        $commandExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($commandExitCode -ne 0) { throw "$Program завершился с кодом $commandExitCode." }
}
function Compose([string[]]$Arguments) { Invoke-Checked 'docker' (@('compose') + $Arguments) }
function Set-Stage([string]$Name) {
    $script:currentStage = $Name
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
}
function Get-AppPort {
    $portLine = Get-Content '.env' | Where-Object { $_ -match '^APP_PORT=' } | Select-Object -First 1
    $portValue = if ($portLine) { ($portLine -split '=', 2)[1].Trim() } else { '5000' }
    $configuredPort = 0
    if (![int]::TryParse($portValue, [ref]$configuredPort) -or $configuredPort -lt 1 -or $configuredPort -gt 65535) {
        throw 'APP_PORT должен быть числом от 1 до 65535.'
    }
    return $configuredPort
}
function Assert-AppPort([int]$Port = (Get-AppPort)) {
    # Уже работающий контейнер этого проекта законно занимает свой порт.
    $runningApp = & docker compose ps --status running --services app
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось проверить состояние контейнера app.' }
    if (@($runningApp) -contains 'app') { return }
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $probe.Start() } catch {
        throw "Порт $Port уже занят другой программой. Остановите локальный Python-сервер или задайте свободный APP_PORT в .env. Чужие процессы автоматически не останавливаются."
    } finally { $probe.Stop() }
}
function Assert-PreparedImages {
    if (!(Test-Path -LiteralPath 'ostis/upstream/repo.path')) {
        throw 'Исходники OSTIS не подготовлены. Сначала завершите setup.bat.'
    }
    foreach ($imageName in @('legal-ai-ostis:903e0c1', 'legal-ai-python:local')) {
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & docker image inspect $imageName *> $null
            $imageExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        if ($imageExitCode -ne 0) {
            throw "Локальный образ $imageName отсутствует. Сборка в setup.bat ещё не завершена. Сначала исправьте ошибку setup.bat; start.bat не скачивает эти образы из Docker Hub."
        }
    }
}
function Prepare-Environment {
    if (!(Test-Path -LiteralPath '.env')) {
        $randomBytes = New-Object byte[] 48
        $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
        $generator.GetBytes($randomBytes)
        $generator.Dispose()
        $secret = [Convert]::ToBase64String($randomBytes)
        $configText = [IO.File]::ReadAllText((Join-Path $projectRoot '.env.example'))
        [IO.File]::WriteAllText((Join-Path $projectRoot '.env'), $configText.Replace('CHANGE_ME_LOCALLY', $secret), (New-Object Text.UTF8Encoding $false))
    }
}
function Prepare-Upstream {
    $pin = Get-Content -Raw 'ostis/upstream.lock.json' | ConvertFrom-Json
    $upstreamPath = Join-Path $projectRoot 'ostis/upstream'
    if (!(Test-Path -LiteralPath $upstreamPath)) {
        Invoke-Checked 'git' @('clone', '--no-checkout', $pin.url, $upstreamPath)
        Invoke-Checked 'git' @('-C', $upstreamPath, 'checkout', '--detach', $pin.sha)
    }
    $actualSha = & git -C $upstreamPath rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $actualSha -ne $pin.sha) { throw 'Upstream имеет другую ревизию. Существующие файлы не изменены.' }
    $dirty = & git -C $upstreamPath status --porcelain
    if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Upstream содержит изменения. Сохраните их отдельно перед установкой.' }
    Invoke-Checked 'git' @('-C', $upstreamPath, 'submodule', 'update', '--init', '--recursive')
    foreach ($entry in $pin.submodules.PSObject.Properties) {
        $actualSubmodule = & git -C (Join-Path $upstreamPath $entry.Name) rev-parse HEAD
        if ($LASTEXITCODE -ne 0 -or $actualSubmodule -ne $entry.Value) { throw "Неверный SHA подмодуля $($entry.Name)" }
    }
    Write-Host 'Upstream checkout сохранён в ostis/upstream. Данные KB не изменялись.'
}
function Wait-Ollama {
    $deadline = (Get-Date).AddMinutes(2)
    do {
        & docker compose exec -T ollama ollama list *> $null
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)
    throw 'Ollama не готов. Выполните docker compose logs ollama.'
}
function Backup-Kb {
    Compose @('stop', 'app', 'machine')
    New-Item -ItemType Directory -Force -Path 'backups' | Out-Null
    $backupName = 'kb-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + $PID + '.tar'
    $backupPath = Join-Path $projectRoot 'backups'
    $archivePath = Join-Path $backupPath $backupName
    Compose @('run', '--rm', '--no-deps', '-v', "${backupPath}:/backup", '--entrypoint', '/bin/tar', 'machine', '-cf', "/backup/$backupName", '-C', '/kb.bin', '.')
    if (!(Test-Path -LiteralPath $archivePath) -or (Get-Item -LiteralPath $archivePath).Length -eq 0) {
        throw 'Резервная копия KB не создана. Сборка остановлена, данные сохранены.'
    }
    Compose @('run', '--rm', '--no-deps', '-v', "${backupPath}:/backup:ro", '--entrypoint', '/bin/tar', 'machine', '-tf', "/backup/$backupName")
    Write-Host "Резервная копия KB создана и проверена: $archivePath"
}
function Build-InitialKb {
    & docker compose run --rm --no-deps --entrypoint /bin/sh machine -c 'test -f /kb.bin/.legal-kb-ready'
    if ($LASTEXITCODE -eq 0) { Write-Host 'KB уже подготовлена; повторная сборка пропущена.'; return }
    & docker compose run --rm --no-deps --entrypoint /app/.venv/bin/python3 machine -c 'import pathlib,sys; sys.exit(any(pathlib.Path(''/kb.bin'').iterdir()))'
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'В KB есть данные без маркера успешной установки. Перед повторной сборкой сохраняется и проверяется резервная копия.'
        Backup-Kb
    }
    Compose @('run', '--rm', '--no-deps', 'machine', 'build')
    Compose @('run', '--rm', '--no-deps', '--entrypoint', '/bin/sh', 'machine', '-c', 'touch /kb.bin/.legal-kb-ready')
}
function Wait-Application {
    $appPort = Get-AppPort
    $appUrl = "http://127.0.0.1:$appPort"
    $deadline = (Get-Date).AddMinutes(6)
    do {
        try {
            $ready = Invoke-WebRequest -UseBasicParsing -Uri "$appUrl/health/ready" -TimeoutSec 15
            if ($ready.StatusCode -eq 200) { Start-Process $appUrl -WindowStyle Hidden; return }
        } catch { }
        Start-Sleep -Seconds 4
    } while ((Get-Date) -lt $deadline)
    throw 'Истекло ожидание готовности. Проверьте docker compose logs и /health/ready.'
}
$script:currentStage = 'Инициализация'
$logDirectory = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$logPath = Join-Path $logDirectory ("{0}-{1}-{2}.log" -f $Action, (Get-Date -Format 'yyyyMMdd-HHmmss'), $PID)
$transcriptStarted = $false
try {
    Start-Transcript -LiteralPath $logPath -ErrorAction Stop | Out-Null
    $transcriptStarted = $true
    Write-Host "Лог запуска: $logPath"
    Set-Stage 'Проверка Docker Engine'
    $containerOperatingSystem = & docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0) { throw 'Docker Engine недоступен. Запустите Docker Desktop.' }
    if ($containerOperatingSystem.Trim() -ne 'linux') { throw 'Нужен Docker Desktop в режиме Linux containers.' }
    if ($Action -eq 'stop') { Compose @('stop'); exit 0 }
    if ($Action -eq 'setup') {
        Set-Stage 'Проверка WSL2'
        if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
            & wsl.exe --status
            if ($LASTEXITCODE -ne 0) { throw 'WSL2 недоступен. Подготовьте WSL2 и Docker Desktop.' }
        }
        Set-Stage 'Подготовка конфигурации и исходников'
        Prepare-Environment
        Prepare-Upstream
        Set-Stage 'Проверка Docker Compose'
        Compose @('config', '--quiet')
        Set-Stage 'Сборка sc-machine и Python-приложения'
        Compose @('--progress', 'plain', 'build', 'machine', 'app')
        Set-Stage 'Подготовка юридической KB'
        Build-InitialKb
        Set-Stage 'Запуск Ollama и загрузка локальной модели'
        Compose @('up', '-d', 'ollama')
        Wait-Ollama
        # Значение передаётся как отдельный аргумент, без исполнения строки из .env.
        $modelLine = Get-Content '.env' | Where-Object { $_ -match '^OLLAMA_MODEL=' } | Select-Object -First 1
        $modelName = if ($modelLine) { ($modelLine -split '=', 2)[1].Trim() } else { 'qwen3:4b-instruct' }
        Compose @('exec', '-T', 'ollama', 'ollama', 'pull', $modelName)
        Set-Stage 'Миграции SQLite'
        Compose @('run', '--rm', '--no-deps', 'app', 'python', '-m', 'app', 'db-upgrade')
        Write-Host 'Первичная установка завершена. Запустите start.bat.'
        exit 0
    }
    if (!(Test-Path -LiteralPath '.env')) { throw 'Сначала выполните setup.bat.' }
    if ($Action -eq 'start') {
        Set-Stage 'Проверка результатов первичной установки'
        Assert-PreparedImages
        Set-Stage 'Проверка порта приложения'
        Assert-AppPort
    }
    if ($Action -eq 'rebuild') {
        Write-Host 'Пересборка заменит бинарную KB исходной версией после сохранения резервной копии.'
        if ((Read-Host 'Введите REBUILD для продолжения') -cne 'REBUILD') { throw 'Пересборка отменена.' }
        Backup-Kb
        Compose @('run', '--rm', '--no-deps', '--entrypoint', '/app/.venv/bin/python3', 'machine', '-c', 'from pathlib import Path; Path(''/kb.bin/.legal-kb-ready'').unlink(missing_ok=True)')
        Compose @('run', '--rm', '--no-deps', 'machine', 'build')
        Compose @('run', '--rm', '--no-deps', '--entrypoint', '/bin/sh', 'machine', '-c', 'touch /kb.bin/.legal-kb-ready')
    }
    Set-Stage 'Запуск контейнеров'
    Compose @('up', '-d', '--no-build')
    Set-Stage 'Ожидание готовности приложения'
    Wait-Application
} catch {
    Write-Host "`nОшибка на этапе: $script:currentStage" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Полный журнал: $logPath"
    exit 1
} finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
