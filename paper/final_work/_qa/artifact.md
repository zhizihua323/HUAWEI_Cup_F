# Official Word Template Distillation Contract

## V2 anonymous submission override — 2026-09-26

User authorized structural reconstruction under the 2026 official format rules. The submission copy intentionally removes the identity cover and artwork, starts abstract pagination at 1, and retains the source template page geometry. It uses 16pt Hei title, 14pt centered Hei H1, 12pt SimSun for all remaining Chinese, single spacing and centered continuous footer page numbers. V1 rules below about a cover page 0, smaller table/caption fonts, Hei H2 and Kai H3 are superseded. The retained original template remains read-only. Rendering now uses user-installed D:\LibreOffice\program\soffice.exe through render_docx.py. The actual delivery is V2 DOCX/PDF, with frozen scientific results unchanged and only cited references included.

## Reference

- Original official template: `C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\参考资料\2026华为杯研赛latex模板\附件3：“华为杯”第二十三届中国研究生数学建模竞赛论文模板.doc`
- Original SHA-256: `195B06CF670EC1AEB796BFD07E6D3E98E36D16DB119308DCF4D0756319FE2E29`
- Retained converted reference: `C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\paper\final_work\_qa\official_template_converted.docx`
- Converted reference SHA-256: `9423744F3C985F5D7AE4E4198E5B99D12581CF22E123312E2D411E866D1922BC`
- Render evidence: `paper/final_work/_qa/template-render/`
- Evidence files: `template-style-evidence.json`, section/style/heading/image/field/footnote/content-control audits recorded in the execution log.
- Page count: 4 in the untouched converted reference. Pages 3 and 4 are blank continuation pages caused by trailing empty paragraphs.
- Section count: 1.

## Page System

- A4 portrait, 8.27 × 11.69 inches.
- Margins: left 0.89 in, right 0.88 in, top 1.18 in, bottom 0.69 in.
- One column.
- Different first page enabled.
- No visible header.
- Two footer parts with centered `PAGE` fields; official rendering shows cover page 0 and summary page 1.
- The first page is the official identity cover. The second page is the official title, abstract, and keywords page. Body pages follow the summary page.

## Typography and Components

- Official cover artwork, logos, lines, table geometry, and footer page fields are preserve-only.
- The converted source uses legacy East Asian font encoding for some cover text. Those runs render correctly in Word but extract as mojibake; they must not be normalized or rebuilt.
- New body text uses SimSun 12 pt for Chinese, Times New Roman 12 pt for Latin characters, single line spacing, justified alignment, and a two-character first-line indent.
- Level 1 headings use SimHei 14 pt, centered, black, with keep-with-next.
- Level 2 headings use SimHei 12 pt, left aligned, black, with keep-with-next.
- Level 3 headings use KaiTi 12 pt, left aligned, black, with keep-with-next.
- Captions use SimSun 10.5 pt, centered, black.
- Tables use visible 0.5 pt gray borders, repeating header rows, and 9 pt text where necessary.
- Display equations use native OMML with sequential Arabic equation numbers.

## Slot Map

- Cover identity table: preserve official labels and blank user-entry cells. No school, team number, or names are available, so the value cells remain blank.
- Summary page title line: replace with the manuscript title.
- Summary page abstract block: replace with the final frozen-results abstract.
- Summary page keywords block: replace with final keywords.
- Trailing blank template paragraphs after the summary page: removable; they are only empty capacity and create blank pages.
- Main body: append after a page break following the keywords block, using official page geometry and footer fields.
- Figure assets: insert only when delivered under `paper/final_figures/`; until then, retain stable `FIG-*` captioned slots.
- Reference assets: insert only when delivered under `paper/final_references/`; until then, retain stable `REF-*` citation anchors and an explicit unresolved reference section.

## Package Preservation

- Preserve cover media: `word/media/image1.png`, `image2.png`, `image3.jpeg`, and `image4.png`.
- Preserve footer1/footer2 page fields, document relationships, theme, font table, and official cover table.
- Body authoring may extend `word/document.xml`, styles, numbering, and settings. Existing media and footer relationships must remain present.
- Baseline package contains 20 parts. The source media hashes are recorded in the command log; preservation is verified by final package inventory.

## Fidelity Gates

1. Official cover logos, title treatment, identity table, and lines remain visually unchanged.
2. Official summary-page competition title and page geometry remain source-derived.
3. Cover is page 0; abstract page is page 1; subsequent pages retain centered page numbers.
4. No headers are added.
5. The original `.doc` and converted reference remain byte-for-byte unchanged.
6. Every final page is rendered through Word PDF export and inspected as PNG because the bundled Windows runtime has no LibreOffice executable.
