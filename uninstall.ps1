Write-Host "🗑️ Starting MCP Vault Uninstallation..." -ForegroundColor Cyan

# 윈도우 환경인지 (또는 wsl이 아닌지) 체크
$configDir = "$env:USERPROFILE\.gemini\antigravity"
$configFile = "$configDir\mcp_config.json"
$backupFile = "$configDir\mcp_config.original.json"
$rootPathFile = "$configDir\root_path.txt"
$boosterScript = "$configDir\boost_launcher.bat"
$shortcut = "$env:USERPROFILE\Desktop\Antigravity Boost (mcpv).lnk"

Write-Host "📦 Stage 1: Uninstalling mcpv python package..."
# uv가 있는지 체크
$uvCheck = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCheck) {
    Write-Host "   Using uv to uninstall..." -ForegroundColor Gray
    uv pip uninstall mcpv
}
else {
    Write-Host "   Using pip to uninstall..." -ForegroundColor Gray
    pip uninstall mcpv -y
}

Write-Host "🗑️ Stage 2: Removing Desktop Shortcut..."
if (Test-Path $shortcut) {
    Remove-Item $shortcut -Force
    Write-Host "   -> Shortcut removed." -ForegroundColor Green
}
else {
    Write-Host "   -> Shortcut not found (already removed)." -ForegroundColor Gray
}

Write-Host "🔧 Stage 3: Restoring original MCP configuration..."
if (Test-Path $backupFile) {
    if (Test-Path $configFile) {
        Remove-Item $configFile -Force
    }
    Rename-Item -Path $backupFile -NewName "mcp_config.json" -Force
    Write-Host "   -> Successfully restored mcp_config.original.json to mcp_config.json" -ForegroundColor Green
}
else {
    if (Test-Path $configFile) {
        Remove-Item $configFile -Force
        Write-Host "   -> Original backup not found. Cleaned up mcpv config." -ForegroundColor Yellow
    }
}

Write-Host "🧹 Stage 4: Cleaning up booster scripts and configs..."
$cleaned = 0
if (Test-Path $rootPathFile) { Remove-Item $rootPathFile -Force; $cleaned++ }
if (Test-Path $boosterScript) { Remove-Item $boosterScript -Force; $cleaned++ }

if ($cleaned -gt 0) {
    Write-Host "   -> Removed $cleaned mcpv environment files." -ForegroundColor Green
}
else {
    Write-Host "   -> Everything already clean." -ForegroundColor Gray
}

Write-Host "`n🎉 Success! MCP Vault has been completely removed and Antigravity is restored to original state." -ForegroundColor Cyan
Write-Host "👉 You can now safely close this terminal." -ForegroundColor Gray
