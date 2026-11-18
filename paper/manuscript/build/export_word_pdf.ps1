param(
    [Parameter(Mandatory=$true)][string]$DocumentPath,
    [Parameter(Mandatory=$true)][string]$PdfPath,
    [Parameter(Mandatory=$true)][string]$ReceiptPath
)

# Optional file exporter. It is prepared, not executed, by the pipeline agent.
# A fresh Word COM application must have zero documents before we open ours.
# Never attach to an active Word instance and never save the input DOCX.
$ErrorActionPreference = 'Stop'
$sequenceBase = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$sequenceDocument = [System.IO.Path]::GetFullPath($DocumentPath)
$sequencePdf = [System.IO.Path]::GetFullPath($PdfPath)
$sequenceReceipt = [System.IO.Path]::GetFullPath($ReceiptPath)
foreach ($sequenceTarget in @($sequenceDocument,$sequencePdf,$sequenceReceipt)) {
    if (-not $sequenceTarget.StartsWith($sequenceBase + [System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Document export paths must remain inside the repository'
    }
}
if ([System.IO.Path]::GetExtension($sequenceDocument) -ne '.docx' -or [System.IO.Path]::GetExtension($sequencePdf) -ne '.pdf') {
    throw 'Expected DOCX input and PDF output'
}
if (-not (Test-Path -LiteralPath $sequenceDocument -PathType Leaf)) { throw 'Missing source DOCX' }
if (Test-Path -LiteralPath $sequencePdf) { throw 'Use a new PDF target or explicitly archive the previous new-build PDF first' }
if (Test-Path -LiteralPath $sequenceReceipt) { throw 'Never overwrite an export receipt' }
$sequenceBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $sequenceDocument).Hash.ToLowerInvariant()
$sequenceWord = $null
$sequenceDoc = $null
$sequenceStarted = Get-Date
try {
    $sequenceWord = New-Object -ComObject Word.Application
    if ($sequenceWord.Documents.Count -ne 0) {
        throw 'Word returned an instance containing existing documents; no document was closed or changed'
    }
    $sequenceWord.Visible = $false
    $sequenceWord.DisplayAlerts = 0
    $sequenceWord.AutomationSecurity = 3
    $sequenceDoc = $sequenceWord.Documents.Open($sequenceDocument,$false,$true,$false)
    $sequenceDoc.ShowRevisions = $false
    $sequenceDoc.Repaginate()
    [void]$sequenceDoc.Fields.Update()
    $sequencePages = $sequenceDoc.ComputeStatistics(2)
    # wdExportFormatPDF=17; wdExportOptimizeForPrint=0; wdExportAllDocument=0;
    # wdExportDocumentContent=0 excludes markup; bookmarks use native headings.
    $sequenceDoc.ExportAsFixedFormat2($sequencePdf,17,$false,0,0,1,$sequencePages,0,$true,$true,1,$true,$false,$false,$true)
    $sequenceDoc.Close(0)
    [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($sequenceDoc)
    $sequenceDoc = $null
    $sequenceAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $sequenceDocument).Hash.ToLowerInvariant()
    if ($sequenceBefore -ne $sequenceAfter) { throw 'Input DOCX changed during PDF export' }
    $sequenceResult = [ordered]@{
        status = 'EXPORTED_REQUIRES_VISUAL_REVIEW'
        started = $sequenceStarted.ToUniversalTime().ToString('o')
        completed = (Get-Date).ToUniversalTime().ToString('o')
        docx = $sequenceDocument
        docx_sha256 = $sequenceAfter
        docx_unchanged = $true
        pdf = $sequencePdf
        pdf_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sequencePdf).Hash.ToLowerInvariant()
        pages_word = $sequencePages
        renderer = 'Microsoft Word native ExportAsFixedFormat2 OptimizeForImageQuality=true through a fresh isolated document instance'
        visual_review = 'PENDING every-page inspection after Poppler rasterization'
    }
    $sequenceResult | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $sequenceReceipt -Encoding UTF8
    $sequenceResult | ConvertTo-Json -Depth 5
}
finally {
    if ($null -ne $sequenceDoc) {
        $sequenceDoc.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($sequenceDoc)
    }
    if ($null -ne $sequenceWord) {
        # Do not call Application.Quit: only our explicitly opened document closes.
        # Releasing our COM reference leaves every user Word document untouched.
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($sequenceWord)
    }
}
