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
- Puede **dividir historias largas en varias partes o tomos** (*Part I*, *Part II*…): de forma **automática** según un máximo de páginas (con tamaños parejos y sin cortar capítulos) o de forma **manual** eligiendo qué capítulos van en cada tomo.
- Formatos de papel a elegir: **A4, A5, A6, Carta y folleto** (explicado más abajo).
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
 
Las opciones son `a4`, `a5`, `a6`, `letter` y `booklet`. También podés usar otro archivo de configuración con `--config otro.toml`.
 
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
combine = false
start_on_recto = true
toc_on_recto = false
font_family = "Georgia, 'Times New Roman', serif"
font_size = "11pt"
line_height = 1.45
 
[booklet]
sheet = "a4"
signatures = false
sheets_per_signature = 50
balance = false

[split]
split_long_works = false
max_pages_per_part = 600
enabled = false
# volumes = ["1-3", "4-5", "6-8"]
# names = ["Año 1", "Año 3", "Año 5"]
renumber_chapters = false
```
 
### Todas las opciones
 
| Sección | Opción | Valores | Qué hace |
|---------|--------|---------|----------|
| `[input]` | `dir` | una carpeta | Carpeta donde están los `.html` (por defecto `input`) |
| `[input]` | `output_dir` | una carpeta | Carpeta donde se guardan los PDF (por defecto `output`) |
| `[book]` | `format` | `"a4"`, `"a5"`, `"a6"`, `"letter"`, `"booklet"` | Tamaño del libro (ver tabla de formatos) |
| `[book]` | `combine` | `true` / `false` | `true`: un solo libro con todas las historias. `false`: un PDF por historia |
| `[book]` | `start_on_recto` | `true` / `false` | `true`: cada historia empieza en una página derecha (agrega páginas en blanco si hace falta). Solo tiene efecto si `combine = true` |
| `[book]` | `toc_on_recto` | `true` / `false` | `true`: el índice empieza en una página derecha (agrega una página en blanco después de la portada si hace falta). `false`: va en la página inmediatamente siguiente |
| `[book]` | `font_family` | nombre de fuente | Tipo de letra. Se puede poner una lista de respaldo, por ejemplo `"Garamond, Georgia, serif"`. Usa fuentes instaladas en tu computadora |
| `[book]` | `font_size` | por ejemplo `"11pt"` | Tamaño base de la letra. **Escala todo el libro en proporción** (texto, títulos, subtítulo, autor, índice, citas, encabezado y número de página). Probá `"10pt"` para ahorrar papel o `"12pt"`–`"13pt"` para letra grande |
| `[book]` | `line_height` | por ejemplo `1.45` | Espacio entre renglones. Más alto = más aireado y más páginas |
| `[booklet]` | `sheet` | `"a4"`, `"a5"` o `"letter"` | Solo para folleto: tamaño de la **hoja** que vas a poner en la impresora |
| `[booklet]` | `signatures` | `true` / `false` | Solo para folleto: `true` divide el libro en varios **cuadernillos** más chicos dentro del mismo PDF; `false` arma todo en un único cuadernillo |
| `[booklet]` | `sheets_per_signature` | entero ≥ 1 (por defecto `50`) | Cantidad máxima de **hojas físicas** por cuadernillo cuando `signatures = true` (1 hoja doblada = 4 páginas del libro; 50 hojas = 200 páginas) |
| `[booklet]` | `balance` | `true` / `false` | Solo tiene efecto con `signatures = true`: `false` arma cuadernillos llenos y deja el resto en el último; `true` reparte las hojas lo más parejo posible entre los cuadernillos |
| `[split]` | `split_long_works` | `true` / `false` | `true`: divide automáticamente las historias que superen `max_pages_per_part` en varias partes (*Part I*, *Part II*…), con tamaños parejos y sin cortar capítulos. `false`: las deja completas |
| `[split]` | `max_pages_per_part` | por ejemplo `600` | Cantidad máxima de páginas del PDF por parte cuando `split_long_works = true` (son páginas del libro, no hojas físicas) |
| `[split]` | `enabled` | `true` / `false` | `true`: activa la **división manual en tomos** según `volumes` (requiere un solo archivo `.html` en `input`). Si además está activo `split_long_works`, gana la división manual |
| `[split]` | `volumes` | lista de textos, p. ej. `["1-3", "4", "5-8"]` | Capítulos de cada tomo cuando `enabled = true`. Cada elemento es un rango (`"inicio-fin"`) o un capítulo suelto (`"4"`), usando la **posición** del capítulo en el archivo (desde `1`) |
| `[split]` | `names` | *(opcional)* lista de textos | Un subtítulo por tomo (misma cantidad de elementos que `volumes`). Se muestra debajo del título en la portada y se agrega al nombre del PDF |
| `[split]` | `renumber_chapters` | `true` / `false` | `false`: mantiene la numeración original de los capítulos. `true`: dentro de cada tomo o parte, los capítulos con título `Chapter N` o `Chapter N: Título` vuelven a empezar desde `Chapter 1` (otros títulos no se tocan). Aplica tanto a división manual como automática |
 
Las carpetas se cuentan desde donde está `config.toml`.

> **Nota sobre migración:** `split_long_works` y `max_pages_per_part` antes vivían en `[book]`. Si todavía los tenés ahí, el programa los sigue leyendo pero muestra un aviso para que los muevas a `[split]`. Si están en ambas secciones, gana `[split]`.

### Dividir una historia en tomos (`[split]`)

Además de la división automática por cantidad de páginas (`split_long_works = true`), podés dividir **una historia larga en tomos elegidos por vos** (por ejemplo, separando arcos o años).

1. Dejá **un solo archivo `.html`** en la carpeta `input`.
2. Configurá la sección `[split]` en `config.toml`:

```toml
[split]
enabled = true
volumes = ["1-3", "4", "5-8"]
names = ["Año 1", "La tormenta", "Año 5"]
renumber_chapters = true
```

Qué hace el programa con esa configuración:
- Genera un PDF separado por cada tomo (si tenías `combine = true`, lo ignora con un aviso leve porque no es un error y continúa normalmente). Si usás `format = "booklet"`, cada tomo se arma como folleto aparte (y si `signatures = true`, los cuadernillos se calculan por separado para cada tomo).
- Cada tomo se titula `{Título} Part I`, `{Título} Part II`, etc., y conserva el autor y el resumen.
- Si incluís `names`, cada nombre aparece como subtítulo en la portada y se suma al nombre del archivo (por ejemplo `mi-historia-part-i-ano-1.pdf`).
- Incluso si un tomo tiene **un solo capítulo** (como `"4"` arriba), conserva su índice y el encabezado del capítulo.
- Los números de `volumes` son la **posición del capítulo en el archivo** (`1` = primer capítulo), sin importar el número escrito en el título.

#### Errores comunes en `[split]` y cómo corregirlos

Cuando `enabled = true`, cualquier error en `[split]` detiene el programa antes de generar PDFs e indica exactamente qué corregir:

| Error | Qué pasó | Cómo corregirlo |
|-------|----------|-----------------|
| `input.dir: se encontraron N archivos .html` / `ningún archivo .html` | Hay 0 o más de 1 archivo `.html` en la carpeta de entrada | Dejá un único `.html` en `input` (o poné `enabled = false`) |
| `split.volumes: debe ser una lista de textos, no una sola cadena` | Escribiste `volumes = "1-3, 4-5"` en lugar de una lista | Usá corchetes y comillas por cada tomo: `volumes = ["1-3", "4-5"]` |
| `formato inválido` / `el número de capítulo no puede ser 0` / `el rango está invertido` | Algún elemento tiene letras, un `0` o está al revés (ej. `"5-3"`) | Usá solo números positivos en formato `"N"` o `"N-M"` con `N <= M`, ej. `["1-3", "4", "5-8"]` |
| `hay un salto` / `hay un solapamiento` / `no están en orden ascendente` / `debe empezar en el capítulo 1` | Faltan capítulos entre tomos, alguno se repite o los rangos están desordenados | Empezá en `1`, en orden ascendente y sin huecos ni repetidos: `["1-3", "4-5", "6-7"]` |
| `split.names: tiene X elemento(s), pero split.volumes tiene Y` / `está vacío` | `names` no coincide en cantidad con `volumes` o tiene un texto vacío | Poné un texto no vacío por cada tomo, o comentá/borrá la línea `names` |
| `el rango supera la cantidad de capítulos` / `cobertura incompleta` | La historia tiene menos o más capítulos de los que cubren los rangos | El mensaje muestra la cantidad real de capítulos; ajustá el último rango para que termine exactamente en ese número |
| `la obra tiene un solo capítulo y no se puede dividir en tomos` | El archivo tiene un solo capítulo | Poné `enabled = false` en `[split]` para generarla completa |
 
### Formatos
 
| `format` | Tamaño de la página del libro | Para qué sirve |
|----------|-------------------------------|----------------|
| `"a4"` | 210 × 297 mm | Libro grande, hoja común |
| `"a5"` | 148 × 210 mm | Libro de bolsillo (mitad de A4) |
| `"a6"` | 105 × 148 mm | Libro de bolsillo chico (cuarto de A4 / mitad de A5), ideal para historias cortas |
| `"letter"` | 8,5 × 11 pulgadas | Hoja carta |
| `"booklet"` | La mitad de la hoja elegida en `sheet` (`a4`, `a5` o `letter`) | Imprimir en hojas sueltas y doblarlas para armar un librito (ver abajo) |

### Libros con pocas páginas

Si una historia queda demasiado fina para encuadernar (por ejemplo, unas 40 páginas en A5), tenés tres formas simples de darle más cuerpo:

- **Agrandar letra e interlineado en A5:** como `font_size` escala todo el libro en proporción (títulos, encabezado, pie y espaciados), el diseño sigue equilibrado:
  ```toml
  [book]
  format = "a5"
  font_size = "12pt"
  line_height = 1.6
  ```
- **Pasar a formato A6 con la letra por defecto:** la página es más chica (105 × 148 mm) y los márgenes se achican en proporción, así que la misma historia ocupa bastante más páginas:
  ```toml
  [book]
  format = "a6"
  font_size = "11pt"
  line_height = 1.45
  ```
- **Armar un folleto en hojas A5:** produce páginas tamaño A6 impuestas de a dos por cara sobre hojas A5 apaisadas:
  ```toml
  [book]
  format = "booklet"

  [booklet]
  sheet = "a5"
  ```
 
---
 
## Cómo imprimir
 
**A4, A5, A6 y Carta**
- Abrí el PDF, elegí imprimir y poné la escala en **"Tamaño real"** o **100 %** (no "Ajustar a la página").
- Si elegís `a5` o `a6`, lo ideal es imprimir en papel de ese tamaño (o cortar hojas A4 al medio para A5 / en cuatro para A6). Si no, tu impresora puede ofrecer varias páginas por hoja, aunque conviene probar.
- Para ahorrar papel, imprimí a **doble cara**, volteando por el borde largo, como un libro.
**Folleto (`booklet`)**
1. En `config.toml` poné `format = "booklet"` y en `sheet` el tamaño de hoja que usás (`"a4"`, `"a5"` o `"letter"`).
2. Ejecutá el programa. En la pantalla te dice cuántas hojas vas a usar.
3. Imprimí el PDF en **tamaño real**, a **doble cara** y con la opción **"voltear por el borde corto"**.
4. Juntá las hojas en el orden en que salieron, **doblalas por la mitad** y engrapá o cosé por el pliegue.
- **Si usás `sheet = "a5"`:** la hoja física de impresión es A5 (210 × 148 mm en apaisado). Si solo tenés hojas A4, podés cortarlas por la mitad antes de imprimir (una A4 cortada al medio da dos hojas A5 apaisadas) o imprimir a tamaño real sobre A4 y cortar después, según lo que acepte tu impresora.
La cantidad de páginas se completa sola con páginas en blanco al final, hasta ser múltiplo de 4.

#### Libros gruesos: modo cuadernillos (`signatures`)

Cuando un libro tiene muchas páginas, doblar todas las hojas juntas en un único cuadernillo resulta incómodo o imposible. La encuadernación tradicional resuelve esto dividiendo el libro en varios **cuadernillos**: pequeños grupos de hojas (por ejemplo, de 8 a 50 hojas físicas según el grosor del papel) que se doblan y cosen o pegan por separado, y después se unen en orden para formar el lomo completo.

Para activarlo, agregá estas opciones en `[booklet]` dentro de `config.toml`:

```toml
[book]
format = "booklet"

[booklet]
sheet = "a4"
signatures = true
sheets_per_signature = 50     # hojas físicas por cuadernillo (1 hoja doblada = 4 páginas)
balance = false               # false: llenos + resto al final; true: repartir parejo
```

- **Unidad:** `sheets_per_signature` se mide en **hojas físicas** (las que salen de la impresora). Cada hoja doblada al medio tiene **4 páginas del libro** (2 por cara), así que 50 hojas equivalen a 200 páginas del libro (100 caras en el PDF).
- **`balance = false` (por defecto):** arma cuadernillos completos de `sheets_per_signature` hojas y pone lo que sobra en el último. Por ejemplo, un libro de 230 páginas con 50 hojas por cuadernillo sale en **2 cuadernillos: 50 + 8 hojas** (las páginas en blanco de relleno quedan siempre al final del libro).
- **`balance = true`:** reparte las hojas totales lo más parejo posible entre la misma cantidad de cuadernillos (sin superar `sheets_per_signature` y con una diferencia máxima de 1 hoja entre ellos). Con el mismo ejemplo de 230 páginas y límite 50, salen **2 cuadernillos de 29 + 29 hojas**.
- **Con tomos o varias historias:** los cuadernillos se calculan por cada PDF generado (si dividís una historia con `[split]`, cada tomo tiene sus propios cuadernillos; si `combine = true`, se calculan sobre el libro combinado completo). Si el libro entra en un solo cuadernillo, el resultado es igual al modo folleto normal.
- Si dejás `signatures = true` pero elegís un `format` distinto de `"booklet"`, no da error: muestra un aviso y sigue normalmente con el formato elegido.

**Cómo imprimir y armar con cuadernillos:**
1. Ejecutá el programa. Todo sale en **un único PDF**, con los cuadernillos uno detrás del otro, y en la consola te indica cuántas hojas lleva cada cuadernillo y dónde separar el montón.
2. Imprimí el PDF completo en **tamaño real**, a **doble cara** y con **"voltear por el borde corto"**.
3. Sin desordenar las hojas que salieron de la impresora, **separá el montón** según la cantidad de hojas que te indicó el programa (por ejemplo cada 50 hojas, o en los grupos exactos si usaste `balance = true`).
4. **Doblá cada grupo por la mitad** y **cosé o pegá cada cuadernillo por su pliegue**.
5. **Uní los cuadernillos en orden** (primero el 1, luego el 2, etc.) para armar el libro final.

Si además preferís dividir una historia muy larga en varios libros físicos independientes (cada uno con su portada e índice), podés combinar esto con `combine = false` o con la sección `[split]` (`split_long_works = true` o `enabled = true`).
 
---
 
## Si algo falla
 
**"No se pudo importar WeasyPrint" o `cannot load library`**
Falta Pango o el programa no lo encuentra. Repetí el paso 2. En Windows, si instalaste MSYS2 en otra carpeta, buscá la ayuda oficial: [guía de instalación de WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
 
**"No existe la carpeta de entrada" o "No se encontraron obras válidas"**
Revisá que la carpeta `input` exista y que adentro haya archivos `.html` descargados de AO3.
 
**Un archivo aparece como `[aviso]` y no sale en el libro**
No parece una descarga de AO3 en HTML (por ejemplo, está dañado o es otro formato). El resto del libro se genera igual.
 
**"Error de configuración" o mensajes `[error] split...`**
Hay un valor mal escrito en `config.toml` o un problema en los rangos de `[split]`. El mensaje indica exactamente qué corregir y muestra un ejemplo válido. Revisá la tabla de errores comunes de `[split]` más arriba, las comillas y que `true`/`false` estén en minúsculas.
 
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