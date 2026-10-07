$ErrorActionPreference = 'Stop'
$sourcePath = $PSScriptRoot
$configPath = if ($env:JEV_ROUTER_CONFIG_DIR) { $env:JEV_ROUTER_CONFIG_DIR } else { Join-Path $HOME '.config\jev' }

& uv tool install --reinstall $sourcePath
if ($LASTEXITCODE -ne 0) { throw 'uv tool install 失敗。' }

New-Item -ItemType Directory -Path $configPath -Force | Out-Null
$configEnvPath = Join-Path $configPath '.env'
if (-not (Test-Path -LiteralPath $configEnvPath)) {
    # 設定資料夾只給目前使用者存取
    $accountSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls $configPath /inheritance:r /grant:r "*${accountSid}:(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw '設定資料夾權限失敗。' }
    # 金鑰優先取環境變數，否則以不顯示的方式詢問
    $apiKey = $env:TYPESAFE_API_KEY
    if (-not $apiKey) {
        $secure = Read-Host -Prompt 'TYPESAFE_API_KEY' -AsSecureString
        $apiKey = [System.Net.NetworkCredential]::new('', $secure).Password
    }
    if (-not $apiKey.Trim()) { throw '沒有輸入 TYPESAFE_API_KEY。' }
    $model = if ($env:TYPESAFE_MODEL) { $env:TYPESAFE_MODEL } else { 'jev-latest' }
    $lines = @("TYPESAFE_API_KEY=$apiKey", "TYPESAFE_MODEL=$model")
    [System.IO.File]::WriteAllLines($configEnvPath, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
}
$modelsPath = Join-Path $configPath 'models.json'
if (-not (Test-Path -LiteralPath $modelsPath)) {
    Copy-Item -LiteralPath (Join-Path $sourcePath 'models.example.json') -Destination $modelsPath
}
Write-Output "已安裝 jev-router，設定位於 $configPath；金鑰未輸出。請把 models.json 改成自己可用的模型。"
