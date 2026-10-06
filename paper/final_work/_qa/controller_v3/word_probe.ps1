$ErrorActionPreference='Stop'
$taskDir=$PSScriptRoot
$taskDocPath=Join-Path (Split-Path (Split-Path $taskDir)) 'FINAL_MANUSCRIPT_V3.docx'
$taskResult=Join-Path $taskDir 'word_probe_result.json'
$taskWord=$null
$taskDoc=$null
try {
  $taskWord=New-Object -ComObject Word.Application
  $taskWord.Visible=$false
  $taskWord.DisplayAlerts=0
  $taskWord.AutomationSecurity=3
  $taskWord.Options.UpdateLinksAtOpen=$false
  $taskDoc=$taskWord.Documents.Open($taskDocPath,$false,$true,$false)
  [ordered]@{open_succeeded=$true;read_only=$taskDoc.ReadOnly;toc_count=$taskDoc.TablesOfContents.Count;hyperlinks=$taskDoc.Hyperlinks.Count;pages=$taskDoc.ComputeStatistics(2);word_version=$taskWord.Version} | ConvertTo-Json | Set-Content -LiteralPath $taskResult -Encoding UTF8
} catch { @{error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $taskResult -Encoding UTF8 }
finally { if($taskDoc){$taskDoc.Close(0)}; if($taskWord){$taskWord.Quit(0)} }
