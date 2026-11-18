# Article materials and third-party rights

The repository's MIT license applies to the authors' own document-generation
software. It does not relicense the journal template, manuscript, figures, data,
or third-party materials. Manuscript text and author-created figures retain the
named human authors' rights; no new blanket license is imposed by this folder.

The official Computers & Geosciences Word template is supplied by
[cageo/CAGEO_WordTemplate](https://github.com/cageo/CAGEO_WordTemplate/tree/6c95188814973fba89ce1ac8911726b6e1e8f4f5).
That pinned tree exposes the DOCX without a separate license file. Consequently,
the reference binary is restored from its official source for authoring and is
not included in this publication payload or described as MIT-licensed.
`paper/templates/provenance.json` records its exact identity. The derivative
article preserves the retained template's styles, page structure and credits.

The figures retain their source attribution: SSN/UNAM observations and captured
terms, USGS ComCat records, NRCan data under the Open Government Licence–Canada,
Natural Earth cartographic context, and PB2002/Bird plate boundaries with the
credited Ahlenius/Nordpil/csterling ODC-BY provenance. A screenshot or native map
export does not change the providers' rights or establish earthquake identities.
Leaflet attribution remains visible in the native map materials.

The generator depends on [lxml](https://pypi.org/project/lxml/6.1.1/), distributed
under BSD-3-Clause with its own dependency notices. It renders the article's
mathematical statements; it does not bundle or execute the GPL scientific author
code, NumPy detector, data acquisition or benchmarking workflows. Their distinct
licenses remain with the separate scientific reproduction package.

The article's references and academic assistance disclosure are preserved. Git
authorship and the scientific responsibility of the named human authors are not
assigned by a document generator.
