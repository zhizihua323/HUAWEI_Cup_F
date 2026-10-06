from pathlib import Path
import win32com.client as win32

root=Path(__file__).resolve().parents[2]
docx=root/'paper'/'showcase'/'SHOWCASE_MANUSCRIPT_V0_9.docx'
pdf=root/'paper'/'showcase'/'SHOWCASE_MANUSCRIPT_V0_9.pdf'
word=win32.gencache.EnsureDispatch('Word.Application')
word.Visible=False
word.DisplayAlerts=0
doc=None
try:
    doc=word.Documents.Open(str(docx), ConfirmConversions=False, ReadOnly=False)
    doc.Fields.Update()
    if doc.TablesOfContents.Count:
        doc.TablesOfContents(1).Update()
    doc.Save()
    doc.ExportAsFixedFormat(str(pdf), ExportFormat=17, OpenAfterExport=False, OptimizeFor=0, Range=0, Item=0, IncludeDocProps=True, KeepIRM=True, CreateBookmarks=1, DocStructureTags=True, BitmapMissingFonts=True, UseISO19005_1=False)
    print(pdf)
finally:
    if doc is not None:
        doc.Close(SaveChanges=0)
    word.Quit()
