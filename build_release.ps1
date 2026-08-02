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
$settings = Join-Path $root "ModTools_5_4\data\settings.json"
$stdColors = Join-Path $root "ModTools_5_4\data\standard_colors.json"
$resImages = Join-Path $root "ModTools_5_4\resources\images"

if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }

$addDataArgs = @(
    "--add-data", "$db;.",
    "--add-data", "$settings;ModTools_5_4/data",
    "--add-data", "$stdColors;ModTools_5_4/data",
    "--add-data", "$resImages\citybanner_backing.png;ModTools_5_4/resources/images",
    "--add-data", "$resImages\citybanner_base.png;ModTools_5_4/resources/images",
    "--add-data", "$resImages\citybanner_base_mask.png;ModTools_5_4/resources/images",
    "--add-data", "$resImages\citybanner_darken_mask.png;ModTools_5_4/resources/images",
    "--add-data", "$resImages\citybanner_lighten_mask.png;ModTools_5_4/resources/images",
    "--add-data", "$resImages\citybanner_overlay.png;ModTools_5_4/resources/images",
    "--add-data", "$resImages\citybanner_secondary.png;ModTools_5_4/resources/images"
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
Copy-Item $settings (Join-Path $releaseDir "settings.json") -Force

$zipPath = Join-Path $root "$AppName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -Force

Write-Host "Release prepared: $zipPath"