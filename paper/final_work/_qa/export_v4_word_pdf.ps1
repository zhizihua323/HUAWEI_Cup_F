$ErrorActionPreference='Stop'
$d=(Resolve-Path 'paper/final_work/FINAL_MANUSCRIPT_V4.docx').Path
$tempDir='C:\Temp'
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$p=(Join-Path $tempDir 'FINAL_MANUSCRIPT_V4_WORD.pdf')
$w=New-Object -ComObject Word.Application
$w.Visible=$false
$w.DisplayAlerts=0
try {
  $doc=$w.Documents.Open($d,$false,$true)
  try {
    $doc.ExportAsFixedFormat($p,17)
  } finally {
    $doc.Close([ref]0)
  }
} finally {
  $w.Quit()
}
Copy-Item -LiteralPath $p -Destination (Join-Path (Resolve-Path 'paper/final_work').Path 'FINAL_MANUSCRIPT_V4_WORD.pdf') -Force
Write-Output $p
