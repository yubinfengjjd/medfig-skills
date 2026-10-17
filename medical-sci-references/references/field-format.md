# 作者样例字段格式

样例只读保存在 assets/baseline-sample.docx 与 assets/baseline-sample-types.docx；前者缺失拒绝注入，后者缺失仅标注 preprint 映射未经样例验证。下列原始片段来自这两份文件，不依赖任何其他项目文件。

复杂域结构：w:r/w:fldChar(begin) → 一个或多个w:instrText → fldChar(separate) → 原结果run → fldChar(end)。必须先拼接begin至separate之间全部instrText再解析JSON；第一份样例首域拆成1020/765/510/255/1106字符。新字段可用单段指令，首尾各一空格。一个标识处对应一个域，多篇按原顺序放 citationItems。citationID 与文档session均为8位字母数字随机串。

citationItems.id 与 itemData.id 都是本地真实整数 itemID，同一条目在所有域必须一致；URI取库API真实CSL id。properties.unsorted=false、noteIndex=0、schema沿用样例。注入只把 formattedCitation/plainCitation 改成原标识全文，结果run直接复用源文字，刷新前文本与逐字符直接格式完全相同。

itemData直接取本地API的CSL-JSON，不手写Zotero到CSL字段映射。与样例298/307两个期刊和297预印本的实测逐键比较发现：除id的URI→整数外，期刊只需去URL/accessed；preprint保留URL/accessed，type为article。这样三个样例逐键完全相等。此结论只覆盖作者样例中的类型；document没有可用样例，不猜映射。PMID等新字段保留API原生转换结果。

偏好：docProps/custom.xml 保存 ZOTERO_PREF_1 与 ZOTERO_PREF_2，lpwstr文本拼接为data XML；前者存主体，后者是 </data>。fmtid固定，pid取目标未占用值；保留其他属性。session换新随机串。样式：Elsevier Vancouver短作者表，fieldType=Field。XML用序列化库转义，不手工插入未转义尖括号。

[Content_Types].xml注册 `/docProps/custom.xml`，类型为 `application/vnd.openxmlformats-officedocument.custom-properties+xml`；_rels/.rels的Type为 `http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties`，Target为docProps/custom.xml，rId选未占用值。已有注册不重复加。

文末在最终sectPr之前新增：Arial12空段、Normal并直接格式Arial12加粗的References标题、文献表begin/instruction/separate段、承载end的空段。文献表指令不带条目信息；结果空白，待作者Refresh。原文档所有其他段落、空白、资产、表格与分节零改动。

## 原始引文字段指令

```text
 ADDIN ZOTERO_ITEM CSL_CITATION {"citationID":"pkqf33Dm","properties":{"unsorted":false,"formattedCitation":"[1,2]","plainCitation":"[1,2]","noteIndex":0},"citationItems":[{"id":298,"uris":["http://zotero.org/users/12981125/items/VK8BIE8J"],"itemData":{"id":298,"type":"article-journal","container-title":"Water Research","DOI":"10.1016/j.watres.2025.124693","ISSN":"00431354","journalAbbreviation":"Water Research","language":"en","page":"124693","source":"DOI.org (Crossref)","title":"Using machine learning to deeply analyze the critical role of trace element additives in anaerobic digestion and guide the optimization of addition strategies","volume":"288","author":[{"family":"Yu","given":"Yating"},{"family":"Zhang","given":"Yi"},{"family":"Feng","given":"Yijing"},{"family":"Leong","given":"Zheng Hao"},{"family":"Pan","given":"Junting"},{"family":"Su","given":"Jianping"},{"family":"Li","given":"Yeqing"}],"issued":{"date-parts":[["2026",1]]}}},{"id":306,"uris":["http://zotero.org/users/12981125/items/ADZGDV9D"],"itemData":{"id":306,"type":"article-journal","abstract":"Background  Colorectal cancer (CRC) is a common gastrointestinal cancer with poor response to therapy and high metastatic risk. Cancer-associated fibroblasts (CAFs) support tumor progression, but their functional heterogeneity remains poorly understood.\nMethods  We integrated multi-omics data from 10,164 samples, including single-cell, bulk, spatial transcriptomics, and proteomics, to identify and characterize CAF subpopulations. Functional validation was performed using molecular assays, in vivo models, and drug screening.\nResults  We identified a COL10A1-positive fibroblast subpopulation (COL10A1+Fib) associated with CRC progression and poor patient prognosis. COL10A1+Fib promotes tumor cell proliferation, immune suppression, and metastasis. Mechanistically, COL10A1+Fib facilitates epithelial–mesenchymal transition (EMT) in CRC cells via COL10A1 secretion and induces M2 macrophage polarization through the COL10A1/CD18/JAK1/STAT3 signaling axis. In turn, M2 macrophages enhance COL10A1 expression in fibroblasts via the TGF-β/RUNX2 pathway, forming a pro-tumorigenic feedback loop. The DNA-PKcs inhibitor NU7441 reduces COL10A1 expression, suppresses CAF activity, and reverses EMT and M2 polarization. Pan-cancer analysis suggests that COL10A1+Fib may have similar functional roles across multiple major solid tumors.\nConclusion  Our study identifies a CAF subpopulation, COL10A1+Fib, associated with CRC progression and immune suppression, suggesting it as a potential therapeutic target in CRC and possibly other malignancies.","container-title":"Journal of Experimental & Clinical Cancer Research","DOI":"10.1186/s13046-025-03510-8","ISSN":"1756-9966","issue":"1","journalAbbreviation":"J Exp Clin Cancer Res","language":"en","page":"243","source":"DOI.org (Crossref)","title":"COL10A1+ fibroblasts promote colorectal cancer metastasis and M2 macrophage polarization with pan-cancer relevance","volume":"44","author":[{"family":"Hu","given":"Shangshang"},{"family":"Ding","given":"Muzi"},{"family":"Lou","given":"Jinwei"},{"family":"Qin","given":"Jian"},{"family":"Chen","given":"Yuhan"},{"family":"Liu","given":"Zixuan"},{"family":"Li","given":"Yue"},{"family":"Nie","given":"Junjie"},{"family":"Xu","given":"Mu"},{"family":"Sun","given":"Huiling"},{"family":"Gu","given":"Xinliang"},{"family":"Xu","given":"Tao"},{"family":"Wang","given":"Shukui"},{"family":"Wang","given":"Shukui"},{"family":"Pan","given":"Yuqin"}],"issued":{"date-parts":[["2025",8,18]]}}}],"schema":"https://github.com/citation-style-language/schema/raw/master/csl-citation.json"} 
```

## 原始文献表指令（首尾空格保留）

```text
 ADDIN ZOTERO_BIBL {"uncited":[],"omitted":[],"custom":[]} CSL_BIBLIOGRAPHY 
```

## 原始偏好与注册片段

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="ZOTERO_PREF_1"><vt:lpwstr>&lt;data data-version="3" zotero-version="10.0.6"&gt;&lt;session id="05hWo5mH"/&gt;&lt;style id="http://www.zotero.org/styles/elsevier-vancouver-short-author-list" hasBibliography="1" bibliographyStyleHasBeenSet="1"/&gt;&lt;prefs&gt;&lt;pref name="fieldType" value="Field"/&gt;&lt;/prefs&gt;</vt:lpwstr></property><property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="3" name="ZOTERO_PREF_2"><vt:lpwstr>&lt;/data&gt;</vt:lpwstr></property></Properties>
```

```xml
<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>
```

rId4只展示样例原值，不作为目标固定值。

## 样例校验值

- baseline-sample.docx SHA256 0cdbff1960e634f9d18f50ef27b9b6ba4fbf18ae452b31f4dcd758d5d8abb598
- baseline-sample-types.docx SHA256 171bbd8eb5ecb0afaecab84b8253791879a12b7ae49e5599976dcd585cc57511
