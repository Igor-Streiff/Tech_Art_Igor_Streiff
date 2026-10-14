# Ejecuta rig_renamer.py con mayapy (CLI en Maya).
# Uso:
#   .\Run-Renamer-Maya.ps1 -Character hero -Rig hero_rig
#   .\Run-Renamer-Maya.ps1 -Character hero -Rig hero_rig -Apply

param(
    [Parameter(Mandatory = $true)]
    [string]$Character,

    [Parameter(Mandatory = $true)]
    [string]$Rig,

    [switch]$Apply,
    [switch]$IncludeJoints
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Find-Mayapy {
    $candidates = @(
        "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe",
        "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe",
        "C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe",
        "C:\Program Files\Autodesk\Maya2023\bin\mayapy.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "No se encontró mayapy.exe. Instalá Maya o editá la ruta en Run-Renamer-Maya.ps1."
}

$mayapy = Find-Mayapy
$argsList = @(
    (Join-Path $ProjectRoot "rig_renamer.py"),
    "--rig", $Rig,
    "--character", $Character
)
if ($Apply) { $argsList += "--apply" }
if ($IncludeJoints) { $argsList += "--include-joints" }

$env:PYTHONPATH = $ProjectRoot
Write-Host ">> $mayapy $($argsList -join ' ')"
& $mayapy @argsList
