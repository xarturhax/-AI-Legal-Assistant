$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'manage.ps1'
$parseErrors = $null
$tokens = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'FAIL: синтаксис manage.ps1' }
foreach ($name in @('Invoke-Checked', 'Compose', 'Assert-PreparedImages', 'Get-AppPort', 'Assert-AppPort', 'Build-InitialKb')) {
    $definition = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
    . ([scriptblock]::Create($definition.Extent.Text))
}
function docker { $script:received = @($args); $global:LASTEXITCODE = 0 }
Compose @('exec', '-T', 'app', 'python', '-m', 'app', 'db-upgrade')
if (($script:received -join '|') -ne 'compose|exec|-T|app|python|-m|app|db-upgrade') {
    throw ('FAIL: передача аргументов: ' + ($script:received -join '|'))
}
Write-Output 'PASS (mock): PowerShell передаёт все аргументы Compose; Docker не запускался.'

# Настоящий дочерний процесс: stderr с exit 0 не является ошибкой установки.
$pythonPath = Join-Path (Split-Path -Parent $PSScriptRoot) '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $pythonPath) {
    Invoke-Checked $pythonPath @('-c', 'import sys; sys.stderr.write(''native-progress\n''); sys.exit(0)')
    $caughtFailure = $false
    try { Invoke-Checked $pythonPath @('-c', 'import sys; sys.exit(7)') } catch { $caughtFailure = $true }
    if (!$caughtFailure) { throw 'FAIL: ненулевой exit code должен останавливать установку' }
    Write-Output 'PASS (native): stderr с exit 0 разрешён; exit 7 корректно распознан.'
} else {
    Write-Output 'SKIPPED (native): локальная .venv с Python отсутствует.'
}

function docker { $global:LASTEXITCODE = 1 }
$missingImageCaught = $false
try { Assert-PreparedImages } catch { $missingImageCaught = $true }
if (!$missingImageCaught) { throw 'FAIL: start не должен запускать неподготовленный стек' }
Write-Output 'PASS (mock): неподготовленный стек блокирует start до запуска контейнеров.'

function docker { $global:LASTEXITCODE = 0 }
$busyListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
try {
    $busyListener.Start()
    $testPort = $busyListener.LocalEndpoint.Port
    $busyPortCaught = $false
    try { Assert-AppPort -Port $testPort } catch { $busyPortCaught = $true }
    if (!$busyPortCaught) { throw 'FAIL: занятый порт должен быть обнаружен до запуска app' }
} finally { $busyListener.Stop() }
Assert-AppPort -Port $testPort
Write-Output 'PASS (mock Docker, native TCP): занятый порт отклонён; освобождённый разрешён.'

# Незавершённая KB после ошибки GWF: до новой сборки обязательна успешная копия.
$script:kbEvents = New-Object 'System.Collections.Generic.List[string]'
$script:readyKb = $false
$script:backupFails = $false
$script:buildFails = $false
function docker {
    if ($args -contains 'test -f /kb.bin/.legal-kb-ready') {
        $global:LASTEXITCODE = if ($script:readyKb) { 0 } else { 1 }
    } else { $global:LASTEXITCODE = 1 } # Непустая KB без маркера.
}
function Backup-Kb {
    $script:kbEvents.Add('backup')
    if ($script:backupFails) { throw 'test-only: backup failed' }
}
function Compose([string[]]$Arguments) {
    if ($Arguments -contains 'build') {
        $script:kbEvents.Add('build')
        if ($script:buildFails) { throw 'test-only: builder failed' }
    } else { $script:kbEvents.Add('mark-ready') }
}
Build-InitialKb
if (($script:kbEvents -join '|') -ne 'backup|build|mark-ready') { throw 'FAIL: неверный порядок восстановления KB' }
$script:kbEvents.Clear()
$script:backupFails = $true
$backupFailureCaught = $false
try { Build-InitialKb } catch { $backupFailureCaught = $true }
if (!$backupFailureCaught -or ($script:kbEvents -join '|') -ne 'backup') { throw 'FAIL: нельзя собирать KB при ошибке бэкапа' }
$script:kbEvents.Clear()
$script:backupFails = $false
$script:buildFails = $true
$buildFailureCaught = $false
try { Build-InitialKb } catch { $buildFailureCaught = $true }
if (!$buildFailureCaught -or ($script:kbEvents -join '|') -ne 'backup|build') { throw 'FAIL: маркер готовности нельзя ставить при ошибке сборки' }
$script:kbEvents.Clear()
$script:readyKb = $true
Build-InitialKb
if ($script:kbEvents.Count -ne 0) { throw 'FAIL: готовая KB не должна пересобираться' }
Write-Output 'PASS (mock Docker): бэкап предшествует повторной сборке; ошибки блокируют сборку/маркер; готовая KB сохранена.'
