# 第二轮 B/C 续跑记录

## 当前状态

2026-10-13，用户在得知第二轮未完成后明确要求先补跑第二轮。
服务器服务 `verus-selective-eval-20261013-v2.service` 已启动并核实为
active/running，初始 PID2170368，Linger=yes、Restart=no。
首轮检查已有6条 provider 记录，两次补跑 actor 已启动。
这是启动记录，不是最终完成声明；请以实时 progress、日志和最终 summary 为准。

运行目录位于外部运行根下：
`skillopt-verusage/selective-reference-evaluation-20261013-v2/`。

## 为什么需要续跑

原 v1 在28/40次尝试后因 `IncompleteRead(125251 bytes read)` 停止派发。
provider 已排空、原输入哈希一致；不是费用达到上限。
此前安排的单题补跑服务要求原40次干净完成，因此安全检查拒绝执行，未付费补跑。
其 `waiting_for_parent` 状态文件未随异常更新，不能当成服务仍存活的证据。
旧主服务与单题补跑服务均已核实 inactive；本次续跑取代旧单题补跑计划。

## 冻结清单

保留25个原结果，包括正常超时；新运行15次：

| 类型 | 数量 | 处理 |
|---|---:|---|
| 尚未启动 | 12 | 按原冻结清单运行 |
| 用户确认误杀的 B `3f17ea7c76a0ce99c098` | 1 | 从原始任务起点补跑 |
| API 响应中断的 C `9b9f6ccef89db4103c7f` | 1 | 从原始任务起点补跑 |
| 受共享 bridge 停止连带中断的 B `6a7283f1b8a3f1d862db` | 1 | 从原始任务起点补跑 |

不重跑正常失败/超时、不择优、不重启整轮。保留全部旧尝试及其费用。
固定 validation20、每组每题一次的计分矩阵仍为40格；若本次全部完成，
实际物理尝试为43次（原28+新15），其中3次技术中断不进入最终方法比较。

## 配置与验证

- 同一 B 整篇 reference / C selective-v2 导航与按需读取组合比较。
- DeepSeek V4 Pro/max，600秒，2并发，原TASK/Executive、技能正文、工具权限。
- 沿用两组相同本机 Verus；与 Yuechun 历史二进制哈希差异仍披露。
- 冻结 actor 与 provider transport 不修改；新增 wrapper 仅限定续跑清单和汇总。
- 24项离线测试通过，覆盖准确补跑清单、禁止超时重跑、合并不覆盖原结果。
- 真实 systemd 零API预检通过：B37/C146读取检查、Verus/Lynette、隔离与 Codex0.147.0。
- 审核凭据是用户授权下的 coding-assistant 配置审查，不冒充独立模型审核。

## 费用与最终输出

原 $30 是两阶段合计上限，不增加新预算。新 guard 继承保守占用
$3.901802784 = 已知估算 $2.062757664 + 未知调用预留上限 $1.839045120。
未知调用预留不是确认账单。原 budget 与账本不覆盖。

完成后生成 `combined/report.json`、`combined/episodes.csv` 和
`combined/summary.json`，保留来源哈希与3次排除尝试路径。
计分集资源与全部物理尝试花费分别报告；不把未知 token/费用记为零。
如再次发生 provider 故障，仍停止派发等待审查，不无限自动重试。

此前请求的汇报表待第二轮完整性核验后制作：第一轮 A/B、第二轮 B/C 四臂。
原始/封存数据、原实验结果、已冻结技能和执行代码均未修改。
