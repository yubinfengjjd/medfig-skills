# 范围与确认决策

这是医学论文流水线第12步，前接成品 Word 组装与润色。产物是同命名版本递增的 Zotero 原生字段主稿，旧主稿归档。

- 顺序：收集进 Zotero → 作者批准 → 候选注入 → 逐项核对 → apply → 作者 Word Refresh 验收。
- 覆盖正文、主图注、主表题表注；补充材料不能含引用，本阶段不处理补充材料。
- 公开标识符 PMID、DOI、arXiv 可抓元数据；URL-only 保留纯文本，逐条列原因。不能为了字段化臆造条目。
- 本地 API 读写优先，connector 作为本地写入不支持时的备用；只新增，不修改或删除既有条目，不改设置。
- 初始样式 Elsevier Vancouver 短作者表：`http://www.zotero.org/styles/elsevier-vancouver-short-author-list`。以后由作者在 Word 换样式。
- assets 中作者制作的两份原始 Word 样例是字段格式依据，须保持只读；不依赖任何外部 Zotero 插件、研究编排框架或既往会话。
- 网络只提交公开标识符和检索词给 PubMed/Europe PMC/Crossref/arXiv；稿件、图注、未发表数据一律留本地。
- 过程目录保存全部清单、来源、key、时间、哈希、差异及未完成项。文件替换先归档，不删除历史。
- Zotero 由作者保持运行；连接探测失败总计3次、间隔5秒，随后记录连接待办并继续离线实现/准备，绝不自行修复环境。
- 作者负责 Zotero 授权弹窗、B通道集合选择、Word 打开与 Refresh 验收。没有作者验收，只能记“待确认”；实际安装或修改全局入口须有对应写权限与授权。
