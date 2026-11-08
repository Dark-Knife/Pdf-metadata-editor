#!/usr/bin/env python3
"""
PDF Metadata Editor — lecture et modification des métadonnées d'un PDF
(équivalent simplifié de la partie "Document Properties" de PDF Explorer).

Fonctions :
  - Champs standards : Titre, Auteur, Sujet, Mots-clés, Créateur, Producteur
  - Dates de création / modification (format PDF "D:YYYYMMDDHHmmSS+HH'mm'")
  - Champs personnalisés (ajout / modification / suppression)
  - Renommage du fichier
  - Dates du système de fichiers (création / modification) — création : Windows
  - Informations en lecture seule : pages, version PDF, chiffrement, taille, XMP
  - Synchronisation optionnelle des métadonnées XMP avec le dictionnaire Info

Installation :
    pip install pikepdf

Utilisation :
    python pdf_metadata_editor.py            # interface graphique
    python pdf_metadata_editor.py fichier.pdf --show   # affichage en console
"""

import os
import re
import sys
import ctypes
import shutil
import tempfile
import argparse
from datetime import datetime, timezone

import warnings
import pikepdf

# Les champs personnalisés n'ont pas d'équivalent XMP : avertissement sans importance
warnings.filterwarnings("ignore", message=".*has no XMP equivalent.*")

STANDARD_FIELDS = [
    ("/Title", "Titre"),
    ("/Author", "Auteur"),
    ("/Subject", "Sujet"),
    ("/Keywords", "Mots-clés"),
    ("/Creator", "Créateur (application)"),
    ("/Producer", "Producteur (PDF)"),
]
DATE_FIELDS = [
    ("/CreationDate", "Date de création"),
    ("/ModDate", "Date de modification"),
]
RESERVED = {k for k, _ in STANDARD_FIELDS} | {k for k, _ in DATE_FIELDS}

# --------------------------------------------------------------------------- #
#  Dates PDF
# --------------------------------------------------------------------------- #
_PDF_DATE_RE = re.compile(
    r"^D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?"
    r"(?:(Z|[+\-])(?:(\d{2})'?(?:(\d{2})'?)?)?)?$"
)


def parse_pdf_date(s):
    """Convertit 'D:20261108120000+01'00'' en datetime (aware). None si invalide."""
    if not s:
        return None
    m = _PDF_DATE_RE.match(str(s).strip())
    if not m:
        return None
    y, mo, d, h, mi, se, sign, oh, om = m.groups()
    try:
        from datetime import timedelta
        tz = timezone.utc
        if sign in ("+", "-"):
            delta = timedelta(hours=int(oh or 0), minutes=int(om or 0))
            tz = timezone(delta if sign == "+" else -delta)
        return datetime(int(y), int(mo or 1), int(d or 1),
                        int(h or 0), int(mi or 0), int(se or 0), tzinfo=tz)
    except ValueError:
        return None


def format_pdf_date(dt):
    """datetime -> chaîne de date PDF."""
    if dt.tzinfo is None:
        dt = dt.astimezone()  # suppose l'heure locale
    off = dt.utcoffset()
    total = int(off.total_seconds()) if off else 0
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return "D:{:%Y%m%d%H%M%S}{}{:02d}'{:02d}'".format(
        dt, sign, total // 3600, (total % 3600) // 60)


def human_date(pdf_date):
    """Chaîne de date PDF -> 'YYYY-MM-DD HH:MM:SS' lisible (heure du PDF)."""
    dt = parse_pdf_date(pdf_date)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else (pdf_date or "")


def parse_user_date(text):
    """Accepte 'YYYY-MM-DD HH:MM:SS', 'DD/MM/YYYY HH:MM', 'D:...' ou 'now'."""
    t = text.strip()
    if not t:
        return ""
    if t.lower() in ("now", "maintenant"):
        return format_pdf_date(datetime.now().astimezone())
    if t.startswith("D:"):
        if parse_pdf_date(t):
            return t
        raise ValueError("Date PDF invalide : " + t)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return format_pdf_date(datetime.strptime(t, fmt).astimezone())
        except ValueError:
            pass
    raise ValueError("Format de date non reconnu : " + t)


# --------------------------------------------------------------------------- #
#  Lecture / écriture
# --------------------------------------------------------------------------- #
def read_info(path):
    """Retourne (infos dict, extras dict)."""
    with pikepdf.open(path) as pdf:
        info = {}
        if pdf.trailer.get("/Info") is not None:
            for k, v in pdf.docinfo.items():
                try:
                    info[str(k)] = str(v)
                except Exception:
                    info[str(k)] = "<valeur non lisible>"
        xmp_present = False
        try:
            xmp_present = pdf.Root.get("/Metadata") is not None
        except Exception:
            pass
        extras = {
            "Pages": len(pdf.pages),
            "Version PDF": pdf.pdf_version,
            "Chiffré": "oui" if pdf.is_encrypted else "non",
            "Linéarisé (Fast Web View)": "oui" if pdf.is_linearized else "non",
            "XMP présent": "oui" if xmp_present else "non",
            "Taille": "{:,} octets".format(os.path.getsize(path)).replace(",", " "),
        }
    return info, extras


def write_info(path, info, sync_xmp=False, output=None):
    """
    Écrit le dictionnaire Info. `info` : {'/Clé': 'valeur'}; valeur vide => suppression.
    Réécrit le fichier (en place si output est None) via un fichier temporaire.
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
                    print("Avertissement XMP :", e, file=sys.stderr)
            pdf.save(tmp)
        shutil.move(tmp, output)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def get_fs_times(path):
    st = os.stat(path)
    return (datetime.fromtimestamp(st.st_ctime), datetime.fromtimestamp(st.st_mtime))


def set_fs_times(path, created=None, modified=None):
    """Modifie les dates du système de fichiers. La date de création n'est gérée que sous Windows."""
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
            raise OSError("Impossible d'ouvrir le fichier pour modifier sa date de création")
        try:
            ticks = int((created.timestamp() + 11644473600) * 10_000_000)
            ft = wintypes.FILETIME(ticks & 0xFFFFFFFF, ticks >> 32)
            if not k32.SetFileTime(handle, ctypes.byref(ft), None, None):
                raise OSError("SetFileTime a échoué")
        finally:
            k32.CloseHandle(handle)


def parse_fs_date(text):
    t = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            pass
    raise ValueError("Format de date non reconnu : " + t)


# --------------------------------------------------------------------------- #
#  Mode console
# --------------------------------------------------------------------------- #
def show_console(path):
    info, extras = read_info(path)
    print("Fichier :", path)
    print("-" * 60)
    for k, label in STANDARD_FIELDS:
        print("{:<28} {}".format(label, info.get(k, "")))
    for k, label in DATE_FIELDS:
        print("{:<28} {}".format(label, human_date(info.get(k, ""))))
    custom = {k: v for k, v in info.items() if k not in RESERVED}
    for k, v in custom.items():
        print("{:<28} {}".format(k.lstrip("/") + " (perso)", v))
    print("-" * 60)
    for k, v in extras.items():
        print("{:<28} {}".format(k, v))


# --------------------------------------------------------------------------- #
#  Interface graphique
# --------------------------------------------------------------------------- #
def run_gui(initial=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("Éditeur de métadonnées PDF")
    root.geometry("760x720")

    state = {"path": None, "orig_info": {}}
    entries = {}          # clé PDF -> StringVar
    sv_filename = tk.StringVar()
    sv_fs_created = tk.StringVar()
    sv_fs_modified = tk.StringVar()
    sv_path = tk.StringVar()
    sync_xmp = tk.BooleanVar(value=True)
    apply_fs = tk.BooleanVar(value=False)
    keep_fs_mtime = tk.BooleanVar(value=False)

    # --- barre du haut
    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")
    ttk.Button(top, text="Ouvrir un PDF…", command=lambda: choose()).pack(side="left")
    ttk.Label(top, textvariable=sv_path, foreground="#555").pack(side="left", padx=8)

    # --- champs standards
    box = ttk.LabelFrame(root, text="Propriétés du document", padding=8)
    box.pack(fill="x", padx=8, pady=4)
    box.columnconfigure(1, weight=1)

    r = 0
    ttk.Label(box, text="Nom du fichier").grid(row=r, column=0, sticky="w", pady=2)
    ttk.Entry(box, textvariable=sv_filename).grid(row=r, column=1, sticky="ew", pady=2)
    r += 1
    for key, label in STANDARD_FIELDS:
        entries[key] = tk.StringVar()
        ttk.Label(box, text=label).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=entries[key]).grid(row=r, column=1, sticky="ew", pady=2)
        r += 1
    for key, label in DATE_FIELDS:
        entries[key] = tk.StringVar()
        ttk.Label(box, text=label).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=entries[key]).grid(row=r, column=1, sticky="ew", pady=2)
        ttk.Button(box, text="Maintenant", width=12,
                   command=lambda k=key: entries[k].set(
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                   ).grid(row=r, column=2, padx=4)
        r += 1
    ttk.Label(box, foreground="#777",
              text="Dates : AAAA-MM-JJ HH:MM:SS, JJ/MM/AAAA HH:MM, 'now', ou 'D:AAAAMMJJHHMMSS+HH'mm''. "
                   "Champ vide = supprimé.").grid(row=r, column=0, columnspan=3, sticky="w")

    # --- champs personnalisés
    cbox = ttk.LabelFrame(root, text="Champs personnalisés", padding=8)
    cbox.pack(fill="both", expand=True, padx=8, pady=4)
    tree = ttk.Treeview(cbox, columns=("k", "v"), show="headings", height=5)
    tree.heading("k", text="Nom")
    tree.heading("v", text="Valeur")
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
        win.title("Champ personnalisé")
        win.transient(root)
        win.grab_set()
        k = tk.StringVar(value=existing[0] if existing else "")
        v = tk.StringVar(value=existing[1] if existing else "")
        ttk.Label(win, text="Nom").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        ke = ttk.Entry(win, textvariable=k, width=40)
        ke.grid(row=0, column=1, padx=6, pady=4)
        if existing:
            ke.state(["disabled"])
        ttk.Label(win, text="Valeur").grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ttk.Entry(win, textvariable=v, width=40).grid(row=1, column=1, padx=6, pady=4)

        def ok():
            name = k.get().strip().lstrip("/")
            if not name or " " in name:
                messagebox.showerror("Erreur", "Nom invalide (non vide, sans espace).", parent=win)
                return
            if "/" + name in RESERVED:
                messagebox.showerror("Erreur", "Ce champ est déjà dans les propriétés standards.", parent=win)
                return
            for iid in tree.get_children():
                if tree.item(iid, "values")[0] == name and not existing:
                    messagebox.showerror("Erreur", "Ce champ existe déjà.", parent=win)
                    return
            if existing:
                for iid in tree.get_children():
                    if tree.item(iid, "values")[0] == existing[0]:
                        tree.item(iid, values=(name, v.get()))
            else:
                tree.insert("", "end", values=(name, v.get()))
            win.destroy()

        ttk.Button(win, text="OK", command=ok).grid(row=2, column=1, sticky="e", padx=6, pady=6)

    def add_custom():
        edit_custom()

    def mod_custom():
        sel = tree.selection()
        if sel:
            edit_custom(tree.item(sel[0], "values"))

    def del_custom():
        for iid in tree.selection():
            tree.delete(iid)

    ttk.Button(cbtn, text="Ajouter", command=add_custom).pack(fill="x", pady=2)
    ttk.Button(cbtn, text="Modifier", command=mod_custom).pack(fill="x", pady=2)
    ttk.Button(cbtn, text="Supprimer", command=del_custom).pack(fill="x", pady=2)
    tree.bind("<Double-1>", lambda e: mod_custom())

    # --- infos lecture seule
    ibox = ttk.LabelFrame(root, text="Informations (lecture seule)", padding=8)
    ibox.pack(fill="x", padx=8, pady=4)
    info_label = ttk.Label(ibox, text="—", justify="left")
    info_label.pack(anchor="w")

    # --- système de fichiers
    fbox = ttk.LabelFrame(root, text="Dates du fichier (système)", padding=8)
    fbox.pack(fill="x", padx=8, pady=4)
    fbox.columnconfigure(1, weight=1)
    ttk.Checkbutton(fbox, text="Appliquer ces dates au fichier",
                    variable=apply_fs).grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(fbox, text="Création").grid(row=1, column=0, sticky="w")
    ttk.Entry(fbox, textvariable=sv_fs_created).grid(row=1, column=1, sticky="ew", pady=2)
    ttk.Label(fbox, text="Modification").grid(row=2, column=0, sticky="w")
    ttk.Entry(fbox, textvariable=sv_fs_modified).grid(row=2, column=1, sticky="ew", pady=2)
    ttk.Checkbutton(fbox, text="Conserver la date de modification d'origine du fichier si je n'applique pas ces dates",
                    variable=keep_fs_mtime).grid(row=3, column=0, columnspan=2, sticky="w")

    # --- options + boutons
    bot = ttk.Frame(root, padding=8)
    bot.pack(fill="x")
    ttk.Checkbutton(bot, text="Synchroniser les métadonnées XMP", variable=sync_xmp).pack(side="left")
    ttk.Button(bot, text="Enregistrer", command=lambda: save()).pack(side="right")
    ttk.Button(bot, text="Enregistrer sous…", command=lambda: save(as_new=True)).pack(side="right", padx=6)
    ttk.Button(bot, text="Recharger", command=lambda: load(state["path"])).pack(side="right")

    # --- logique
    def load(path):
        if not path:
            return
        try:
            info, extras = read_info(path)
        except Exception as e:
            messagebox.showerror("Erreur", "Impossible d'ouvrir le PDF :\n{}".format(e))
            return
        state["path"] = path
        state["orig_info"] = info
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
        info_label.config(text="\n".join("{} : {}".format(k, v) for k, v in extras.items()))
        c, m = get_fs_times(path)
        sv_fs_created.set(c.strftime("%Y-%m-%d %H:%M:%S"))
        sv_fs_modified.set(m.strftime("%Y-%m-%d %H:%M:%S"))
        apply_fs.set(False)

    def choose():
        p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")])
        if p:
            load(p)

    def save(as_new=False):
        path = state["path"]
        if not path:
            messagebox.showwarning("Aucun fichier", "Ouvrez d'abord un PDF.")
            return
        try:
            new_info = {}
            for k, _ in STANDARD_FIELDS:
                new_info[k] = entries[k].get()
            for k, _ in DATE_FIELDS:
                new_info[k] = parse_user_date(entries[k].get())
            # champs perso : supprime ceux qui ont disparu de la liste
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
                raise ValueError("Nom de fichier invalide.")
            folder = os.path.dirname(path)
            dest = os.path.join(folder, new_name)
            if as_new:
                dest = filedialog.asksaveasfilename(
                    initialdir=folder, initialfile=new_name, defaultextension=".pdf",
                    filetypes=[("PDF", "*.pdf")])
                if not dest:
                    return
            elif os.path.normcase(dest) != os.path.normcase(path) and os.path.exists(dest):
                if not messagebox.askyesno("Fichier existant",
                                           "{} existe déjà. Remplacer ?".format(new_name)):
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
            messagebox.showinfo("OK", "Métadonnées enregistrées.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    if initial:
        load(initial)
    root.mainloop()


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Lecture / modification des métadonnées PDF")
    ap.add_argument("pdf", nargs="?", help="Fichier PDF à ouvrir")
    ap.add_argument("--show", action="store_true", help="Afficher les métadonnées en console")
    a = ap.parse_args()
    if a.show:
        if not a.pdf:
            ap.error("--show nécessite un fichier PDF")
        show_console(a.pdf)
    else:
        run_gui(a.pdf)


if __name__ == "__main__":
    main()
