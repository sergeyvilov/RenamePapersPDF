# RenamePapersPDF

python script to give human-readable names to academic papers

renames .pdf files based on DOI

requires an Internet connection

Usage:

First create new environment with all required packages
```
conda env create -f RenamePapersPDF.yml
```
then

```
conda activate rename_pdf
python3 rename_pdf.py pdf_to_rename.pdf
```
or
```
conda activate rename_pdf
python3 rename_pdf.py folder_with_pdfs_to_rename/
```
