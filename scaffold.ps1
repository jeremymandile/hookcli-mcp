# scaffold.ps1
# Hook CLI MCP – Complete Repository Generator (Windows PowerShell)
# Usage: .\scaffold.ps1
# Creates the entire hookcli-mcp project in the current directory

$ErrorActionPreference = "Stop"
$REPO = "hookcli-mcp"

Write-Host "Scaffolding $REPO..." -ForegroundColor Cyan

$dirs = @(
    ".github\workflows", "config", "data\vector_db",
    "hookcli_mcp\api", "hookcli_mcp\auth", "hookcli_mcp\core",
    "hookcli_mcp\db", "hookcli_mcp\observability", "hookcli_mcp\sandbox",
    "hookcli_mcp\services", "hookcli_mcp\tools", "hookcli_mcp\telemetry",
    "tests\rbac", "tests\approval", "tests\bottleneck", "tests\security"
)
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path "$REPO\$dir" -Force | Out-Null
}
Set-Location $REPO
git init

Write-Host "Scaffold complete. Run: pip install -e .[dev] && docker compose up -d" -ForegroundColor Green
