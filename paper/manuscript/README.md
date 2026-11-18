# Rebuilding the earthquake-sequence article

This directory contains the current article source, its figures, native editable
equations and the journal-specific Word generator. It reconstructs the document;
scientific experiments are reproduced separately under `research/sequences`.
No script here commits, pushes, publishes or submits an article.

The double-spaced journal document and the compact reading document have the same
text, equations, tables, figures, image links and fonts. The reading copy changes
only direct body paragraph auto-line spacing from 480 to 276 twips (1.15 lines).
Use the double-spaced document for the journal workflow. The reading format is
provided for convenient review and does not redefine the journal template.

## Inputs

- `manuscript.md`: maintained scientific text, captions, table data and placement.
- `figures_main.json`: thirteen groups and every panel's exact interactive URL.
- `figures/`: twenty-five PNGs used in Word, four additional provenance composites,
  and six exact native SVG map/timeline exports. No image is regenerated here.
- `figure_provenance.json`: nine preserved original groups and eight original panels.
- `author_metadata.json`: title and human author/core-property values.
- `BUILD_INPUTS.json`: paths, sizes and SHA256 hashes of the document inputs/code.
- `build/equations.json`: two display equations and fourteen inline mathematical
  expressions, rendered as editable Office Math by `native_equations.py`.

The original journal template is deliberately not redistributed or relicensed.
Its source commit and SHA256 are in `paper/templates/provenance.json`. The
restoration helper fetches that exact official file, verifies its size and hash,
and refuses to overwrite a different local template. A local copy with the same
SHA256 can be supplied for offline rebuilding.

## Build from the repository root

Use Python 3.10 or later. The decoded-part replay was performed with Python
3.12.14 and lxml 6.1.1 (see the [pinned requirement](requirements.txt)). An isolated Python
environment is recommended:

```text
python -m venv .venv-manuscript
```

After activating that environment, run:

```text
python -m pip install -r paper/manuscript/requirements.txt
python paper/manuscript/build/rebuild.py --download-template --output-dir outputs/manuscript_rebuild_01
```

For an already retained official template, replace `--download-template` with
`--template-source path/to/C&G_WordTemplate.docx`. Quote paths containing spaces
or shell metacharacters. Once installed and verified, the local template needs
no network access. The official source is
[cageo/CAGEO_WordTemplate](https://github.com/cageo/CAGEO_WordTemplate/tree/6c95188814973fba89ce1ac8911726b6e1e8f4f5).

The output directory must be new and remain under repository `outputs/`.
Rebuilding writes a DOCX, a build report and a structural receipt. It checks the
sealed source, metadata, figures, generator and template; no private context,
draft, previous delivery, scientific output or local review record is required.

## Reading copy and PDF

```text
python paper/manuscript/build/make_reading_copy.py --journal-docx outputs/manuscript_rebuild_01/Seismic_CG_sequences_manuscript.docx --reading-docx outputs/manuscript_rebuild_01/Seismic_CG_sequences_manuscript_reading.docx --receipt outputs/manuscript_rebuild_01/reading_receipt.json
```

The helper restores a clone of the modified XML and requires it to equal the
original tree; every other decoded DOCX part must remain identical.

PDF export requires Microsoft Word on Windows and the fonts Times New Roman and
Cambria Math. The supplied PowerShell exporter opens a read-only document in a
fresh empty Word instance, exports with native SVG support, and closes only that
document. It does not quit Word or save over its input:

```text
powershell -NoProfile -File paper/manuscript/build/export_word_pdf.ps1 -DocumentPath outputs/manuscript_rebuild_01/Seismic_CG_sequences_manuscript.docx -PdfPath outputs/manuscript_rebuild_01/Seismic_CG_sequences_manuscript.pdf -ReceiptPath outputs/manuscript_rebuild_01/pdf_receipt.json
```

Use the corresponding reading-DOCX path to export its PDF. Word version, fonts
and PDF renderer can affect pagination. Structural checks do not replace
rendering and inspecting every PDF page, especially native SVG panels, tables,
equations and image hyperlinks. No cross-renderer pixel identity is promised.

## Integrity and maintenance

`build/compare_docx_parts.py` compares all decoded ZIP parts of two DOCX files,
with no exceptions for metadata, paths, content or layout. ZIP timestamps and
compression bytes need not match. The retained-template build preserves sixteen
template parts exactly and adds the article's media and native SVG content type.

After an intentional source or asset edit, keep the old build, review the change,
and create a fresh input seal. `build/seal.py --output path` creates a new seal;
replacing `BUILD_INPUTS.json` additionally requires its exact old hash through
`--replace-if-sha`. A new seal records inputs, not author approval or scientific
validation. Publication and submission remain separate human actions.

Licenses and provenance are described in `THIRD_PARTY_NOTICES.md`. The manuscript
retains its truthful academic assistance declaration; document reconstruction
does not imply editorial acceptance or human approval.
