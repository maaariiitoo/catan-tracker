"""
Ajusta estos valores a tu resolución/ventana antes de jugar.

Cómo obtener las coordenadas: haz una captura de pantalla completa mientras
juegas (Win+Shift+S), ábrela en Paint/GIMP y anota las esquinas de cada
región en píxeles (arriba-izquierda y abajo-derecha).

Aquí había tres ajustes más -- MY_USERNAME, GAME_WINDOW_TITLE_HINT y
POLL_INTERVAL_SECONDS -- que solo usaba el tracker por visión. Retirado ese
el 19 de agosto de 2026, no los lee ya nadie y se han quitado: un ajuste que
no hace nada es peor que no tenerlo, porque el día que alguien lo cambie
esperará que pase algo.
"""

# Región del PANEL DE REGISTRO (el cuadro "REGISTRO DE LA PARTIDA")
# formato: (x1, y1, x2, y2)
LOG_PANEL_REGION = (105, 582, 684, 1428)

# Región del TABLERO (donde están las casillas hexagonales)
BOARD_REGION = (715, 241, 1648, 994)

# Ruta de la base de datos SQLite
DB_PATH = "catan_stats.db"

# Idioma de tesseract. Instala el paquete de español para mejor precisión:
#  - Windows: instalador de tesseract, marcar "Spanish" en los language packs
#  - o descargar spa.traineddata en la carpeta tessdata de tu instalación
#  https://github.com/tesseract-ocr/tessdata
OCR_LANG = "spa"  # usa "eng" si no tienes el paquete de español instalado

# Ruta al ejecutable de Tesseract (necesario en Windows si "tesseract" no
# está en el PATH del sistema).
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
