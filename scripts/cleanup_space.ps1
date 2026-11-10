param([switch]$ProjectOnly, [switch]$ReportOnly)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
Set-Location -LiteralPath $projectRoot
$script:cleanupFailed = $false
$dockerCacheCleaned = $null
$pipCacheCleaned = $null

function Get-FreeSpace {
    $driveRoot = [IO.Path]::GetPathRoot($projectRoot)
    return [IO.DriveInfo]::new($driveRoot).AvailableFreeSpace
}

function Get-CacheSize([string]$Path) {
    $pending = New-Object 'System.Collections.Generic.Stack[System.IO.DirectoryInfo]'
    $rootItem = Get-Item -LiteralPath $Path -Force
    if ($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Отказ: каталог кеша является ссылкой: $Path"
    }
    $pending.Push($rootItem)
    $sizeBytes = 0L
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($item in $directory.EnumerateFileSystemInfos()) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Отказ: в кеше обнаружена ссылка: $($item.FullName)"
            }
            if ($item.Attributes -band [IO.FileAttributes]::Directory) {
                $pending.Push($item)
            } else {
                $sizeBytes += $item.Length
            }
        }
    }
    return $sizeBytes
}

function Clear-ProjectCaches {
    $cacheNames = @('.cache/browser-evidence', '.cache/chrome-smoke', '.cache/chrome-smoke-software', '.pytest_cache', '.ruff_cache')
    $removedBytes = 0L
    foreach ($relativePath in $cacheNames) {
        $target = [IO.Path]::GetFullPath((Join-Path $projectRoot $relativePath))
        # Проверка абсолютного пути обязательна перед рекурсивным удалением.
        if (!$target.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "Путь вышел за пределы проекта: $target"
        }
        if (!(Test-Path -LiteralPath $target -PathType Container)) { continue }
        try {
            $ancestor = Get-Item -LiteralPath $target -Force
            while ($ancestor.FullName.TrimEnd('\') -ine $projectRoot) {
                if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                    throw "Отказ: путь кеша проходит через ссылку: $($ancestor.FullName)"
                }
                $ancestor = $ancestor.Parent
                if ($null -eq $ancestor) { throw 'Путь кеша не принадлежит workspace.' }
            }
            $size = Get-CacheSize $target
            Write-Host ("Кеш проекта: {0}, {1:N2} МиБ" -f $target, ($size / 1MB))
            if (!$ReportOnly) {
                Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
                $removedBytes += $size
            }
        } catch {
            $script:cleanupFailed = $true
            Write-Host "Кеш пропущен: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    return $removedBytes
}

function Invoke-CleanupCommand([string]$Program, [string[]]$Arguments) {
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Program @Arguments 2>&1 | ForEach-Object { Write-Host ([string]$_) }
        $commandExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    if ($commandExitCode -ne 0) {
        $script:cleanupFailed = $true
        Write-Host "${Program}: шаг не выполнен, код $commandExitCode." -ForegroundColor Yellow
    }
    return $commandExitCode -eq 0
}

$transcriptStarted = $false
if (!$ProjectOnly -and !$ReportOnly) {
    $logDirectory = Join-Path $projectRoot 'logs'
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    $cleanupLogPath = Join-Path $logDirectory ('cleanup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + $PID + '.log')
    Start-Transcript -LiteralPath $cleanupLogPath | Out-Null
    $transcriptStarted = $true
    Write-Host "Журнал очистки: $cleanupLogPath"
}
try {
$before = Get-FreeSpace
Write-Host ("Свободно на диске до очистки: {0:N2} ГиБ" -f ($before / 1GB))
Write-Host 'Сохраняются исходники, .env, .venv, SQLite, логи, образы, контейнеры, модели и Docker-тома.'
$removedProjectBytes = Clear-ProjectCaches

if (!$ProjectOnly -and !$ReportOnly) {
    Write-Host "`n=== Неиспользуемый кеш сборки Docker ===" -ForegroundColor Cyan
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        if (Invoke-CleanupCommand 'docker' @('info', '--format', '{{.OSType}}')) {
            Invoke-CleanupCommand 'docker' @('system', 'df') | Out-Null
            $dockerCacheCleaned = Invoke-CleanupCommand 'docker' @('builder', 'prune', '--all', '--force')
            Invoke-CleanupCommand 'docker' @('system', 'df') | Out-Null
        } else {
            Write-Host 'Кеш Docker не очищен: нет доступа к Docker Engine из этого сеанса.'
        }
    } else {
        $script:cleanupFailed = $true
        Write-Host 'Docker CLI не найден. Этот шаг пропущен.'
    }
    Write-Host "`n=== Кеш скачанных пакетов pip ===" -ForegroundColor Cyan
    $pythonLocation = Join-Path $projectRoot '.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $pythonLocation) {
        Invoke-CleanupCommand $pythonLocation @('-m', 'pip', 'cache', 'info') | Out-Null
        $pipCacheCleaned = Invoke-CleanupCommand $pythonLocation @('-m', 'pip', 'cache', 'purge')
    } else {
        Write-Host 'Локальный Python не найден; кеш pip оставлен без изменений.'
    }
}

$after = Get-FreeSpace
Write-Host ("`nУдалено кешей проекта: {0:N2} МиБ" -f ($removedProjectBytes / 1MB))
if ($null -ne $dockerCacheCleaned) {
    Write-Host ("Очистка кеша сборки Docker успешна: {0}. Объём указан в строке Total выше." -f $dockerCacheCleaned)
}
if ($null -ne $pipCacheCleaned) {
    Write-Host ("Очистка кеша pip успешна: {0}. Число файлов указано выше." -f $pipCacheCleaned)
}
Write-Host ("Свободно на диске после очистки: {0:N2} ГиБ" -f ($after / 1GB))
Write-Host ("Изменение свободного места Windows: {0:N2} МиБ" -f (($after - $before) / 1MB))
Write-Host 'Счётчик кешей проекта не включает Docker и pip. Место внутри Docker VHDX и свободное место Windows учитываются отдельно.'
Write-Host 'Файл Docker VHDX не удаляется и принудительно не сжимается.'
if (!$ReportOnly) {
    $report = [ordered]@{
        created_at = (Get-Date).ToString('o')
        project_only = [bool]$ProjectOnly
        project_cache_bytes_removed = $removedProjectBytes
        docker_cache_cleanup_succeeded = $dockerCacheCleaned
        pip_cache_cleanup_succeeded = $pipCacheCleaned
        host_free_bytes_before = $before
        host_free_bytes_after = $after
        incomplete = $script:cleanupFailed
    }
    $reportPath = Join-Path $projectRoot 'docs/evidence/disk-cleanup.json'
    [IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
}
} finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
if ($script:cleanupFailed) { exit 1 }
