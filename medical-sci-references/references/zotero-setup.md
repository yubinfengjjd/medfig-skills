# Zotero 连接与安全写入

## 环境与就绪

作者维护 Zotero Desktop 和 Word 集成。脚本不启动、重启、终止进程，不写 prefs。个人库本地 API 默认 `http://127.0.0.1:23119`，Python urllib 的本地客户端固定 `ProxyHandler({})`，不会经系统代理访问 loopback。公开元数据请求使用系统正常 HTTPS 验证，不降低 TLS 检查。

每次执行 `zotero_collect.py probe --output-dir <过程目录>`。GET /api/、GET /api/users/0/items/top?limit=1、GET /connector/ping、POST /connector/getSelectedCollection 均需成功。网络/读库探测共尝试3次，间隔5秒；失败写报告，离线工作继续，实际联网步骤待恢复。不做环境修复。报告记录 X-Zotero-Version、Total-Results、Zotero-Server-ID 和所选集合。

## A：本地 API

授权文件默认 `%USERPROFILE%/.medical-sci-references/zotero-local-api-key.json`，可 `--key-file` 改路径。内容为 `key`、`server_id`、`library_user_id`；脚本仅读取，不打印 key、不上传、不自动改此文件。读取免 key。写入使用保存的 Zotero-API-Key 与本轮 GET 返回的 Zotero-Server-ID，不能沿用失效的 server id。

无副作用能力探测发送空数组 `POST /api/users/0/items []`：本环境返回 HTTP400 `No items provided`，没有条目提交；不等于真实条目写入成功。404/405/501 说明该写入口不支持，auto 模式选 B。认证/Server-ID 403/412/428 则停止写入，不降级。401 只重授权一次：`POST /api/local/authorize {"appName":"medical-sci-references"}`，携带 Server-ID，作者在场批准；返回 key 只在内存使用，不自动写任何凭证文件。缺少初始凭证时默认选B或提示作者先授权，不在无人在场时弹窗循环。实际 A 写入必须以条目 successful/success 与后续读库、集合回查为证据。

集合：项目标题为默认顶层集合名，读取作者决定 References 节的指定名后显式传 `--collection`。同名顶层集合复用，重名不唯一则停下。只有明确允许新建时传 `--allow-create-collection`；不改既有集合或给既有条目加集合。独立使用必须显式给集合。开发测试禁止创建集合，只能用作者指定测试集合。

## B：Connector

`--channel B` 可显式测试备用通道。先 POST `/connector/getSelectedCollection {}`，向作者报告名称、库与内部集合ID。必须名称、个人库 internal libraryID=1、SQLite副本中的目标 collectionID 都吻合且 editable。否则停止并请作者在 Zotero 选择目标集合；不得通过 UI 自动改选。

逐条生成完整 BibTeX，`POST /connector/import?session=<uuid>`，Content-Type text/plain。写前再次核对所选集合，写后 API 按 DOI（无DOI时按PMID/arXiv/题名年）回查 item key 与 collections。HTTP200 本身不等于入库成功。网络超时不重发 POST，先回查已计划条目，避免重复。

## 整数身份与只读副本

CSL-JSON 从 `/api/users/0/items/<key>?format=csljson` 取得。整数 itemID 只从复制的 sqlite/wal/shm 查询：`--sqlite <数据目录>/zotero.sqlite --work-dir <显式_tmp>`。默认数据目录为用户 home/Zotero。脚本复制到 `_tmp/zotero-readonly-<uuid>/`，以 mode=ro 开库，PRAGMA integrity_check 校验后查个人库 items/key/itemID 与 collections/key/collectionID。不会连接原数据库执行 SQL，也不删除快照。异常时停止身份映射，不能生成临时整数代替。

URI 采用 API 自身 CSL id，核对其 key；不硬编码用户ID。个人库已同步时形如 `http://zotero.org/users/<userID>/items/<key>`，未同步 URI 可为 users/local/<localUserKey>/items/<key>。当前脚本明确限定个人库，不接管群组库。

## 审计与撤销

保存 library-before/after、write-plan、逐条结果、最终 key 与集合。断网可能已写入，必须先用计划标识查重。恢复会话按当前库重新查重，不复制条目。作者可按新增key手动定位测试条目，确认后决定是否移除；脚本不自动清理 Zotero。
