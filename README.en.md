🇪🇸 [Leer en español](README.md)

# ao3-book

Converts stories downloaded from **AO3 (Archive of Our Own)** in HTML format into a **print-ready book PDF**, all styled consistently.

Drop your `.html` files into a folder, run one command, and get your PDF.

## Contents

- [What it does](#what-it-does)
- [What you need to install](#what-you-need-to-install)
- [Step-by-step installation](#step-by-step-installation)
- [How to use it](#how-to-use-it)
- [How to change the configuration](#how-to-change-the-configuration)
- [How to print](#how-to-print)
- [Troubleshooting](#troubleshooting)
- [What it doesn't do (for now)](#what-it-doesnt-do-for-now)
- [For anyone who wants to look at the code](#for-anyone-who-wants-to-look-at-the-code)

---

## What it does

- Converts every `.html` file in a folder into a book-formatted PDF.
- Each story follows this structure: **title and author → summary → table of contents → chapters**.
- **Table of contents with page numbers**, plus PDF bookmarks for reading on screen.
- Cleans up chapter headings:
  - `Chapter 1: Chapter 1` becomes `Chapter 1`.
  - If a chapter has its own title (`Chapter 3: Something`), it is kept as-is.
  - If a story has **only one chapter**, both the chapter heading and the table of contents are omitted.
- Strips out what doesn't belong on paper: tags, stats, author's notes, end notes, and links.
- Can generate **one combined book with all stories** (sorted alphabetically by title) or **one PDF per story**.
- Can **split long stories into multiple parts or volumes** (*Part I*, *Part II*…): either **automatically** based on a maximum page count (evenly balanced and without splitting mid-chapter) or **manually** by choosing which chapters go into each volume.
- Choice of paper formats: **A4, A5, A6, Letter, and booklet** (explained below).
- Book layout: binding-friendly mirrored margins (wider on the spine side), story title at the top, page number at the bottom, justified text with indented paragraphs, and `* * *` scene breaks.
- If a file is corrupted or isn't from AO3, it prints a warning and continues with the rest.

---

## What you need to install

| What | What it's for | How to install it |
|------|---------------|-------------------|
| **Python 3.11 or newer** | The programming language the tool is written in | See step-by-step guide |
| **Pango** | System library used by WeasyPrint to render the PDF | See step-by-step guide (varies by OS) |
| **Python packages** | The remaining components | Installed automatically with one command (see Step 4) |

The Python packages installed via `requirements.txt` are:

| Package | What it does |
|---------|--------------|
| `beautifulsoup4` and `lxml` | Reads AO3 HTML files |
| `jinja2` | Builds the book from a template |
| `weasyprint` | Converts the book into a PDF |
| `pypdf` | Reorders pages for booklet mode and counts pages when splitting long stories |
| `pytest` | Only needed to run tests (optional) |

---

## Step-by-step installation

You only need to do this **once**.

### Step 0: Get the project

Choose one of these two options:

- **Download as ZIP (easiest, no Git required):**
  1. Go to [github.com/Kikinota27/ao3-book](https://github.com/Kikinota27/ao3-book).
  2. Click the green **`<> Code`** button, then click **"Download ZIP"**.
  3. Unzip the downloaded file into the folder of your choice (for example, `ao3-book`).
- **Clone with Git (if you already have Git installed):** open a terminal where you want to save the project and run:
```
git clone https://github.com/Kikinota27/ao3-book.git
```

### Step 1: Install Python

- **Windows:** open the **Microsoft Store**, search for **Python** (the latest version), and install it.
  You can also download it from [python.org/downloads](https://www.python.org/downloads/). If you do, check the **"Add python.exe to PATH"** box during installation.
- **Mac:** install [Homebrew](https://brew.sh), then run in Terminal: `brew install python`
- **Linux (Ubuntu/Debian):** run in a terminal: `sudo apt install python3 python3-venv python3-pip`

To verify it installed properly, open a terminal (see Step 3) and type `python --version` (on Mac and Linux: `python3 --version`). It should report 3.11 or higher.

### Step 2: Install Pango

This is the trickiest part, especially on Windows.

- **Mac:** in Terminal: `brew install pango libffi`
- **Linux (Ubuntu/Debian):** in a terminal:
```
sudo apt install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libffi-dev libjpeg-dev libopenjp2-7-dev
```
- **Windows:**
  1. Download and install [MSYS2](https://www.msys2.org), leaving all default options as-is.
  2. Once finished, an MSYS2 window opens. Type this command and press Enter:
```
pacman -S mingw-w64-x86_64-pango
```
  3. When it finishes, close that window.
  If you later see a `cannot load library` error, check the "Troubleshooting" section.
  Another option on Windows is using WSL (Linux inside Windows) and following the Linux steps instead.

### Step 3: Open a terminal in the project folder

The terminal is the window where you type commands. It needs to be open **inside the project folder** (the one containing `run.py` and `config.toml`).

- **Windows:** open the folder, click the address bar at the top, type `cmd`, and press Enter.
- **Mac:** open Terminal, type `cd ` (with a trailing space), drag the project folder into the window, and press Enter.
- **Linux:** right-click inside the folder and select **"Open in Terminal"**.

### Step 4: Install the packages

Run these two commands one at a time and wait for each to finish.

**Windows:**
```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

**Mac and Linux:**
```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

The first command creates a `venv` folder to keep the packages isolated (so it doesn't clutter the rest of your computer). The second installs them.

### Step 5: Check that everything works

**Windows:**
```
venv\Scripts\python -m weasyprint --info
```

**Mac and Linux:**
```
venv/bin/python -m weasyprint --info
```

If it prints version information, you're all set. If it shows an error, check "Troubleshooting".

---

## How to use it

1. **Copy your AO3 `.html` files** into the `input` folder.
2. *(Optional)* Open `config.toml` in a text editor (Notepad, TextEdit, etc.) and adjust any settings you want (see the next section).
3. Open a terminal in the project folder (Step 3) and run:
   **Windows:**
```
venv\Scripts\python run.py
```

   **Mac and Linux:**
```
venv/bin/python run.py
```

4. **The PDF appears in the `output` folder.** If `combine = true`, it is named `libro.pdf`; if `false`, there is one PDF per story named after its title.
Every time you run it, existing PDFs with the same name are **overwritten**. If you want to keep one, copy it somewhere else first.

### Changing the format without editing the file

Add `--format` to any of the commands above—for example, to try booklet mode:

```
venv\Scripts\python run.py --format booklet
```

Available options are `a4`, `a5`, `a6`, `letter`, and `booklet`. You can also point to a different configuration file with `--config otro.toml`.

---

## How to change the configuration

Everything is configured in **`config.toml`**, which you can open with any plain-text editor (Notepad, TextEdit, etc.). After saving your changes, run the program again.

Rules for editing it:
- Text values go **in quotes** (`"a5"`).
- Yes/no values are written as `true` or `false`, **lowercase and without quotes**.
- Anything after a `#` is a comment and is ignored.

Here are the defaults:

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

### All options

| Section | Option | Values | What it does |
|---------|--------|--------|--------------|
| `[input]` | `dir` | a folder path | Folder containing the `.html` files (default: `input`) |
| `[input]` | `output_dir` | a folder path | Folder where PDFs are saved (default: `output`) |
| `[book]` | `format` | `"a4"`, `"a5"`, `"a6"`, `"letter"`, `"booklet"` | Book page size (see the Formats table) |
| `[book]` | `combine` | `true` / `false` | `true`: a single book with all stories. `false`: one PDF per story |
| `[book]` | `start_on_recto` | `true` / `false` | `true`: each story starts on a right-hand page (adds blank pages if needed). Only applies when `combine = true` |
| `[book]` | `toc_on_recto` | `true` / `false` | `true`: the table of contents starts on a right-hand page (adds a blank page after the title page if needed). `false`: starts on the immediately following page |
| `[book]` | `font_family` | font name(s) | Typeface. Supports a fallback list, e.g. `"Garamond, Georgia, serif"`. Uses fonts installed on your computer |
| `[book]` | `font_size` | e.g. `"11pt"` | Base font size. **Scales the entire book proportionally** (body text, headings, subtitle, author, table of contents, blockquotes, running header, and page number). Try `"10pt"` to save paper or `"12pt"`–`"13pt"` for larger print |
| `[book]` | `line_height` | e.g. `1.45` | Line spacing. Higher = more open layout and more pages |
| `[booklet]` | `sheet` | `"a4"`, `"a5"`, or `"letter"` | Booklet mode only: size of the **physical sheet** you load into your printer |
| `[booklet]` | `signatures` | `true` / `false` | Booklet mode only: `true` splits the book into smaller **signatures** within the same PDF; `false` imposes the whole book as a single signature |
| `[booklet]` | `sheets_per_signature` | integer ≥ 1 (default: `50`) | Maximum number of **physical sheets** per signature when `signatures = true` (1 folded sheet = 4 book pages; 50 sheets = 200 pages) |
| `[booklet]` | `balance` | `true` / `false` | Only applies when `signatures = true`: `false` fills signatures to the limit and puts the remainder in the last one; `true` distributes sheets as evenly as possible across signatures |
| `[split]` | `split_long_works` | `true` / `false` | `true`: automatically splits stories longer than `max_pages_per_part` into multiple parts (*Part I*, *Part II*…), evenly sized and never splitting a chapter. `false`: leaves them whole |
| `[split]` | `max_pages_per_part` | e.g. `600` | Maximum PDF pages per part when `split_long_works = true` (book pages, not physical sheets) |
| `[split]` | `enabled` | `true` / `false` | `true`: enables **manual splitting into volumes** using `volumes` (requires a single `.html` file in `input`). If `split_long_works` is also enabled, manual splitting takes precedence |
| `[split]` | `volumes` | list of strings, e.g. `["1-3", "4", "5-8"]` | Chapters for each volume when `enabled = true`. Each entry is a range (`"start-end"`) or a single chapter (`"4"`), using the chapter's **position** in the file (starting at `1`) |
| `[split]` | `names` | *(optional)* list of strings | One subtitle per volume (same number of entries as `volumes`). Shown below the title on the title page and appended to the PDF filename |
| `[split]` | `renumber_chapters` | `true` / `false` | `false`: keeps original chapter numbering. `true`: inside each volume or part, chapters titled `Chapter N` or `Chapter N: Title` restart from `Chapter 1` (other titles are left untouched). Applies to both manual and automatic splitting |

Folder paths are resolved relative to the location of `config.toml`.

> **Migration note:** `split_long_works` and `max_pages_per_part` previously lived in `[book]`. If they are still there, the program will still read them but print a warning asking you to move them to `[split]`. If present in both sections, `[split]` takes precedence.

### Splitting a story into volumes (`[split]`)

In addition to automatic splitting by page count (`split_long_works = true`), you can split **a long story into custom volumes** (for example, separating story arcs or years).

1. Place **a single `.html` file** in the `input` folder.
2. Configure the `[split]` section in `config.toml`:

```toml
[split]
enabled = true
volumes = ["1-3", "4", "5-8"]
names = ["Año 1", "La tormenta", "Año 5"]
renumber_chapters = true
```

What the program does with this setup:
- Generates a separate PDF for each volume (if `combine = true` was set, it is ignored with a mild warning since it isn't an error, and execution continues normally). If you use `format = "booklet"`, each volume is imposed as its own booklet (and if `signatures = true`, signatures are calculated separately for each volume).
- Each volume is titled `{Title} Part I`, `{Title} Part II`, etc., keeping the original author and summary.
- If you provide `names`, each name appears as a subtitle on the title page and is appended to the filename (for example, `mi-historia-part-i-ano-1.pdf`).
- Even if a volume has **only one chapter** (such as `"4"` above), it keeps its table of contents and chapter heading.
- The numbers in `volumes` refer to the **chapter's position in the file** (`1` = first chapter), regardless of the number written in its heading.

#### Common `[split]` errors and how to fix them

When `enabled = true`, any error in `[split]` stops the program before generating any PDFs and explains exactly what to fix.

> *Note: console error messages are currently printed in Spanish. The exact Spanish text emitted by the program is shown below along with its English meaning.*

| Error | What went wrong | How to fix it |
|-------|-----------------|---------------|
| `input.dir: se encontraron N archivos .html` (*N .html files were found*) / `ningún archivo .html` (*no .html file found*) | There are 0 or more than 1 `.html` files in the input folder | Leave a single `.html` file in `input` (or set `enabled = false`) |
| `split.volumes: debe ser una lista de textos, no una sola cadena` (*must be a list of strings, not a single string*) | You wrote `volumes = "1-3, 4-5"` instead of a list | Use square brackets with quotes around each volume: `volumes = ["1-3", "4-5"]` |
| `formato inválido` (*invalid format*) / `el número de capítulo no puede ser 0` (*chapter number cannot be 0*) / `el rango está invertido` (*range is reversed*) | An entry contains letters, a `0`, or is reversed (e.g. `"5-3"`) | Use positive numbers only in `"N"` or `"N-M"` format with `N <= M`, e.g. `["1-3", "4", "5-8"]` |
| `hay un salto` (*there is a gap*) / `hay un solapamiento` (*there is an overlap*) / `no están en orden ascendente` (*not in ascending order*) / `debe empezar en el capítulo 1` (*must start at chapter 1*) | Chapters are missing between volumes, repeated, or out of order | Start at `1`, in ascending order, with no gaps or duplicates: `["1-3", "4-5", "6-7"]` |
| `split.names: tiene X elemento(s), pero split.volumes tiene Y` (*has X item(s), but split.volumes has Y*) / `está vacío` (*is empty*) | `names` doesn't match the length of `volumes` or contains an empty string | Provide one non-empty string per volume, or comment out/remove the `names` line |
| `el rango supera la cantidad de capítulos` (*range exceeds the number of chapters*) / `cobertura incompleta` (*incomplete coverage*) | The story has fewer or more chapters than the ranges cover | The message shows the actual chapter count; adjust the last range so it ends at that exact number |
| `la obra tiene un solo capítulo y no se puede dividir en tomos` (*the work has only one chapter and cannot be split into volumes*) | The file only has one chapter | Set `enabled = false` in `[split]` to generate it as a single book |

### Formats

| `format` | Book page size | Best for |
|----------|----------------|----------|
| `"a4"` | 210 × 297 mm | Large book, standard sheet |
| `"a5"` | 148 × 210 mm | Paperback / pocket book (half of A4) |
| `"a6"` | 105 × 148 mm | Small pocket book (quarter of A4 / half of A5), great for short stories |
| `"letter"` | 8.5 × 11 inches | US Letter paper |
| `"booklet"` | Half of the sheet chosen in `sheet` (`a4`, `a5`, or `letter`) | Printing on loose sheets and folding them into a booklet (see below) |

### Short books (few pages)

If a story turns out too thin to bind comfortably (for instance, around 40 pages in A5), you have three simple ways to give it more bulk:

- **Increase font size and line height in A5:** because `font_size` scales the whole book proportionally (headings, header, footer, and spacing), the layout stays balanced:
  ```toml
  [book]
  format = "a5"
  font_size = "12pt"
  line_height = 1.6
  ```
- **Switch to A6 with the default font size:** the page is smaller (105 × 148 mm) and margins scale down proportionally, so the same story takes noticeably more pages:
  ```toml
  [book]
  format = "a6"
  font_size = "11pt"
  line_height = 1.45
  ```
- **Make a booklet on A5 sheets:** produces A6-sized pages imposed two-up on landscape A5 sheets:
  ```toml
  [book]
  format = "booklet"

  [booklet]
  sheet = "a5"
  ```

---

## How to print

**A4, A5, A6, and Letter**
- Open the PDF, go to Print, and set scaling to **"Actual size"** or **100%** (not "Fit to page").
- If you choose `a5` or `a6`, ideally print on paper of that size (or cut A4 sheets in half for A5 / into quarters for A6). Otherwise, your printer may offer a multiple-pages-per-sheet option, though it's worth doing a test print first.
- To save paper, print **double-sided**, flipping on the **long edge**, just like a regular book.

**Booklet (`booklet`)**
1. In `config.toml`, set `format = "booklet"` and set `sheet` to the paper size you're using (`"a4"`, `"a5"`, or `"letter"`).
2. Run the program. The console tells you how many sheets you'll need.
3. Print the PDF at **actual size**, **double-sided**, set to **"flip on short edge"**.
4. Keep the printed sheets in the exact order they came out, **fold them in half**, and staple or sew along the crease.
- **If you use `sheet = "a5"`:** the physical print sheet is A5 (210 × 148 mm landscape). If you only have A4 paper, you can cut the sheets in half before printing (one A4 sheet cut in half yields two landscape A5 sheets) or print at actual size onto A4 and trim afterward, depending on what your printer handles best.
Blank pages are automatically added at the end so the total page count is a multiple of 4.

#### Thick books: signature mode (`signatures`)

When a book has many pages, folding all the sheets together into a single booklet becomes awkward or impossible. Traditional bookbinding solves this by dividing the book into several **signatures**: small stacks of sheets (e.g., 8 to 50 physical sheets depending on paper weight) that are folded and sewn or glued individually, then bound together in order to form the spine.

To enable it, add these options under `[booklet]` in `config.toml`:

```toml
[book]
format = "booklet"

[booklet]
sheet = "a4"
signatures = true
sheets_per_signature = 50     # physical sheets per signature (1 folded sheet = 4 pages)
balance = false               # false: full signatures + remainder at the end; true: distribute evenly
```

- **Units:** `sheets_per_signature` is measured in **physical sheets** (the sheets coming out of your printer). Each folded sheet holds **4 book pages** (2 per side), so 50 sheets equal 200 book pages (100 PDF faces).
- **`balance = false` (default):** creates full signatures of `sheets_per_signature` sheets and puts whatever is left in the last signature. For example, a 230-page book at 50 sheets per signature produces **2 signatures: 50 + 8 sheets** (any blank padding pages always go at the very end of the book).
- **`balance = true`:** distributes the total sheets as evenly as possible across the same number of signatures (never exceeding `sheets_per_signature`, with at most a 1-sheet difference between them). With the same 230-page example and a limit of 50, you get **2 signatures of 29 + 29 sheets**.
- **With volumes or multiple stories:** signatures are calculated per generated PDF (if you split a story with `[split]`, each volume gets its own signatures; if `combine = true`, they are calculated across the full combined book). If the book fits in a single signature, the output is identical to regular booklet mode.
- If you leave `signatures = true` while choosing a `format` other than `"booklet"`, it won't fail: it prints a warning and continues normally with the chosen format.

**How to print and assemble with signatures:**
1. Run the program. Everything is written to **a single PDF**, with the signatures one after another, and the console tells you how many sheets each signature has and where to split the stack.
2. Print the entire PDF at **actual size**, **double-sided**, with **"flip on short edge"**.
3. Without shuffling the printed stack, **separate the sheets** into the group sizes shown by the program (for example, every 50 sheets, or the exact groups if you used `balance = true`).
4. **Fold each group in half** and **sew or glue each signature along its crease**.
5. **Join the signatures in order** (signature 1 first, then 2, etc.) to assemble the finished book.

If you'd also like to split a very long story into separate physical books (each with its own title page and table of contents), you can combine this with `combine = false` or the `[split]` section (`split_long_works = true` or `enabled = true`).

---

## Troubleshooting

> *Note: console messages are currently printed in Spanish. Exact messages are quoted below alongside their English translation.*

**"No se pudo importar WeasyPrint"** (*"Could not import WeasyPrint"*) **or `cannot load library`**
Pango is missing or the program can't find it. Repeat Step 2. On Windows, if you installed MSYS2 in a non-default folder, check the official help: [WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

**"No existe la carpeta de entrada"** (*"Input folder does not exist"*) **or "No se encontraron obras válidas"** (*"No valid works found"*)
Check that the `input` folder exists and contains `.html` files downloaded from AO3.

**A file shows up with `[aviso]`** (*`[warning]`*) **and is left out of the book**
It doesn't look like an AO3 HTML download (for example, it's corrupted or in another format). The rest of the book is still generated normally.

**"Error de configuración"** (*"Configuration error"*) **or `[error] split...` messages**
There's a mistyped value in `config.toml` or an issue with your `[split]` ranges. The message tells you exactly what to fix and shows a valid example. Check the common `[split]` errors table above, make sure quotes are balanced, and verify that `true`/`false` are lowercase.

**The font doesn't look as expected**
The font you listed in `font_family` isn't installed on your computer, so the program fell back to the next one in the list. Try another font or install the one you want.

**The book has blank pages**
This is expected when `start_on_recto = true`: blank pages are inserted so every story starts on a right-hand page. Set it to `false` to avoid them.

---

## What it doesn't do (for now)

- Doesn't include images, chapter notes, or AO3 end notes.
- Doesn't generate an overall cover page or a master table of contents across all stories.
- Margins can't be customized from `config.toml`; they depend on the chosen format.
- Hyphenation at line endings is configured for English text.
- Doesn't output EPUB or other formats—only PDF.

---

## For anyone who wants to look at the code

```
ao3-book/
├── run.py              # launcher
├── config.toml         # configuration
├── requirements.txt    # Python packages
├── input/              # place .html files here
├── output/             # generated PDFs go here
├── src/ao3book/
│   ├── parser.py       # reads AO3 HTML
│   ├── split.py        # splits long stories into parts
│   ├── build.py        # builds the book
│   ├── render.py       # converts it to PDF
│   ├── booklet.py      # reorders pages for booklet mode
│   ├── config.py       # reads config.toml
│   ├── templates/      # book HTML structure
│   └── styles/         # book appearance (CSS)
└── tests/              # automated tests
```

To run the tests: `venv\Scripts\python -m pytest` (Windows) or `venv/bin/python -m pytest` (Mac and Linux).
