# V3 主控交付检查

本次为论文语言、图形和排版的终稿候选检查，不重新进行科学建模或扩展科学资格。

## 交付对象

- `FINAL_MANUSCRIPT_V3.docx`：唯一 V3 Word 母稿。
- `FINAL_MANUSCRIPT_V3.pdf`：上述母稿经 LibreOffice 更新目录后导出的 PDF，共 29 页。
- `../final_figures/submission_v3/ASSET_INDEX.md`：5 幅核心图的 SVG、矢量 PDF、600 dpi PNG、脚本和最小源数据索引。
- `BODY_EXPANSION_V3.md`：本轮正文展开内容及对应冻结边界。
- `WORD_QA_REPORT_V3.md`：执行器逐页检查记录。

## 主控独立复核

- 摘要占第 1–2 页，自动目录占第 3 页；DOCX 存在真实 TOC 域，使用 Heading 1/2 标题样式。
- 41 个内部目录链接均具有有效书签；41 个 PDF 目录显示页码均与实际跳转页一致。
- 35 个公式为原生 Office Math；9 张表；5 幅最终图的嵌入 PNG 与图形交付文件逐字节相同。
- 无修订记录、批注部件或页眉；作者与最后修改人属性为空。
- PDF 已逐页渲染检查；重点复查目录、长公式、图 2/4/5、Q3 推导、Q4 图文衔接和参考文献。最后调整只移动既有图前后解释，未添加科学内容。
- 展开过程中发现的质量成本表达遗漏和替代率尺度表述已按照冻结来源纠正：质量增量成本保留数据量乘数及相对锚点差；质量替代率明确为 S03 情景，不称已标定关系。
- 负值、失败验证、部分稳定、未验证情景及跨来源限制继续保留。

机器证据：`_qa/controller_v3/document_checks.json`、`_qa/controller_v3/final_navigation_and_assets.json`；页面图像为 `_qa/controller_v3/page-01.png` 至 `page-29.png`。该目录旧的 `page-30.png` 和旧 contact 图片来自中间候选，不属于当前 29 页交付。

## 明确保留的限制

本机 Microsoft Word COM 的只读打开/分页探测卡住，已停止本次探测进程，未写入母稿。因此本轮完成的是 DOCX 结构与链接检查、LibreOffice 目录更新和 PDF 逐页视觉检查；**尚未自动确认 Microsoft Word 原生分页与该 PDF 逐页完全一致**。提交前应在实际提交用 Word 中打开母稿，快速检查目录与分页。此限制不应被写成“原生 Word 已验收”。

## 当前文件指纹

- DOCX SHA-256：`9f74fa660d57f62e476731566e65867cb1a3c253abee4a5b81deda6eec3331a4`
- PDF SHA-256：`49c1a99648190ad86c532aa177770bcf15128da1143808a5048fad242cc61054`

交付资格：供队伍最终通读和提交环境检查的 V3 候选版。SCIENCE CLOSED 保持不变。
