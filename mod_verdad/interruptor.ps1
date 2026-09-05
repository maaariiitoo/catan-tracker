# Enciende o apaga el mod.
#
#   .\interruptor.ps1 on     -> el juego arranca CON el mod (partidas contra la IA)
#   .\interruptor.ps1 off    -> el juego arranca limpio, como si no existiera
#   .\interruptor.ps1        -> dice como esta ahora
#
# Esto NO se enciende solo a proposito. El mod se mete dentro del proceso
# del juego, y las condiciones de uso de Catan Universe prohiben modificar
# el cliente: encenderlo es una decision que tomas tu cada vez, no algo que
# pase por defecto mientras juegas online.
#
# La carpeta del juego no va escrita a mano: se le pregunta a Steam, asi
# que esto sigue valiendo si mueves el juego a otro disco.
param([string]$modo = "", [string]$python = "")

$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
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

$cfg = Join-Path $juego "doorstop_config.ini"
if (-not (Test-Path $cfg)) { Write-Output "el mod no esta instalado en $juego"; exit 1 }

$texto = [System.IO.File]::ReadAllText($cfg)

if ($modo -eq "") {
    $estado = if ($texto -match "(?m)^enabled\s*=\s*true") { "ENCENDIDO" } else { "apagado" }
    Write-Output "juego:  $juego"
    Write-Output "el mod esta $estado"
    $plug = Join-Path $juego "BepInEx\plugins\CatanVerdad.dll"
    Write-Output ("plugin instalado: " + $(if (Test-Path $plug) { "si" } else { "NO" }))
    $verdad = Join-Path $juego "verdad_catan"
    if (Test-Path $verdad) {
        $fs = @(Get-ChildItem $verdad -Filter *.jsonl -ErrorAction SilentlyContinue)
        Write-Output "partidas apuntadas: $($fs.Count)  (en $verdad)"
        foreach ($f in $fs) {
            $n = (Get-Content $f.FullName | Measure-Object -Line).Lines
            Write-Output ("   {0}  {1} acciones" -f $f.Name, $n)
        }
    } else {
        Write-Output "todavia no ha apuntado ninguna partida"
    }
    $datos = Join-Path $aqui "datos"
    if (Test-Path $datos) {
        $fotos = @(Get-ChildItem $datos -Recurse -Filter *.png -ErrorAction SilentlyContinue)
        Write-Output "fotos recogidas: $($fotos.Count)"
    }
    exit 0
}

if ($modo -eq "on")  { $texto = $texto -replace "(?m)^enabled\s*=\s*false", "enabled = true" }
elseif ($modo -eq "off") { $texto = $texto -replace "(?m)^enabled\s*=\s*true", "enabled = false" }
else { Write-Output "usa: interruptor.ps1 on | off"; exit 1 }

[System.IO.File]::WriteAllText($cfg, $texto)
$ahora = if ($texto -match "(?m)^enabled\s*=\s*true") { "ENCENDIDO" } else { "apagado" }
Write-Output "el mod queda $ahora"
