$ErrorActionPreference = 'Stop'
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
if (-not (Test-Path -LiteralPath $chrome)) { throw 'Chrome executable not found' }
if (Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 9222 is occupied. Do not attach to an unrelated browser.'
}
$profile = Join-Path $PSScriptRoot ('experiments\20261008\chrome-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$arguments = @('--headless=new', '--disable-gpu', '--remote-debugging-port=9222',
    ('--user-data-dir=' + $profile), '--proxy-server=http://127.0.0.1:7770',
    '--proxy-bypass-list=<-loopback>', '--no-first-run', '--no-default-browser-check', 'about:blank')
Start-Process -FilePath $chrome -ArgumentList $arguments -WindowStyle Hidden
Write-Output 'Dedicated benchmark Chrome started on CDP 9222; shared read-only proxy 7770.'
