# 引用抽取与收集规则

## 数据与位置

`引用清单.json` 含 source/source_sha256、occurrences（每处 occurrence/marker/paragraph/start/end/before/after/section/kind/identifiers）、references（首现去重的 id/type/value/first_occurrence/status/reason/key/match/warnings）、crosscheck，以及字段源的 restored_fields。

每一个显式前缀标识都保留；括号或方括号中仅由分号/逗号分隔的一组前缀标识合为一处引用，例如 `(PMID: 1; DOI: 10.1234/a)` 是一处、两篇。正文中的无括号前缀标识也能提取。跨 run 按段落可见字符定位；不扫描域指令文本作为正文。图表注与表格单元格均按文档顺序编号；种类标签只帮助审阅，不决定覆盖范围。

三方核对读取 `_process/Finalize/**/参考文献候选清单.md` 与 `04_manuscript/*/*核查说明.md`：各文件的标识集合差异逐条保存，候选清单不是真相；缺席文件标注不存在，不伪造支持。核验表若包含题名、期刊、第一作者年份，收集时和公开元数据比较。期刊全称规范化后完全相等，或本地期刊值与公开记录的 journalAbbreviation（ISO/short-container-title）规范化后相等时视为等价；缩写等价放行每次都记录 WARN，包含来源/列、标识、本地值、公开全称及缩写，并进入元数据、引用清单与写入结果报告。不得凭未验证的模糊相似度、自由首字母或词前缀猜测等价。真正不同的期刊、题名、年份、第一作者冲突仍停止，交作者裁决。候选清单中的结构化书目字段也需检查，不能仅凭“候选”认定已核验。

## 查重与来源

每条先按公开标识拉元数据，将 PMID 解析到 DOI，依次查 DOI → PMID → 题名+年份。DOI 小写、去 DOI URL 前缀及尾部句号逗号。PMID 兼容 extra 中 `PMID: N`、原生 PMID 字段、PubMed URL/libraryCatalog。多个命中停止；题名年兜底列 WARN，收集后由作者确认。

PMID 用 NCBI efetch 结构化作者列表；DOI 用 Crossref works；arXiv 用 Atom API。仅提交 ID 与 API 控制参数，正文从不进入请求。PubMed pages 优先完整 MedlinePgn，否则拼 StartPage–EndPage。Crossref 作者采用 family/given；集体作者采用单字段 name。arXiv 仅提供全名时保存为单字段作者，绝不按空格猜姓/名；因此产生结构化姓名不足 WARN。保留全部作者，不按引文样式截断。

条目有则填 volume、issue、pages、ISO/short-container journalAbbreviation、ISSN、language。题名、作者、年份、期刊（期刊条目）缺失时不臆造，保留人工标识并列原因；缩写缺失可以入库但列WARN。预印本用 preprint，CSL由本地API生成。document 不属于作者样例覆盖类型，遇到时先报告未经样例验证，不凭空扩展映射。

写入前保存 metadata 与目标集合计划，立即重查库；只对缺失条目 POST。有 PMID 则提交 `extra: PMID: N`（BibTeX 用 pmid）。Zotero 10 可能将其规范化为原生 PMID 字段；保留原始提交与回查快照，记录 WARN，查重兼容两者，不为恢复 Extra 改动已入库条目。既有库条目的书目字段与新公开记录不同列 WARN，不修改它；若涉及本地核验表/候选书目字段冲突，先请作者裁决。

## 三分类与人工保留

最终 references.status 只能是 `既有`、`新增`、`人工保留`，或显式作者映射产生的 `作者指定`。来源缺失、请求失败、必填数据不足时人工保留并写 reason，不丢标识。URL-only 不联网抓取。一个合并标识含任何人工保留条目时，整处原文保留，列明同组原因，不生成部分字段。应注入却没有 key/快照或未分类时阻断。

收集后 `zotero条目快照.json` 保存 raw、citation_item、resolved_identifiers；引用标识与库的 PMID/DOI桥接由公开 metadata 文件留证。完成时汇报三类数量、全部WARN、字段预计数与文献表位置，等作者批准后再 candidate。已获授权的隔离验收可完整执行，但不是作者 Word 验收。


## 作者映射（所引版本优先）

作者已在Zotero建好正式条目、核定实际引用版本时，可在collect中传 `--resolve-file <json>`。此功能只复用已存在条目，不抓取URL网页，不为了“全字段化”臆造书目信息或改用另一版本。是否支持正文论断仍由作者确认。

```json
{
  "note": "作者核定：使用原引用版本",
  "collection_key": "LZPSVVK8",
  "mapping": {
    "URL: https://example.org/paper": {
      "item_key": "ABCD1234",
      "note": "保留该会议版本"
    }
  }
}
```

`mapping` 为对象，键优先直接复制引用清单的完整id，必须逐字符相同。兼容作者样例中的裸 `https://...`/`http://...` 键：仅补固定 `URL: ` 前缀并记WARN，不改变URL本身。大小写/空白近似但不一致的键报错，不做casefold、去空白、百分号解码或重定向匹配。规范键与裸URL键若指向同一个id而重复出现也报错。无关且格式正确的映射键可以留在文件中，本稿未命中的URL保持人工保留。

值为 `{"item_key":"8位大写字母数字key","note":"可选说明"}`。备用形式为 `{"identifier":{"type":"DOI","value":"10.1234/example"},"note":"可选说明"}`，两种目标形式只能选一种。备用标识类型可为DOI、PMID、arXiv或URL，仅按当前库可识别的标识查找既有条目；若找不到或命中不唯一即停止，不抓取元数据来新建替代条目。PMID无法直接匹配当前库时，请作者改给已核定item_key。

根note与条目note合并进resolution.note；根collection_key可选，给出时要求命中条目在声明集合内，且该集合等于本轮目标集合，不移动条目。所有本稿命中目标在任何新增条目或集合之前统一检查；key不存在、目标标识无命中或歧义均硬错误停止并报告，绝不降级人工保留后继续写库。未提供映射、或本处未命中时，原来的URL-only人工保留规则不变。

命中后references.status=`作者指定`，key为既有条目key，resolution保存：

```json
{"source":"作者映射","file":"映射文件绝对路径","note":"合并后的作者说明","item_key":"ABCD1234"}
```

单列作者指定数量及WARN级“作者映射、需作者确认”，写入报告结果中保存resolution；`缺口与人工清单.md` 增加“已由作者映射”分节。未映射的URL仍原文保留。注入的占位始终是原标识原文，不把URL改成DOI；`(Author, year; URL: …)` 的作者/年份等其余字符与原稿一致。I1允许作者指定状态，I4独立比较字段URI中的key与resolution.item_key，不能仅依赖条目快照相等。

重跑时继续传同一映射文件，新过程目录重新查当前库；复用条目不新增。字段源重跑仍传上一轮引用清单做I9核对。作者映射只证明选定了条目，不证明引用论断或Word排版已经验收。
