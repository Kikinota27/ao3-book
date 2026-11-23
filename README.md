# ao3-book
 
Convierte historias descargadas de **AO3 (Archive of Our Own)** en formato HTML en un **PDF listo para imprimir como libro**, todas con el mismo formato.
 
Ponés los archivos `.html` en una carpeta, ejecutás un comando y obtenés el PDF.
 
---
 
## Qué hace
 
- Convierte todos los `.html` de una carpeta en un PDF con formato de libro.
- Cada historia queda con esta estructura: **título y autor → resumen → índice → capítulos**.
- **Índice con números de página**, y marcadores en el PDF para navegar en pantalla.
- Limpia los títulos de capítulo:
  - `Chapter 1: Chapter 1` se muestra como `Chapter 1`.
  - Si el capítulo tiene un título propio (`Chapter 3: Algo`), lo deja como está.
  - Si la historia tiene **un solo capítulo**, no muestra el título de capítulo ni el índice.
- Descarta lo que no sirve en papel: tags, estadísticas, notas del autor, notas finales y links.
- Puede generar **un solo libro con todas las historias** (ordenadas alfabéticamente por título) o **un PDF por historia**.
- Puede **dividir historias muy largas en varias partes** (*Part I*, *Part II*…) según un máximo de páginas, con tamaños parejos y sin cortar capítulos por la mitad.
- Formatos de papel a elegir: **A4, A5, Carta y folleto** (explicado más abajo).
- Formato de libro: márgenes pensados para encuadernar (más espacio del lado del lomo), título de la historia arriba, número de página abajo, texto justificado con sangría y separador de escenas `* * *`.
- Si un archivo está dañado o no es de AO3, avisa y sigue con los demás.
---
 
## Qué necesitás instalar
 
| Qué | Para qué | Cómo se instala |
|-----|----------|-----------------|
| **Python 3.11 o más nuevo** | Es el lenguaje en el que está hecho el programa | Ver paso a paso |
| **Pango** | Librería del sistema que usa WeasyPrint para dibujar el PDF | Ver paso a paso (cambia según tu sistema) |
| **Paquetes de Python** | El resto de las piezas | Se instalan solos con un comando (ver paso 4) |
 
Los paquetes de Python que se instalan con `requirements.txt` son:
 
| Paquete | Para qué sirve |
|---------|----------------|
| `beautifulsoup4` y `lxml` | Leer los archivos HTML de AO3 |
| `jinja2` | Armar el libro a partir de una plantilla |
| `weasyprint` | Convertir el libro a PDF |
| `pypdf` | Reordenar las páginas para el modo folleto y contar páginas al dividir historias largas |
| `pytest` | Solo para correr las pruebas (opcional) |
 
---
 
## Instalación paso a paso
 
Hacé esto **una sola vez**.
 
### Paso 1: Instalar Python
 
- **Windows:** abrí la **Microsoft Store**, buscá **Python** (la última versión) e instalalo.
  También podés bajarlo de [python.org/downloads](https://www.python.org/downloads/). En ese caso, marcá la casilla **"Add python.exe to PATH"** durante la instalación.
- **Mac:** instalá [Homebrew](https://brew.sh) y luego, en la Terminal: `brew install python`
- **Linux (Ubuntu/Debian):** en la terminal: `sudo apt install python3 python3-venv python3-pip`
Para comprobar que quedó bien, abrí una terminal (ver el paso 3) y escribí `python --version` (en Mac y Linux: `python3 --version`). Tiene que decir 3.11 o más.
 
### Paso 2: Instalar Pango
 
Es la parte que más trabajo da, sobre todo en Windows.
 
- **Mac:** en la Terminal: `brew install pango libffi`
- **Linux (Ubuntu/Debian):** en la terminal:
```
sudo apt install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libffi-dev libjpeg-dev libopenjp2-7-dev
```
- **Windows:**
  1. Descargá e instalá [MSYS2](https://www.msys2.org) dejando todas las opciones por defecto.
  2. Cuando termine, se abre una ventana de MSYS2. Escribí este comando y apretá Enter:
```
pacman -S mingw-w64-x86_64-pango
```
  3. Cuando termine, cerrá esa ventana.
  Si más adelante aparece un error del tipo `cannot load library`, mirá la sección "Si algo falla".
  Otra opción en Windows es usar WSL (Linux dentro de Windows) y seguir los pasos de Linux.
 
### Paso 3: Abrir una terminal en la carpeta del proyecto
 
La terminal es la ventana donde se escriben los comandos. Tiene que estar abierta **dentro de la carpeta del proyecto** (la que tiene `run.py` y `config.toml`).
 
- **Windows:** abrí la carpeta, hacé clic en la barra de direcciones de arriba, escribí `cmd` y apretá Enter.
- **Mac:** abrí la Terminal, escribí `cd ` (con un espacio al final), arrastrá la carpeta del proyecto a la ventana y apretá Enter.
- **Linux:** clic derecho dentro de la carpeta y **"Abrir en terminal"**.
### Paso 4: Instalar los paquetes
 
Escribí estos dos comandos, uno por vez, y esperá a que cada uno termine.
 
**Windows:**
```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```
 
**Mac y Linux:**
```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```
 
El primero crea una carpeta `venv` donde quedan guardados los paquetes (no ensucia el resto de tu computadora). El segundo los instala.
 
### Paso 5: Comprobar que todo funciona
 
**Windows:**
```
venv\Scripts\python -m weasyprint --info
```
 
**Mac y Linux:**
```
venv/bin/python -m weasyprint --info
```
 
Si muestra información de versiones, está todo listo. Si muestra un error, mirá "Si algo falla".
 
---
 
## Cómo usarlo
 
1. **Copiá los archivos `.html`** de AO3 a la carpeta `input`.
2. *(Opcional)* Abrí `config.toml` con el Bloc de notas y cambiá lo que quieras (ver sección siguiente).
3. Abrí una terminal en la carpeta del proyecto (paso 3) y ejecutá:
   **Windows:**
```
venv\Scripts\python run.py
```
 
   **Mac y Linux:**
```
venv/bin/python run.py
```
 
4. **El PDF aparece en la carpeta `output`.** Si `combine = true` se llama `libro.pdf`; si es `false`, hay un PDF por historia con el título como nombre.
Cada vez que lo ejecutás, los PDF anteriores con el mismo nombre se **reemplazan**. Si querés conservar uno, copialo a otro lado antes.
 
### Cambiar el formato sin tocar el archivo
 
Agregando `--format` a cualquier comando de arriba, por ejemplo para probar el folleto:
 
```
venv\Scripts\python run.py --format booklet
```
 
Las opciones son `a4`, `a5`, `letter` y `booklet`. También podés usar otro archivo de configuración con `--config otro.toml`.
 
---
 
## Cómo cambiar la configuración
 
Todo se cambia en el archivo **`config.toml`**, que se abre con cualquier editor de texto (Bloc de notas, TextEdit, etc.). Después de guardarlo, volvé a ejecutar el programa.
 
Reglas para editarlo:
- Los textos van **entre comillas** (`"a5"`).
- Los valores sí/no se escriben `true` o `false`, **en minúsculas y sin comillas**.
- Lo que está después de un `#` es un comentario y se ignora.
Así viene por defecto:
 
```toml
[input]
dir = "input"
output_dir = "output"
 
[book]
format = "a5"
combine = true
start_on_recto = true
toc_on_recto = false
font_family = "Georgia, 'Times New Roman', serif"
font_size = "11pt"
line_height = 1.45
split_long_works = false
max_pages_per_part = 400
 
[booklet]
sheet = "a4"
```
 
### Todas las opciones
 
| Opción | Valores | Qué hace |
|--------|---------|----------|
| `dir` | una carpeta | Carpeta donde están los `.html` (por defecto `input`) |
| `output_dir` | una carpeta | Carpeta donde se guardan los PDF (por defecto `output`) |
| `format` | `"a4"`, `"a5"`, `"letter"`, `"booklet"` | Tamaño del libro (ver tabla de formatos) |
| `combine` | `true` / `false` | `true`: un solo libro con todas las historias. `false`: un PDF por historia |
| `start_on_recto` | `true` / `false` | `true`: cada historia empieza en una página derecha (agrega páginas en blanco si hace falta). Solo tiene efecto si `combine = true` |
| `toc_on_recto` | `true` / `false` | `true`: el índice empieza en una página derecha (agrega una página en blanco después de la portada si hace falta). `false`: va en la página inmediatamente siguiente |
| `font_family` | nombre de fuente | Tipo de letra. Se puede poner una lista de respaldo, por ejemplo `"Garamond, Georgia, serif"`. Usa fuentes instaladas en tu computadora |
| `font_size` | por ejemplo `"11pt"` | Tamaño de la letra. Probá `"10pt"` para ahorrar papel o `"13pt"` para letra grande |
| `line_height` | por ejemplo `1.45` | Espacio entre renglones. Más alto = más aireado y más páginas |
| `split_long_works` | `true` / `false` | `true`: divide automáticamente las historias que superen `max_pages_per_part` en varias partes (*Part I*, *Part II*…), con tamaños parejos y sin cortar capítulos. `false`: las deja completas |
| `max_pages_per_part` | por ejemplo `400` | Cantidad máxima de páginas del PDF por parte cuando `split_long_works = true` (son páginas del libro, no hojas físicas) |
| `sheet` | `"a4"` o `"letter"` | Solo para folleto: tamaño de la **hoja** que vas a poner en la impresora |
 
Las carpetas se cuentan desde donde está `config.toml`.
 
### Formatos
 
| `format` | Tamaño de la página del libro | Para qué sirve |
|----------|-------------------------------|----------------|
| `"a4"` | 210 × 297 mm | Libro grande, hoja común |
| `"a5"` | 148 × 210 mm | Libro de bolsillo (mitad de A4) |
| `"letter"` | 8,5 × 11 pulgadas | Hoja carta |
| `"booklet"` | La mitad de la hoja elegida en `sheet` | Imprimir en hojas sueltas y doblarlas para armar un librito (ver abajo) |
 
---
 
## Cómo imprimir
 
**A4, A5 y Carta**
- Abrí el PDF, elegí imprimir y poné la escala en **"Tamaño real"** o **100 %** (no "Ajustar a la página").
- Si elegís `a5`, lo ideal es imprimir en papel A5. Si no, tu impresora puede ofrecer "2 páginas por hoja", aunque conviene probar.
- Para ahorrar papel, imprimí a **doble cara**, volteando por el borde largo, como un libro.
**Folleto (`booklet`)**
1. En `config.toml` poné `format = "booklet"` y en `sheet` el tamaño de hoja que usás (`"a4"` o `"letter"`).
2. Ejecutá el programa. En la pantalla te dice cuántas hojas vas a usar.
3. Imprimí el PDF en **tamaño real**, a **doble cara** y con la opción **"voltear por el borde corto"**.
4. Juntá las hojas en el orden en que salieron, **doblalas por la mitad** y engrapá o cosé por el pliegue.
La cantidad de páginas se completa sola con páginas en blanco al final, hasta ser múltiplo de 4. Los libros muy gruesos son difíciles de doblar en un solo cuadernillo: si te pasa, usá `combine = false` para hacer un librito por historia (y `split_long_works = true` si una sola historia sigue siendo demasiado larga).
 
---
 
## Si algo falla
 
**"No se pudo importar WeasyPrint" o `cannot load library`**
Falta Pango o el programa no lo encuentra. Repetí el paso 2. En Windows, si instalaste MSYS2 en otra carpeta, buscá la ayuda oficial: [guía de instalación de WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
 
**"No existe la carpeta de entrada" o "No se encontraron obras válidas"**
Revisá que la carpeta `input` exista y que adentro haya archivos `.html` descargados de AO3.
 
**Un archivo aparece como `[aviso]` y no sale en el libro**
No parece una descarga de AO3 en HTML (por ejemplo, está dañado o es otro formato). El resto del libro se genera igual.
 
**"Error de configuración"**
Hay un valor mal escrito en `config.toml`. El mensaje indica cuál y cuáles son las opciones válidas. Revisá las comillas y que `true`/`false` estén en minúsculas.
 
**La letra no se ve como esperaba**
La fuente que pusiste en `font_family` no está instalada en tu computadora, y el programa usa la siguiente de la lista. Probá con otra o instalá la fuente.
 
**El libro tiene páginas en blanco**
Es normal con `start_on_recto = true`: se agregan para que cada historia empiece en una página derecha. Poné `false` para evitarlas.
 
---
 
## Qué no hace (por ahora)
 
- No incluye imágenes, notas de capítulo ni notas finales de AO3.
- No genera portada general ni índice general de todas las historias.
- Los márgenes no se cambian desde `config.toml`; dependen del formato elegido.
- Los guiones de fin de renglón están pensados para texto en inglés.
- No genera EPUB ni otros formatos, solo PDF.
---
 
## Para quien quiera ver el código
 
```
ao3-book/
├── run.py              # lanzador
├── config.toml         # configuración
├── requirements.txt    # paquetes de Python
├── input/              # acá van los .html
├── output/             # acá salen los PDF
├── src/ao3book/
│   ├── parser.py       # lee el HTML de AO3
│   ├── split.py        # divide historias largas en partes
│   ├── build.py        # arma el libro
│   ├── render.py       # lo convierte a PDF
│   ├── booklet.py      # reordena páginas para folleto
│   ├── config.py       # lee config.toml
│   ├── templates/      # estructura del libro
│   └── styles/         # aspecto del libro (CSS)
└── tests/              # pruebas automáticas
```
 
Para correr las pruebas: `venv\Scripts\python -m pytest` (Windows) o `venv/bin/python -m pytest` (Mac y Linux).