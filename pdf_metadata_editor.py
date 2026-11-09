#!/usr/bin/env python3
"""
PDF Metadata Editor — read and edit the metadata of a PDF file
(simplified equivalent of the "Document Properties" window of PDF Explorer).

Features:
  - Standard fields: Title, Author, Subject, Keywords, Creator, Producer
  - Creation / modification dates (PDF format "D:YYYYMMDDHHmmSS+HH'mm'")
  - Custom fields (add / edit / delete)
  - File renaming
  - File system dates (creation / modification) — creation date: Windows only
  - Read-only information: pages, PDF version, encryption, size, XMP
  - Optional synchronization of XMP metadata with the Info dictionary
  - Interface language: English (default) or French

Installation:
    pip install pikepdf

Usage:
    python pdf_metadata_editor.py                         # graphical interface (English)
    python pdf_metadata_editor.py --lang fr               # graphical interface (French)
    python pdf_metadata_editor.py file.pdf --show         # print metadata in the console
    python pdf_metadata_editor.py file.pdf --show --lang fr
"""

import os
import re
import sys
import ctypes
import shutil
import tempfile
import argparse
import warnings
from datetime import datetime, timedelta, timezone

import pikepdf

# Custom fields have no XMP equivalent: harmless warning
warnings.filterwarnings("ignore", message=".*has no XMP equivalent.*")

# --------------------------------------------------------------------------- #
#  Internationalization
# --------------------------------------------------------------------------- #
DEFAULT_LANG = "en"          # change to "fr" to make French the default
LANG = DEFAULT_LANG
LANG_NAMES = {"en": "English", "fr": "Français"}

STRINGS = {
    "en": {
        "sep": ": ",
        "app_title": "PDF Metadata Editor",
        "open": "Open a PDF…",
        "language": "Language",
        "doc_props": "Document properties",
        "file_name": "File name",
        "f_title": "Title",
        "f_author": "Author",
        "f_subject": "Subject",
        "f_keywords": "Keywords",
        "f_creator": "Creator (application)",
        "f_producer": "Producer (PDF)",
        "f_created": "Creation date",
        "f_modified": "Modification date",
        "now": "Now",
        "date_hint": "Dates: YYYY-MM-DD HH:MM:SS, DD/MM/YYYY HH:MM, 'now', or "
                     "'D:YYYYMMDDHHmmSS+HH'mm''. Empty field = removed.",
        "custom_fields": "Custom fields",
        "col_name": "Name",
        "col_value": "Value",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "info_box": "Information (read-only)",
        "fs_box": "File dates (system)",
        "apply_fs": "Apply these dates to the file",
        "fs_created": "Creation",
        "fs_modified": "Modification",
        "keep_fs": "Keep the file's original modification date if I don't apply these dates",
        "sync_xmp": "Synchronize XMP metadata",
        "save": "Save",
        "save_as": "Save as…",
        "reload": "Reload",
        "custom_title": "Custom field",
        "ok": "OK",
        "err": "Error",
        "err_name": "Invalid name (must not be empty or contain spaces).",
        "err_reserved": "This field is already among the standard properties.",
        "err_exists": "This field already exists.",
        "err_open": "Could not open the PDF:\n{}",
        "err_filename": "Invalid file name.",
        "err_date_fmt": "Unrecognized date format: {}",
        "err_pdf_date": "Invalid PDF date: {}",
        "no_file_title": "No file",
        "no_file": "Open a PDF first.",
        "exists_title": "File exists",
        "exists_q": "{} already exists. Replace it?",
        "saved": "Metadata saved.",
        "xmp_warn": "XMP warning: {}",
        "x_pages": "Pages",
        "x_version": "PDF version",
        "x_encrypted": "Encrypted",
        "x_linearized": "Linearized (Fast Web View)",
        "x_xmp": "XMP present",
        "x_size": "Size",
        "yes": "yes",
        "no": "no",
        "size_fmt": "{} bytes",
        "custom_suffix": "(custom)",
        "file_label": "File",
        "unreadable": "<unreadable value>",
        "cli_show_needs_pdf": "--show requires a PDF file",
        "cli_desc": "Read / edit PDF metadata",
        "cli_pdf": "PDF file to open",
        "cli_show": "Print the metadata in the console",
        "cli_lang": "Interface language (default: {})",
    },
    "fr": {
        "sep": " : ",
        "app_title": "Éditeur de métadonnées PDF",
        "open": "Ouvrir un PDF…",
        "language": "Langue",
        "doc_props": "Propriétés du document",
        "file_name": "Nom du fichier",
        "f_title": "Titre",
        "f_author": "Auteur",
        "f_subject": "Sujet",
        "f_keywords": "Mots-clés",
        "f_creator": "Créateur (application)",
        "f_producer": "Producteur (PDF)",
        "f_created": "Date de création",
        "f_modified": "Date de modification",
        "now": "Maintenant",
        "date_hint": "Dates : AAAA-MM-JJ HH:MM:SS, JJ/MM/AAAA HH:MM, 'now', ou "
                     "'D:AAAAMMJJHHMMSS+HH'mm''. Champ vide = supprimé.",
        "custom_fields": "Champs personnalisés",
        "col_name": "Nom",
        "col_value": "Valeur",
        "add": "Ajouter",
        "edit": "Modifier",
        "delete": "Supprimer",
        "info_box": "Informations (lecture seule)",
        "fs_box": "Dates du fichier (système)",
        "apply_fs": "Appliquer ces dates au fichier",
        "fs_created": "Création",
        "fs_modified": "Modification",
        "keep_fs": "Conserver la date de modification d'origine du fichier "
                   "si je n'applique pas ces dates",
        "sync_xmp": "Synchroniser les métadonnées XMP",
        "save": "Enregistrer",
        "save_as": "Enregistrer sous…",
        "reload": "Recharger",
        "custom_title": "Champ personnalisé",
        "ok": "OK",
        "err": "Erreur",
        "err_name": "Nom invalide (non vide, sans espace).",
        "err_reserved": "Ce champ est déjà dans les propriétés standards.",
        "err_exists": "Ce champ existe déjà.",
        "err_open": "Impossible d'ouvrir le PDF :\n{}",
        "err_filename": "Nom de fichier invalide.",
        "err_date_fmt": "Format de date non reconnu : {}",
        "err_pdf_date": "Date PDF invalide : {}",
        "no_file_title": "Aucun fichier",
        "no_file": "Ouvrez d'abord un PDF.",
        "exists_title": "Fichier existant",
        "exists_q": "{} existe déjà. Remplacer ?",
        "saved": "Métadonnées enregistrées.",
        "xmp_warn": "Avertissement XMP : {}",
        "x_pages": "Pages",
        "x_version": "Version PDF",
        "x_encrypted": "Chiffré",
        "x_linearized": "Linéarisé (Fast Web View)",
        "x_xmp": "XMP présent",
        "x_size": "Taille",
        "yes": "oui",
        "no": "non",
        "size_fmt": "{} octets",
        "custom_suffix": "(perso)",
        "file_label": "Fichier",
        "unreadable": "<valeur non lisible>",
        "cli_show_needs_pdf": "--show nécessite un fichier PDF",
        "cli_desc": "Lecture / modification des métadonnées PDF",
        "cli_pdf": "Fichier PDF à ouvrir",
        "cli_show": "Afficher les métadonnées en console",
        "cli_lang": "Langue de l'interface (défaut : {})",
    },
}


def set_lang(code):
    global LANG
    LANG = code if code in STRINGS else DEFAULT_LANG


def t(key, *args):
    """Translate `key` into the current language (falls back to English)."""
    s = STRINGS.get(LANG, {}).get(key) or STRINGS["en"].get(key, key)
    return s.format(*args) if args else s


STANDARD_FIELDS = [
    ("/Title", "f_title"),
    ("/Author", "f_author"),
    ("/Subject", "f_subject"),
    ("/Keywords", "f_keywords"),
    ("/Creator", "f_creator"),
    ("/Producer", "f_producer"),
]
DATE_FIELDS = [
    ("/CreationDate", "f_created"),
    ("/ModDate", "f_modified"),
]
RESERVED = {k for k, _ in STANDARD_FIELDS} | {k for k, _ in DATE_FIELDS}

# --------------------------------------------------------------------------- #
#  PDF dates
# --------------------------------------------------------------------------- #
_PDF_DATE_RE = re.compile(
    r"^D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?"
    r"(?:(Z|[+\-])(?:(\d{2})'?(?:(\d{2})'?)?)?)?$"
)


def parse_pdf_date(s):
    """Convert 'D:20261108120000+01'00'' to an aware datetime. None if invalid."""
    if not s:
        return None
    m = _PDF_DATE_RE.match(str(s).strip())
    if not m:
        return None
    y, mo, d, h, mi, se, sign, oh, om = m.groups()
    try:
        tz = timezone.utc
        if sign in ("+", "-"):
            delta = timedelta(hours=int(oh or 0), minutes=int(om or 0))
            tz = timezone(delta if sign == "+" else -delta)
        return datetime(int(y), int(mo or 1), int(d or 1),
                        int(h or 0), int(mi or 0), int(se or 0), tzinfo=tz)
    except ValueError:
        return None


def format_pdf_date(dt):
    """datetime -> PDF date string."""
    if dt.tzinfo is None:
        dt = dt.astimezone()  # assume local time
    off = dt.utcoffset()
    total = int(off.total_seconds()) if off else 0
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return "D:{:%Y%m%d%H%M%S}{}{:02d}'{:02d}'".format(
        dt, sign, total // 3600, (total % 3600) // 60)


def human_date(pdf_date):
    """PDF date string -> readable 'YYYY-MM-DD HH:MM:SS' (time as stored in the PDF)."""
    dt = parse_pdf_date(pdf_date)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else (pdf_date or "")


def parse_user_date(text):
    """Accepts 'YYYY-MM-DD HH:MM:SS', 'DD/MM/YYYY HH:MM', 'D:...', 'now' or 'maintenant'."""
    s = text.strip()
    if not s:
        return ""
    if s.lower() in ("now", "maintenant"):
        return format_pdf_date(datetime.now().astimezone())
    if s.startswith("D:"):
        if parse_pdf_date(s):
            return s
        raise ValueError(t("err_pdf_date", s))
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return format_pdf_date(datetime.strptime(s, fmt).astimezone())
        except ValueError:
            pass
    raise ValueError(t("err_date_fmt", s))


# --------------------------------------------------------------------------- #
#  Reading / writing
# --------------------------------------------------------------------------- #
def read_info(path):
    """Return (info dict, extras dict). Extras use raw values; see extras_lines()."""
    with pikepdf.open(path) as pdf:
        info = {}
        if pdf.trailer.get("/Info") is not None:
            for k, v in pdf.docinfo.items():
                try:
                    info[str(k)] = str(v)
                except Exception:
                    info[str(k)] = t("unreadable")
        xmp_present = False
        try:
            xmp_present = pdf.Root.get("/Metadata") is not None
        except Exception:
            pass
        extras = {
            "pages": len(pdf.pages),
            "version": pdf.pdf_version,
            "encrypted": bool(pdf.is_encrypted),
            "linearized": bool(pdf.is_linearized),
            "xmp": xmp_present,
            "size": os.path.getsize(path),
        }
    return info, extras


def extras_lines(extras):
    """Translate the read-only extras into a list of (label, value) strings."""
    def yn(b):
        return t("yes") if b else t("no")

    size = "{:,}".format(extras["size"])
    if LANG == "fr":
        size = size.replace(",", " ")
    return [
        (t("x_pages"), str(extras["pages"])),
        (t("x_version"), str(extras["version"])),
        (t("x_encrypted"), yn(extras["encrypted"])),
        (t("x_linearized"), yn(extras["linearized"])),
        (t("x_xmp"), yn(extras["xmp"])),
        (t("x_size"), t("size_fmt", size)),
    ]


def write_info(path, info, sync_xmp=False, output=None):
    """
    Write the Info dictionary. `info`: {'/Key': 'value'}; empty value => field removed.
    Rewrites the file (in place if `output` is None) through a temporary file.
    """
    output = output or path
    fd, tmp = tempfile.mkstemp(suffix=".pdf", dir=os.path.dirname(os.path.abspath(output)))
    os.close(fd)
    try:
        with pikepdf.open(path) as pdf:
            for key, value in info.items():
                if value == "" or value is None:
                    if key in pdf.docinfo:
                        del pdf.docinfo[key]
                else:
                    pdf.docinfo[key] = pikepdf.String(value)
            if sync_xmp:
                try:
                    with pdf.open_metadata(set_pikepdf_as_editor=False,
                                           update_docinfo=False) as meta:
                        meta.load_from_docinfo(pdf.docinfo, delete_missing=True,
                                               raise_failure=False)
                except Exception as e:
                    print(t("xmp_warn", e), file=sys.stderr)
            pdf.save(tmp)
        shutil.move(tmp, output)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def get_fs_times(path):
    st = os.stat(path)
    return (datetime.fromtimestamp(st.st_ctime), datetime.fromtimestamp(st.st_mtime))


def set_fs_times(path, created=None, modified=None):
    """Change file system dates. The creation date is only handled on Windows."""
    if modified is not None:
        ts = modified.timestamp()
        os.utime(path, (ts, ts))
    if created is not None and os.name == "nt":
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.HANDLE]
        handle = k32.CreateFileW(path, 0x100, 0, None, 3, 0x80, None)  # FILE_WRITE_ATTRIBUTES
        if handle == wintypes.HANDLE(-1).value:
            raise OSError("Cannot open the file to change its creation date")
        try:
            ticks = int((created.timestamp() + 11644473600) * 10_000_000)
            ft = wintypes.FILETIME(ticks & 0xFFFFFFFF, ticks >> 32)
            if not k32.SetFileTime(handle, ctypes.byref(ft), None, None):
                raise OSError("SetFileTime failed")
        finally:
            k32.CloseHandle(handle)


def parse_fs_date(text):
    s = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(t("err_date_fmt", s))


# --------------------------------------------------------------------------- #
#  Console mode
# --------------------------------------------------------------------------- #
def show_console(path):
    info, extras = read_info(path)
    print("{}{}{}".format(t("file_label"), t("sep"), path))
    print("-" * 60)
    for k, key in STANDARD_FIELDS:
        print("{:<28} {}".format(t(key), info.get(k, "")))
    for k, key in DATE_FIELDS:
        print("{:<28} {}".format(t(key), human_date(info.get(k, ""))))
    for k, v in info.items():
        if k not in RESERVED:
            print("{:<28} {}".format(k.lstrip("/") + " " + t("custom_suffix"), v))
    print("-" * 60)
    for label, value in extras_lines(extras):
        print("{:<28} {}".format(label, value))


# --------------------------------------------------------------------------- #
#  Graphical interface
# --------------------------------------------------------------------------- #
def run_gui(initial=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.geometry("760x740")

    state = {"path": None, "orig_info": {}, "extras": None}
    entries = {}          # PDF key -> StringVar
    sv_filename = tk.StringVar()
    sv_fs_created = tk.StringVar()
    sv_fs_modified = tk.StringVar()
    sv_path = tk.StringVar()
    sv_lang = tk.StringVar(value=LANG_NAMES[LANG])
    sync_xmp = tk.BooleanVar(value=True)
    apply_fs = tk.BooleanVar(value=False)
    keep_fs_mtime = tk.BooleanVar(value=False)

    # Registry of translatable widgets: (widget, option, i18n key)
    reg = []

    def R(widget, key, opt="text"):
        widget.config(**{opt: t(key)})
        reg.append((widget, opt, key))
        return widget

    # --- top bar
    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")
    R(ttk.Button(top, command=lambda: choose()), "open").pack(side="left")
    ttk.Label(top, textvariable=sv_path, foreground="#555").pack(side="left", padx=8)
    lang_box = ttk.Combobox(top, textvariable=sv_lang, state="readonly", width=10,
                            values=list(LANG_NAMES.values()))
    lang_box.pack(side="right")
    R(ttk.Label(top), "language").pack(side="right", padx=6)

    # --- standard fields
    box = R(ttk.LabelFrame(root, padding=8), "doc_props")
    box.pack(fill="x", padx=8, pady=4)
    box.columnconfigure(1, weight=1)

    r = 0
    R(ttk.Label(box), "file_name").grid(row=r, column=0, sticky="w", pady=2)
    ttk.Entry(box, textvariable=sv_filename).grid(row=r, column=1, sticky="ew", pady=2)
    r += 1
    for key, label_key in STANDARD_FIELDS:
        entries[key] = tk.StringVar()
        R(ttk.Label(box), label_key).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=entries[key]).grid(row=r, column=1, sticky="ew", pady=2)
        r += 1
    for key, label_key in DATE_FIELDS:
        entries[key] = tk.StringVar()
        R(ttk.Label(box), label_key).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=entries[key]).grid(row=r, column=1, sticky="ew", pady=2)
        R(ttk.Button(box, width=12,
                     command=lambda k=key: entries[k].set(
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
          "now").grid(row=r, column=2, padx=4)
        r += 1
    R(ttk.Label(box, foreground="#777", wraplength=700, justify="left"),
      "date_hint").grid(row=r, column=0, columnspan=3, sticky="w")

    # --- custom fields
    cbox = R(ttk.LabelFrame(root, padding=8), "custom_fields")
    cbox.pack(fill="both", expand=True, padx=8, pady=4)
    tree = ttk.Treeview(cbox, columns=("k", "v"), show="headings", height=5)
    tree.column("k", width=180)
    tree.column("v", width=480)
    tree.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(cbox, orient="vertical", command=tree.yview)
    sb.pack(side="left", fill="y")
    tree.configure(yscrollcommand=sb.set)
    cbtn = ttk.Frame(cbox)
    cbtn.pack(side="left", padx=6, anchor="n")

    def edit_custom(existing=None):
        win = tk.Toplevel(root)
        win.title(t("custom_title"))
        win.transient(root)
        win.grab_set()
        k = tk.StringVar(value=existing[0] if existing else "")
        v = tk.StringVar(value=existing[1] if existing else "")
        ttk.Label(win, text=t("col_name")).grid(row=0, column=0, padx=6, pady=4, sticky="w")
        ke = ttk.Entry(win, textvariable=k, width=40)
        ke.grid(row=0, column=1, padx=6, pady=4)
        if existing:
            ke.state(["disabled"])
        ttk.Label(win, text=t("col_value")).grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ttk.Entry(win, textvariable=v, width=40).grid(row=1, column=1, padx=6, pady=4)

        def ok():
            name = k.get().strip().lstrip("/")
            if not name or " " in name:
                messagebox.showerror(t("err"), t("err_name"), parent=win)
                return
            if "/" + name in RESERVED:
                messagebox.showerror(t("err"), t("err_reserved"), parent=win)
                return
            if not existing:
                for iid in tree.get_children():
                    if tree.item(iid, "values")[0] == name:
                        messagebox.showerror(t("err"), t("err_exists"), parent=win)
                        return
            if existing:
                for iid in tree.get_children():
                    if tree.item(iid, "values")[0] == existing[0]:
                        tree.item(iid, values=(name, v.get()))
            else:
                tree.insert("", "end", values=(name, v.get()))
            win.destroy()

        ttk.Button(win, text=t("ok"), command=ok).grid(row=2, column=1, sticky="e",
                                                        padx=6, pady=6)

    def add_custom():
        edit_custom()

    def mod_custom():
        sel = tree.selection()
        if sel:
            edit_custom(tree.item(sel[0], "values"))

    def del_custom():
        for iid in tree.selection():
            tree.delete(iid)

    R(ttk.Button(cbtn, command=add_custom), "add").pack(fill="x", pady=2)
    R(ttk.Button(cbtn, command=mod_custom), "edit").pack(fill="x", pady=2)
    R(ttk.Button(cbtn, command=del_custom), "delete").pack(fill="x", pady=2)
    tree.bind("<Double-1>", lambda e: mod_custom())

    # --- read-only info
    ibox = R(ttk.LabelFrame(root, padding=8), "info_box")
    ibox.pack(fill="x", padx=8, pady=4)
    info_label = ttk.Label(ibox, text="—", justify="left")
    info_label.pack(anchor="w")

    # --- file system dates
    fbox = R(ttk.LabelFrame(root, padding=8), "fs_box")
    fbox.pack(fill="x", padx=8, pady=4)
    fbox.columnconfigure(1, weight=1)
    R(ttk.Checkbutton(fbox, variable=apply_fs), "apply_fs").grid(
        row=0, column=0, columnspan=2, sticky="w")
    R(ttk.Label(fbox), "fs_created").grid(row=1, column=0, sticky="w")
    ttk.Entry(fbox, textvariable=sv_fs_created).grid(row=1, column=1, sticky="ew", pady=2)
    R(ttk.Label(fbox), "fs_modified").grid(row=2, column=0, sticky="w")
    ttk.Entry(fbox, textvariable=sv_fs_modified).grid(row=2, column=1, sticky="ew", pady=2)
    R(ttk.Checkbutton(fbox, variable=keep_fs_mtime), "keep_fs").grid(
        row=3, column=0, columnspan=2, sticky="w")

    # --- options + buttons
    bot = ttk.Frame(root, padding=8)
    bot.pack(fill="x")
    R(ttk.Checkbutton(bot, variable=sync_xmp), "sync_xmp").pack(side="left")
    R(ttk.Button(bot, command=lambda: save()), "save").pack(side="right")
    R(ttk.Button(bot, command=lambda: save(as_new=True)), "save_as").pack(side="right", padx=6)
    R(ttk.Button(bot, command=lambda: load(state["path"])), "reload").pack(side="right")

    # --- language handling
    def render_info():
        if state["extras"]:
            info_label.config(text="\n".join(
                "{}{}{}".format(k, t("sep"), v) for k, v in extras_lines(state["extras"])))

    def refresh_texts():
        root.title(t("app_title"))
        for widget, opt, key in reg:
            widget.config(**{opt: t(key)})
        tree.heading("k", text=t("col_name"))
        tree.heading("v", text=t("col_value"))
        render_info()

    def on_lang_change(_event=None):
        for code, name in LANG_NAMES.items():
            if name == sv_lang.get():
                set_lang(code)
                break
        refresh_texts()

    lang_box.bind("<<ComboboxSelected>>", on_lang_change)

    # --- logic
    def load(path):
        if not path:
            return
        try:
            info, extras = read_info(path)
        except Exception as e:
            messagebox.showerror(t("err"), t("err_open", e))
            return
        state["path"] = path
        state["orig_info"] = info
        state["extras"] = extras
        sv_path.set(path)
        sv_filename.set(os.path.basename(path))
        for k, _ in STANDARD_FIELDS:
            entries[k].set(info.get(k, ""))
        for k, _ in DATE_FIELDS:
            entries[k].set(human_date(info.get(k, "")))
        tree.delete(*tree.get_children())
        for k, v in info.items():
            if k not in RESERVED:
                tree.insert("", "end", values=(k.lstrip("/"), v))
        render_info()
        c, m = get_fs_times(path)
        sv_fs_created.set(c.strftime("%Y-%m-%d %H:%M:%S"))
        sv_fs_modified.set(m.strftime("%Y-%m-%d %H:%M:%S"))
        apply_fs.set(False)

    def choose():
        p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("*", "*.*")])
        if p:
            load(p)

    def save(as_new=False):
        path = state["path"]
        if not path:
            messagebox.showwarning(t("no_file_title"), t("no_file"))
            return
        try:
            new_info = {}
            for k, _ in STANDARD_FIELDS:
                new_info[k] = entries[k].get()
            for k, _ in DATE_FIELDS:
                new_info[k] = parse_user_date(entries[k].get())
            # custom fields: remove those that disappeared from the list
            current_custom = {}
            for iid in tree.get_children():
                n, v = tree.item(iid, "values")
                current_custom["/" + n] = v
            for k in state["orig_info"]:
                if k not in RESERVED and k not in current_custom:
                    new_info[k] = ""
            new_info.update(current_custom)

            fs_c = fs_m = None
            if apply_fs.get():
                fs_c = parse_fs_date(sv_fs_created.get())
                fs_m = parse_fs_date(sv_fs_modified.get())

            # destination
            new_name = sv_filename.get().strip()
            if not new_name.lower().endswith(".pdf"):
                new_name += ".pdf"
            if any(c in new_name for c in '<>:"/\\|?*'):
                raise ValueError(t("err_filename"))
            folder = os.path.dirname(path)
            dest = os.path.join(folder, new_name)
            if as_new:
                dest = filedialog.asksaveasfilename(
                    initialdir=folder, initialfile=new_name, defaultextension=".pdf",
                    filetypes=[("PDF", "*.pdf")])
                if not dest:
                    return
            elif os.path.normcase(dest) != os.path.normcase(path) and os.path.exists(dest):
                if not messagebox.askyesno(t("exists_title"), t("exists_q", new_name)):
                    return

            old_c, old_m = get_fs_times(path)
            write_info(path, new_info, sync_xmp=sync_xmp.get(), output=dest if as_new else None)
            target = dest if as_new else path
            if not as_new and os.path.normcase(dest) != os.path.normcase(path):
                os.replace(path, dest)
                target = dest

            if apply_fs.get():
                set_fs_times(target, created=fs_c, modified=fs_m)
            elif keep_fs_mtime.get():
                set_fs_times(target, created=old_c, modified=old_m)

            load(target)
            messagebox.showinfo(t("ok"), t("saved"))
        except Exception as e:
            messagebox.showerror(t("err"), str(e))

    refresh_texts()
    if initial:
        load(initial)
    root.mainloop()


# --------------------------------------------------------------------------- #
def main():
    # Pre-parse --lang so that the --help texts are also translated
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", choices=sorted(STRINGS), default=DEFAULT_LANG)
    known, _ = pre.parse_known_args()
    set_lang(known.lang)

    ap = argparse.ArgumentParser(description=t("cli_desc"))
    ap.add_argument("pdf", nargs="?", help=t("cli_pdf"))
    ap.add_argument("--show", action="store_true", help=t("cli_show"))
    ap.add_argument("--lang", choices=sorted(STRINGS), default=DEFAULT_LANG,
                    help=t("cli_lang", DEFAULT_LANG))
    a = ap.parse_args()
    set_lang(a.lang)
    if a.show:
        if not a.pdf:
            ap.error(t("cli_show_needs_pdf"))
        show_console(a.pdf)
    else:
        run_gui(a.pdf)


if __name__ == "__main__":
    main()
