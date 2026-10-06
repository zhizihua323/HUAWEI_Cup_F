"""Refresh the V3 table of contents with LibreOffice UNO and export PDF."""
from __future__ import annotations

import pathlib
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(name: str, value):
    item = PropertyValue()
    item.Name = name
    item.Value = value
    return item


def connect(port: int):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    last = None
    for _ in range(60):
        try:
            return resolver.resolve(
                f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
            )
        except Exception as exc:  # pragma: no cover - depends on office startup
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"LibreOffice UNO connection failed: {last}")


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: uno_finalize_v3.py DOCX PDF PORT")
    docx = pathlib.Path(sys.argv[1]).resolve()
    pdf = pathlib.Path(sys.argv[2]).resolve()
    port = int(sys.argv[3])
    ctx = connect(port)
    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx
    )
    document = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(str(docx)),
        "_blank",
        0,
        (prop("Hidden", True), prop("ReadOnly", False), prop("UpdateDocMode", 3)),
    )
    if document is None:
        raise RuntimeError(f"Could not open {docx}")
    try:
        indexes = document.getDocumentIndexes()
        for idx in range(indexes.getCount()):
            indexes.getByIndex(idx).update()
        try:
            document.getTextFields().refresh()
        except Exception:
            pass
        if hasattr(document, "calculateAll"):
            document.calculateAll()
        document.store()
        document.storeToURL(
            uno.systemPathToFileUrl(str(pdf)),
            (prop("FilterName", "writer_pdf_Export"), prop("Overwrite", True)),
        )
        print(
            {
                "docx": str(docx),
                "pdf": str(pdf),
                "indexes": indexes.getCount(),
                "pdf_exists": pdf.exists(),
                "pdf_bytes": pdf.stat().st_size if pdf.exists() else 0,
            }
        )
    finally:
        document.close(True)


if __name__ == "__main__":
    main()
