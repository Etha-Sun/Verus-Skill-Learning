# Initial skill parity

原三题step_0001均skill_present=true，workspace/SKILL.md为838字节，与仓库initial.md及本轮冻结副本SHA256一致：

`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`

原prompt要求“Read TASK.md. Read SKILL.md only if it exists.”。本轮使用同一project-profile runner，skill_file传入冻结initial.md，condition_skill_present=true，经原有单文件skill_text→workspace/SKILL.md装备链路落盘；不将skill额外拼接为hint、不改用skill目录形式。每次actor完成断言workspace技能SHA和manifest一致。没有强制actor阅读的新规则，也不保证模型每次实际遵守读文件指令；后续报告按工具记录检查。

仅装备方式及skill内容对齐；当前任务仍为checkpoint续跑＋hint，并保留新隔离设置，不声称完整运行环境与原始from-scratch逐位相同。所有hint重新生成，hint agent输入保持原设计，actor获得initial skill。旧blank实验不改。
