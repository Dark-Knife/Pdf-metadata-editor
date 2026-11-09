# PDF Metadata Editor

A small Python tool with a graphical interface to **read and edit the metadata of a PDF file**: title, author, subject, keywords, creation and modification dates, custom fields, file name, and more. Inspired by the "Document Properties" window of PDF Explorer (RTT Software).

## Features

- Read and edit the standard fields: **Title, Author, Subject, Keywords, Creator, Producer**
- Edit the **creation and modification dates** (automatically converted to the internal PDF format `D:YYYYMMDDHHmmSS+HH'mm'`)
- **Custom fields**: add, edit, delete
- **Rename the file** when saving
- Change the **file system dates** (creation and modification; creation date on Windows only)
- Read-only information: page count, PDF version, encryption, linearization, XMP presence, size
- Optional **XMP synchronization** so that other PDF readers display the same values
- **Save as…** to work on a copy without touching the original
- Console mode to print the metadata (`--show`)
- **Bilingual interface**: English (default) or French, switchable in the app or with `--lang`

## Installation

Requirements: Python 3.8 or newer (Tkinter is included with the official Python installer on Windows).

```bash
git clone https://github.com/Dark-Knife/pdf-metadata-editor.git
cd pdf-metadata-editor
pip install pikepdf
```

## Usage

Graphical interface:

```bash
python pdf_metadata_editor.py
```

Open a file directly:

```bash
python pdf_metadata_editor.py document.pdf
```

Print the metadata in the console, without the interface:

```bash
python pdf_metadata_editor.py document.pdf --show
```

### Language

The interface is in English by default. You can switch language at any time with the drop-down menu at the top right of the window, or choose it at startup:

```bash
python pdf_metadata_editor.py --lang fr
python pdf_metadata_editor.py document.pdf --show --lang fr
```

To change the default language permanently, edit `DEFAULT_LANG` at the top of `pdf_metadata_editor.py` (`"en"` or `"fr"`). Adding another language only requires a new entry in the `STRINGS` dictionary.

### Accepted date formats

| Input | Example |
|---|---|
| `YYYY-MM-DD HH:MM:SS` | `2026-11-08 10:00:00` |
| `YYYY-MM-DD HH:MM` or `YYYY-MM-DD` | `2026-11-08` |
| `DD/MM/YYYY HH:MM` or `DD/MM/YYYY` | `08/11/2026 10:00` |
| Raw PDF date | `D:20261108100000+01'00'` |
| Current date | `now` or `maintenant` |

A field left empty is **removed** from the PDF.

## Limitations

- Password-protected PDFs are not supported.
- Custom fields exist only in the PDF Info dictionary, not in XMP.
- Saving rewrites the file: its modification date in the file system changes, unless the option to keep it is checked.
- Changing the file creation date is only possible on Windows.

## Dependencies

- [pikepdf](https://github.com/pikepdf/pikepdf): reading and writing PDFs (based on QPDF)
- Tkinter: graphical interface (Python standard library)

## License

MIT
