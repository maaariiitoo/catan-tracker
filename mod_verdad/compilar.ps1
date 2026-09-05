# Compila el plugin contra las librerias del juego y de BepInEx, y lo deja
# puesto en BepInEx\plugins.
#
# Se usa el csc de .NET Framework que ya viene con Windows: no hace falta
# instalar nada. Por eso el codigo esta escrito en C# 5 (sin interpolacion
# de cadenas).
param([string]$python = "")

$aqui    = Split-Path -Parent $MyInvocation.MyCommand.Path
# la carpeta del juego se le pregunta a Steam, no va escrita a mano
# Con que Python se le pregunta a Steam. Lo pasa quien llama (-python), que
# sabe cual esta corriendo. Si el .ps1 se lanza a mano no viene, y entonces
# se prueba `py` PRIMERO y `python` despues: en muchos Windows `python` no
# esta en el PATH, y peor aun, suele resolver al stub de la Microsoft Store,
# que no imprime nada y devuelve vacio.
#
# Esto llamaba a `python` a secas. Cuando no estaba, el .ps1 se quedaba sin
# carpeta y decia "No encuentro Catan Universe": una mentira que manda a
# reinstalar Steam a quien lo que le falta es Python.
if (-not $python) {
    foreach ($c in @("py", "python")) {
        $g = Get-Command $c -ErrorAction SilentlyContinue
        if ($g) { $python = $g.Source; break }
    }
}
if (-not $python) {
    Write-Output "No encuentro Python. Instalalo desde python.org y marca Add to PATH."
    exit 1
}

$dicho = & $python (Join-Path $aqui "donde_esta_el_juego.py") 2>$null
if (-not $dicho) {
    Write-Output "Python no ha contestado ($python). Esto NO es un problema de Catan."
    exit 1
}
$juego = ($dicho | Select-String -Pattern "^Catan Universe: (.+)$").Matches.Groups[1].Value
if (-not $juego -or $juego -eq "NO ENCONTRADO" -or -not (Test-Path $juego)) {
    Write-Output "No encuentro Catan Universe. Abre Steam una vez si lo has movido."
    exit 1
}
$managed = Join-Path $juego "CatanUniverse_Data\Managed"
$core    = Join-Path $juego "BepInEx\core"
$csc     = "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"

# El juego esta compilado contra netstandard 2.1, asi que hay que
# referenciar SU netstandard.dll y SU mscorlib.dll (los que trae en
# Managed), no los del Windows. Sin eso, csc no sabe ni que es
# System.Object cuando lo ve venir de las clases del juego.
$refs = @(
    (Join-Path $core "BepInEx.dll"),
    (Join-Path $core "0Harmony.dll"),
    (Join-Path $managed "Assembly-CSharp.dll"),
    (Join-Path $managed "UnityEngine.dll"),
    (Join-Path $managed "UnityEngine.CoreModule.dll"),
    (Join-Path $managed "netstandard.dll"),
    (Join-Path $managed "mscorlib.dll"),
    (Join-Path $managed "System.dll"),
    (Join-Path $managed "System.Core.dll")
)
foreach ($r in $refs) {
    if (-not (Test-Path $r)) { Write-Output "FALTA: $r"; exit 1 }
}

$salida = Join-Path $aqui "CatanVerdad.dll"
# /nostdlib porque las librerias base salen de Managed, no de Windows, y
# /noconfig para que csc no anada por su cuenta las de Windows (csc.rsp las
# mete siempre, y entonces System.dll aparece dos veces y no compila)
$argumentos = @("/target:library", "/optimize+", "/nologo", "/nostdlib+",
                "/noconfig", "/out:$salida")
$argumentos += ($refs | ForEach-Object { "/reference:$_" })
$argumentos += (Join-Path $aqui "CatanVerdad.cs")

& $csc $argumentos
if ($LASTEXITCODE -ne 0) { Write-Output "no compila"; exit $LASTEXITCODE }
Write-Output "compilado: $salida ($([math]::Round((Get-Item $salida).Length/1KB)) KB)"

# Y se deja puesto donde el juego lo va a buscar. Antes esto habia que
# copiarlo a mano, y una copia a mano que se olvida deja al juego cargando
# la version anterior sin decir nada: se recompila, se prueba, y lo que
# corre es el plugin viejo.
$destino = Join-Path $juego "BepInEx\plugins"
if (-not (Test-Path $destino)) { New-Item -ItemType Directory -Force $destino | Out-Null }
try {
    Copy-Item $salida (Join-Path $destino "CatanVerdad.dll") -Force -ErrorAction Stop
    Write-Output "instalado en: $destino"
} catch {
    Write-Output "NO se pudo copiar a $destino"
    Write-Output "  (si el juego esta abierto, cierralo: tiene el .dll cogido)"
    Write-Output "  $($_.Exception.Message)"
    exit 1
}
