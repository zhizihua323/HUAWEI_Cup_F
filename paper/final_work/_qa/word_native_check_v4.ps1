$ErrorActionPreference = 'Stop'
$docPath = (Resolve-Path 'paper/final_work/FINAL_MANUSCRIPT_V4.docx').Path
$outPath = (Join-Path (Resolve-Path 'paper/final_work/_qa').Path 'word_native_check_v4.json')
$word = $null
$doc = $null
try {
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $doc = $word.Documents.Open($docPath, $false, $true)
  $doc.Repaginate()
  $tocCount = $doc.TablesOfContents.Count
  $hyperlinkCount = $doc.Hyperlinks.Count
  $pageCount = $doc.ComputeStatistics(2)
  $tableCount = $doc.Tables.Count
  $inlineShapes = $doc.InlineShapes.Count
  $head1 = 0
  $head2 = 0
  foreach ($p in $doc.Paragraphs) {
    try { $s = [string]$p.Range.Style.NameLocal } catch { $s = [string]$p.Range.Style }
    if ($s -match '标题 1|Heading 1') { $head1++ }
    if ($s -match '标题 2|Heading 2') { $head2++ }
  }
  $result = [ordered]@{
    status = 'PASS'
    opened_read_only = $true
    page_count = $pageCount
    toc_count = $tocCount
    hyperlink_count = $hyperlinkCount
    table_count = $tableCount
    inline_shape_count = $inlineShapes
    heading1_count = $head1
    heading2_count = $head2
  }
} catch {
  $result = [ordered]@{status='FAIL'; error=$_.Exception.Message}
} finally {
  if ($doc -ne $null) { $doc.Close([ref]0) }
  if ($word -ne $null) { $word.Quit() }
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
}
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $outPath -Encoding UTF8
$result | ConvertTo-Json -Depth 4
