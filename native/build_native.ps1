[CmdletBinding()]
param(
    [ValidateSet('Both', 'Core', 'Overlay')]
    [string]$Component = 'Both',
    [string]$Version = '',
    [string]$Target = 'x86_64-pc-windows-msvc',
    [switch]$Offline
)

$ErrorActionPreference = 'Stop'
$nativeRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$projectRoot = Split-Path -Parent $nativeRoot
$buildRoot = Join-Path $nativeRoot 'target'
$binRoot = Join-Path $nativeRoot 'bin'

if (!$Version) {
    $versionSource = Get-Content -LiteralPath (Join-Path $projectRoot 'app_version.py') -Raw
    $versionMatch = [regex]::Match($versionSource, "PROGRAM_VERSION\s*=\s*['`"](?<version>\d+\.\d+\.\d+)['`"]")
    if (!$versionMatch.Success) { throw 'No se pudo leer PROGRAM_VERSION.' }
    $Version = $versionMatch.Groups['version'].Value
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version debe usar major.minor.patch.' }

$cargo = (Get-Command cargo -ErrorAction Stop).Source
$rustc = (Get-Command rustc -ErrorAction Stop).Source
$rustVersion = (& $rustc --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'No se pudo ejecutar rustc.' }

$components = @(
    @{ Name = 'Core'; Crate = 'dragonlab_core'; Dll = 'dragonlab_core.dll' },
    @{ Name = 'Overlay'; Crate = 'dragonlab_overlay'; Dll = 'dragonlab_overlay.dll' }
) | Where-Object { $Component -eq 'Both' -or $_.Name -eq $Component }
$built = @()

foreach ($part in $components) {
    $crateRoot = Join-Path $nativeRoot $part.Crate
    $manifestPath = Join-Path $crateRoot 'Cargo.toml'
    if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Falta $manifestPath" }
    if (!(Test-Path -LiteralPath (Join-Path $crateRoot 'Cargo.lock') -PathType Leaf)) {
        throw "Falta Cargo.lock en $crateRoot. Resuelve y revisa las dependencias antes del build bloqueado."
    }
    $cargoArgs = @('build', '--release', '--locked', '--target', $Target, '--target-dir', $buildRoot, '--manifest-path', $manifestPath)
    if ($Offline) { $cargoArgs += '--offline' }
    & $cargo @cargoArgs
    if ($LASTEXITCODE -ne 0) { throw "Falló el build de $($part.Crate)." }
    $artifact = Join-Path $buildRoot "$Target/release/$($part.Dll)"
    if (!(Test-Path -LiteralPath $artifact -PathType Leaf)) { throw "No se generó $artifact" }
    $built += @{ Source = $artifact; Name = $part.Dll }
}

[void](New-Item -ItemType Directory -Path $binRoot -Force)
foreach ($artifact in $built) {
    Copy-Item -LiteralPath $artifact.Source -Destination (Join-Path $binRoot $artifact.Name) -Force
}

$files = @()
foreach ($dllName in @('dragonlab_core.dll', 'dragonlab_overlay.dll')) {
    $dllPath = Join-Path $binRoot $dllName
    if (Test-Path -LiteralPath $dllPath -PathType Leaf) {
        $files += [ordered]@{
            name = $dllName
            bytes = (Get-Item -LiteralPath $dllPath).Length
            sha256 = (Get-FileHash -LiteralPath $dllPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
}
$manifest = [ordered]@{
    schema = 1
    abi = 1
    version = $Version
    target = $Target
    rustc = $rustVersion
    files = $files
}
$manifestPath = Join-Path $binRoot 'native-manifest.json'
$pendingPath = Join-Path $binRoot 'native-manifest.pending.json'
[IO.File]::WriteAllText($pendingPath, ($manifest | ConvertTo-Json -Depth 6) + "`n", [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $pendingPath -Destination $manifestPath -Force
Write-Output "Build nativo $Version ($Target): $manifestPath"
