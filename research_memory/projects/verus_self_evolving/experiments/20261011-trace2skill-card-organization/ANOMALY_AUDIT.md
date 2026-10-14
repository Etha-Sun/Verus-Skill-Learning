# v4 停机与轨迹异常审计

日期：2026-10-12。只读审计既有结果，无新增模型调用、无重跑。
原始结果、合同、ledger、冻结实现均未改动。生成的审计副本位于运行目录的
`audit/anomaly_audit.json`，附带来源 SHA256；可用同目录脚本复算。

## 1. 为什么停止：迟到的上游传输错误触发全局保护

这次 systemd 正常托管到程序主动报错退出，和此前 nohup 主进程消失不是同一故障。
也不是额度不足、模型选错或 skill 的证明内容导致停止。

| UTC 时间 | 证据与事件 |
| --- | --- |
| 10:38:56 | B组 `0e8d3ca5b02dc01ee01f` 开始 |
| 10:48:24 | 此题最后一次请求发往上游 |
| 10:48:56 左右 | actor 达到600秒，结束求解；请求线程仍在等待上游 |
| 10:48:58 | 此题最终检查和超时结果写入，此时还没收到上游异常 |
| 10:49:24 | A组 `9b9f6ccef89db4103c7f` 开始 |
| 10:50:19 | 上游 HTTP chunked 流意外结束，抛出 `IncompleteRead(1835121 bytes read)` |
| 10:52:30–37 | 后续A题请求被共享 bridge 以409拒绝；CLI重连后仍失败 |
| 10:52:38 | A题运行约193.65秒后以技术异常结束，不是用满600秒未解出 |
| 10:52:51 | driver完成日志/用量收尾，保存25条结果后退出；15项尚未启动 |

源码直接证据：`codex_deepseek_bridge.py` 的 `response.read()` 读取 HTTP chunk
时遇到 EOF；异常写入 `config.halted_error`。随后同一个 bridge 拒绝所有新请求，
`validate_card_revision.py` 看到该标志便停止调度。

这是既定 fail-closed 保护：遇到响应不完整、费用未知时不自动重发。
它保护费用和证据，但共享错误标志会影响其他任务。无法仅凭这些日志进一步判定
断流发生在 DeepSeek 服务端、网络中间层还是其他传输环节。
“读到约1.84MB”不是“达到输出token上限”；日志没有证明输出上限触发。

日志中的 BrokenPipe 是 bridge 尝试向已断开的 actor 写回响应/错误时发生的，
不能据此推断服务器或 systemd 又丢失了任务。此前超时后回写也会产生该日志。
两条相同 failures 是重复登记同一共享错误，不是两次独立上游故障。
CLI显示五次重连，但均被本地已停止的 bridge 拒绝，不是五次额外付费重跑。

## 2. “证明双通过但V0_INVALID”到底是什么

B组 `aa78e84a931f703c7e9c`：约281.32秒完成；独立 Verus 检查为
`2 verified, 0 errors`，Lynette退出0；input和skill未变，provider与终端均正常。
事件日志配对、快照、文件哈希、完整输出检查也都通过。

唯一使f3失败的直接条件是 `shell_edit_suspect_count=1`：

```text
cp /tmp/orig_cand.rs candidate.rs
```

TASK明确要求所有代码修改走文件编辑/patch工具，禁止用cp修改candidate.rs。
模型先把自己的candidate备份到`/tmp/cand_backup.rs`，之后复制恢复；轨迹能追溯
这份备份的来源，没有证据表明它来自外部参考答案。模型还创建了临时语法测试文件，
也不应把这条轨迹描述成完全遵守“只编辑candidate.rs”的协议。

结论：这是实际编辑协议违规，不是证明失败、日志丢失或provider故障。
保留“600秒内证明/安全双通过”事实，同时单独披露协议不合格；不能偷偷放宽规则、
抹掉异常或重跑到合格为止。此违规不是本次全局停机的触发原因。

## 3. 目前可确认的结果

| 维度 | A 扁平卡 | B 聚类reduce |
| --- | --- | --- |
| 已有episode记录 | 13 | 12 |
| 600秒内独立证明/安全双通过 | 8 | 8 |
| 双通过且V2_TRACE | 8 | 7 |
| 达到600秒超时 | 4 | 4 |
| 提前被基础设施中止 | 1 | 0 |
| 已超时后才收到上游错误 | 0 | 1（包含在4个超时内） |

两组双通过的是相同8道题。fidelity、证明结果、provider结算是不同维度；
本审计不事后把原定主指标替换为新的成功标准，也不把技术异常当普通证明失败。
当前结果不完整，不能据此判定方法提升或退化。

## 4. 审计发现的runner问题（尚未修改冻结实现）

1. **迟到错误没有更新已落盘的有效性字段。** `run_task`在actor结束时算provider_valid，
   结算后driver只更新settled_usage。因此B组0e8d题仍标True，但最终ledger有一条
   unmetered/error请求；需要分开记录“超时的证明结果”与“最终provider证据不完整”。
2. **共享bridge中止被统计成普通未解。** A组9b9题自己的三次上游调用成功，
   所以provider_valid=True；但CLI因共享bridge返回409而提前退出。当前bucket仅查
   provider_valid，误把它放进normal_unsolved，缺少基础设施中止分类。
3. **V0_INVALID的文字原因不准确。** aa78题的fail_reason写成provider/terminal问题，
   实际二者均正常；是shell编辑协议检查失败。不能只读该字符串下结论。
4. **HTTP部分响应未保存。** 代码虽接住`IncompleteRead.partial`，但部分响应落盘
   分支要求`not capture_public_payloads`，本轮启用capture导致该分支不执行。
   异常请求目录只留request.json，无法从日志补回丢失的响应或实际费用。

这些是记账、分类、故障隔离和证据保存方面的问题，不是已知的skill内容问题。
要修改需创建新的执行/审计版本，不能原地改写冻结合同、已有结果和历史费用。

## 5. 费用与后续建议

v4已结算USD2.133143672；新增未知请求保守占用USD1.83904512；继承此前
中断的保守占用USD3.845267536。累计USD7.817456328/30，不是预算耗尽。
这些未知费用上界不是已确认实际消费。

建议保留已有结果，先修复最终分类与不完整响应保存，再经授权处理15项未启动
和1项提前技术中止。不默认重跑已用满600秒的超时，也不默认重跑模型自行违反
编辑协议的双通过项；否则会引入额外试次和选择偏差。不要从头重跑40次。

## 证据位置

运行根（相对于VERUS_SKILL_RUN_ROOT）：
`skillopt-verusage/card-organization-evaluation-20261012-v4/`。

- `audit/anomaly_audit.py`、`audit/anomaly_audit.json`：可复算检查和证据哈希。
- `provider_calls.jsonl`：request61610ee9cd504b649a4ab1940e5fce53。
- `evaluation.log`：上游chunked读取异常、共享保护、收尾退出。
- `episodes/dev_revised--aa78e84a931f703c7e9c/fidelity_audit.json`、`validation.json`、原始事件日志。
- `episodes/dev_revised--0e8d3ca5b02dc01ee01f/result.json`：先超时后上游失败。
- `episodes/dev_old--9b9f6ccef89db4103c7f/codex_events.raw.jsonl`：本地409与提前失败。

原始数据、封存test集、卡片和所有原始运行证据均未修改；本次没有付费模型调用。
