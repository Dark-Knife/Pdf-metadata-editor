# PDF Metadata Editor

Petit outil en Python avec interface graphique pour **lire et modifier les métadonnées d'un fichier PDF** : titre, auteur, sujet, mots-clés, dates de création et de modification, champs personnalisés, nom du fichier, etc. Inspiré de la fenêtre « Propriétés du document » de PDF Explorer (RTT Software).

## Fonctionnalités

- Lecture et modification des champs standards : **Titre, Auteur, Sujet, Mots-clés, Créateur, Producteur**
- Édition des **dates de création et de modification** (conversion automatique vers le format interne PDF `D:AAAAMMJJHHMMSS+HH'mm'`)
- **Champs personnalisés** : ajout, modification, suppression
- **Renommage du fichier** à l'enregistrement
- Modification des **dates du fichier dans le système** (création et modification, création sous Windows uniquement)
- Informations en lecture seule : nombre de pages, version PDF, chiffrement, linéarisation, présence de XMP, taille
- **Synchronisation XMP** optionnelle pour que les autres lecteurs PDF affichent les mêmes valeurs
- **Enregistrer sous…** pour travailler sur une copie sans toucher à l'original
- Mode console pour afficher les métadonnées (`--show`)

## Installation

Prérequis : Python 3.8 ou plus récent (Tkinter est inclus avec l'installateur Python officiel sous Windows).

```bash
git clone https://github.com/<votre-compte>/pdf-metadata-editor.git
cd pdf-metadata-editor
pip install pikepdf
```

## Utilisation

Interface graphique :

```bash
python pdf_metadata_editor.py
```

Ouvrir directement un fichier :

```bash
python pdf_metadata_editor.py document.pdf
```

Afficher les métadonnées dans la console, sans interface :

```bash
python pdf_metadata_editor.py document.pdf --show
```

### Formats de date acceptés

| Saisie | Exemple |
|---|---|
| `AAAA-MM-JJ HH:MM:SS` | `2026-11-08 10:00:00` |
| `AAAA-MM-JJ HH:MM` ou `AAAA-MM-JJ` | `2026-11-08` |
| `JJ/MM/AAAA HH:MM` ou `JJ/MM/AAAA` | `08/11/2026 10:00` |
| Date PDF brute | `D:20261108100000+01'00'` |
| Date actuelle | `now` ou `maintenant` |

Un champ laissé vide est **supprimé** du PDF.

## Limites

- Les PDF protégés par un mot de passe ne sont pas pris en charge.
- Les champs personnalisés n'existent que dans le dictionnaire Info du PDF, pas dans le XMP.
- Enregistrer réécrit le fichier : sa date de modification dans le système change, sauf si l'option de conservation est cochée.
- La modification de la date de création du fichier n'est possible que sous Windows.

## Dépendances

- [pikepdf](https://github.com/pikepdf/pikepdf) : lecture et écriture des PDF (basé sur QPDF)
- Tkinter : interface graphique (bibliothèque standard de Python)

## Licence

MIT
