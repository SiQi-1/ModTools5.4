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

if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }

# 运行时资源整目录递归打包（含 base.qss、FontIcons、data JSON、From/ artdef 等）
$addDataArgs = @(
    "--add-data", "$db;.",
    "--add-data", "$pkg\data;ModTools_5_4/data",
    "--add-data", "$pkg\resources;ModTools_5_4/resources",
    "--add-data", "$pkg\From;ModTools_5_4/From"
)

& $PythonExe -m PyInstaller --noconfirm --clean --onefile --noconsole --name $AppName @addDataArgs $entry

$releaseDir = Join-Path $root "release"
if (Test-Path $releaseDir) { Remove-Item $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $releaseDir | Out-Null

$exePath = Join-Path $dist "$AppName.exe"
if (-not (Test-Path $exePath)) {
    throw "未找到生成的 exe: $exePath"
}

Copy-Item $exePath (Join-Path $releaseDir "$AppName.exe") -Force
Copy-Item $db (Join-Path $releaseDir "local_text_New.sqlite") -Force
Copy-Item (Join-Path $pkg "data\settings.json") (Join-Path $releaseDir "settings.json") -Force

$zipPath = Join-Path $root "$AppName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -Force

Write-Host "Release prepared: $zipPath"