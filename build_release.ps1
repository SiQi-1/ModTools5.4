param(
    [string]$PythonExe = "python",
    [string]$AppName = "ModTools5.4",
    [string]$ProjectRoot = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path $ProjectRoot).Path
$dist = Join-Path $root "dist"
$build = Join-Path $root "build"
$spec = Join-Path $root "ModTools5.4.spec"
$entry = Join-Path $root "ModTools5.4.py"
$db = Join-Path $root "local_text_New.sqlite"
$pkg = Join-Path $root "ModTools_5_4"

# 知识入口/命令/检索质量不合格时，在打包前停止。
Push-Location $root
try {
    & $PythonExe -B -m modgen.cli skill --check
    if ($LASTEXITCODE -ne 0) { throw "Knowledge quality check failed" }
} finally {
    Pop-Location
}

if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }

# 运行时资源整目录递归打包（含 base.qss、FontIcons、data JSON、From/ artdef 等）
$addDataArgs = @(
    "--add-data", "$db;.",
    "--add-data", "$pkg\data;ModTools_5_4/data",
    "--add-data", "$pkg\resources;ModTools_5_4/resources",
    "--add-data", "$pkg\From;ModTools_5_4/From",
    "--add-data", "$(Join-Path $root 'modgen\schemas');modgen/schemas"
)

& $PythonExe -m PyInstaller --noconfirm --clean --onefile --noconsole --name $AppName @addDataArgs $entry

$releaseDir = Join-Path $root "release"
if (Test-Path $releaseDir) { Remove-Item $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $releaseDir | Out-Null

$exePath = Join-Path $dist "$AppName.exe"
if (-not (Test-Path $exePath)) {
    throw "Exe not found: $exePath"
}

Copy-Item $exePath (Join-Path $releaseDir "$AppName.exe") -Force
Copy-Item $db (Join-Path $releaseDir "local_text_New.sqlite") -Force
Copy-Item (Join-Path $pkg "data\settings.json") (Join-Path $releaseDir "settings.json") -Force
Copy-Item (Join-Path $pkg "data") (Join-Path $releaseDir "data") -Recurse -Force
Remove-Item (Join-Path $releaseDir "data\settings.json") -ErrorAction SilentlyContinue

# AI 生成 .CIV 工具（modgen，纯标准库 CLI + schemas + AGENTS.md 指南）
$modgenSrc = Join-Path $root "modgen"
$modgenDst = Join-Path $releaseDir "modgen"
if (Test-Path $modgenSrc) {
    Copy-Item $modgenSrc $modgenDst -Recurse -Force
    Get-ChildItem $modgenDst -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# 本地技能库（skills，知识库随发布包分发；modgen skill 检索入口）
$skillsSrc = Join-Path $root "skills"
if (Test-Path $skillsSrc) {
    Copy-Item $skillsSrc (Join-Path $releaseDir "skills") -Recurse -Force
    Get-ChildItem (Join-Path $releaseDir "skills") -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# 源码发行（agent 可操作/修改/调试的完整源码 + 初始化/工具脚本 + 文档）
Copy-Item (Join-Path $root "ModTools5.4.py") $releaseDir -Force
Copy-Item (Join-Path $root "requirements.txt") $releaseDir -Force
Copy-Item (Join-Path $root "LICENSE") $releaseDir -Force
Copy-Item (Join-Path $root "README.md") $releaseDir -Force
# 社区来源、保留的上游许可证和实际采用范围随源码发行。
Copy-Item (Join-Path $root "THIRD_PARTY_NOTICES.md") $releaseDir -Force
Copy-Item (Join-Path $root "licenses") (Join-Path $releaseDir "licenses") -Recurse -Force
$communityDocsDst = Join-Path $releaseDir "docs"
New-Item -ItemType Directory -Path $communityDocsDst -Force | Out-Null
Copy-Item (Join-Path $root "docs\COMMUNITY_SKILL_INTEGRATION.md") $communityDocsDst -Force
Copy-Item (Join-Path $root "AGENT_SETUP.md") $releaseDir -Force
Copy-Item (Join-Path $root "AGENT.md") $releaseDir -Force
Copy-Item (Join-Path $root "AGENTS.md") $releaseDir -Force
Copy-Item (Join-Path $root "CLAUDE.md") $releaseDir -Force
Copy-Item (Join-Path $root "CIV6_MOD_TUTORIAL.md") $releaseDir -Force
Copy-Item $pkg (Join-Path $releaseDir "ModTools_5_4") -Recurse -Force
Get-ChildItem (Join-Path $releaseDir "ModTools_5_4") -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $releaseDir "ModTools_5_4\logs") -Recurse -Force -ErrorAction SilentlyContinue
$toolsDst = Join-Path $releaseDir "tools"
New-Item -ItemType Directory -Path $toolsDst | Out-Null
Copy-Item (Join-Path $root "tools\setup_env.py") $toolsDst -Force
Copy-Item (Join-Path $root "tools\register_file_association.py") $toolsDst -Force

# 只分发维护归档说明，不分发停用脚本。
$legacyNotes = Join-Path $toolsDst "legacy_skill_builders"
New-Item -ItemType Directory -Path $legacyNotes -Force | Out-Null
Copy-Item (Join-Path $root "tools\legacy_skill_builders\README.md") $legacyNotes -Force

$zipPath = Join-Path $root "$AppName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -Force

Write-Host "Release prepared: $zipPath"