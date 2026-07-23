# Skill Distillation Paper Matrix

**核验日期：** 2026-07-22

**范围：** 与本项目的 `trace → diagnosis → reusable skill → verifier/live
evaluation → small-model transfer` 链条直接相关的代表性论文。正式接收池共 21 篇；
前沿池单列，不把 arXiv、under review 或 Workshop 写成主会中稿。

## 1. 统一术语

| 层级 | 定义 | 最低证据 |
|---|---|---|
| Trajectory reuse | 直接检索或拼接历史 episode | 原任务或相似任务可复现 |
| Local rationale | 针对一条 trace 的解释、修复建议 | 来源任务上有帮助 |
| Candidate skill | 去实例化的规则、workflow 或程序 | 声称可跨实例复用 |
| Validated skill | 带适用条件和 negative scope 的 candidate skill | 来源不重合的 probe tasks 上稳定增益 |
| Meta-skill | 产生、编辑、选择或合并 skill 的策略 | 独立 meta-validation 上改善 skill learner |
| Parametric distillation | 把 rationale/skill-conditioned behavior 内化进权重 | held-out live tasks 上改善准确率或效率 |

本报告把“真正的 skill distillation”限定为：经验被诊断和抽象为可复用单元，并经过
跨实例验证或被内化后在 held-out tasks 上产生收益。只生成一段总结属于 extraction，
不自动等于 learning。

## 2. 正式接收：parameterized reasoning / knowledge distillation

| # | 论文、作者、机构、正式状态 | 蒸馏机制与主要证据 | 被接收时的核心创新 | 强度 |
|---:|---|---|---|---|
| 1 | [STaR: Bootstrapping Reasoning With Reasoning](https://proceedings.neurips.cc/paper_files/paper/2022/hash/639a9a172c044fbb64175b5fad42e9a5-Abstract-Conference.html). Eric Zelikman, Yuhuai Wu, Jesse Mu, Noah D. Goodman. Stanford University; Google Research. NeurIPS 2022. | 生成 rationale，仅保留答对样本；答错样本在给定正确答案后 rationalize；联合答案和 rationale 迭代再训练。 | 建立 `generate → filter/rationalize → train → repeat` 的自举推理学习闭环，不只是一次性合成 CoT 数据。 | L5 |
| 2 | [Distilling Step-by-Step! Outperforming Larger Language Models with Less Training Data and Smaller Model Sizes](https://aclanthology.org/2023.findings-acl.507/). Cheng-Yu Hsieh, Chun-Liang Li, Chih-Kuan Yeh, Hootan Nakhost, Yasuhisa Fujii, Alexander Ratner, Ranjay Krishna, Chen-Yu Lee, Tomas Pfister. University of Washington; Google Cloud AI Research; Google Research. Findings of ACL 2023. | 教师生成 label+rationale；学生以 label prediction 和 rationale generation 的多任务目标训练。 | 将 rationale 明确变成比 hard label 更丰富的监督，并系统展示小模型和数据效率规律。 | L3–L4 |
| 3 | [SCOTT: Self-Consistent Chain-of-Thought Distillation](https://aclanthology.org/2023.acl-long.304/). Peifeng Wang, Zhengyang Wang, Zheng Li, Yifan Gao, Bing Yin, Xiang Ren. University of Southern California; Amazon. ACL 2023 Long, Outstanding Paper. | 答案条件化的 contrastive decoding 生成更支持答案的 rationale；学生增加 counterfactual reasoning objective。 | 同时处理“教师 rationale 不忠实”和“学生绕开 rationale”两个核心 failure mode，并以反事实依赖衡量忠实性。 | L4–L5 |
| 4 | [Symbolic Chain-of-Thought Distillation: Small Models Can Also “Think” Step-by-Step](https://aclanthology.org/2023.acl-long.150/). Liunian Harold Li, Jack Hessel, Youngjae Yu, Xiang Ren, Kai-Wei Chang, Yejin Choi. UCLA; Allen Institute for AI; Yonsei University; USC; University of Washington. ACL 2023 Long. | 对每题采样多条、多样的教师 rationales，训练 125M–1.3B 学生，并分析数量、过滤和多样性。 | 给出重要经验结论：小模型能学到 CoT，覆盖度和多样性比单条“最优” rationale 更关键。 | L3 |
| 5 | [Dialogue Chain-of-Thought Distillation for Commonsense-aware Conversational Agents](https://aclanthology.org/2023.emnlp-main.342/). Hyungjoo Chae, Yongho Song, Kai Tzu-iunn Ong, Taeyoon Kwon, Minjin Kim, Youngjae Yu, Dongha Lee, Dongyeop Kang, Jinyoung Yeo. Yonsei University; University of Minnesota. EMNLP 2023 Main. | 对不可靠教师做 QA-driven rationalization 与 dialogue/response alignment filtering，构建 DONUT 并训练 DOCTOR。 | 将 reasoning distillation 变成带噪教师下的领域数据生产和过滤系统，而非无条件接受教师解释。 | L3 |
| 6 | [Mentor-KD: Making Small Language Models Better Multi-step Reasoners](https://aclanthology.org/2024.emnlp-main.977/). Hojae Lee, Junho Kim, SangKeun Lee. Korea University, Department of Computer Science and Engineering / Department of Artificial Intelligence. EMNLP 2024 Main. | 在黑盒大教师和小学生之间训练 task-specific mentor；mentor 扩充 CoT 并给学生 soft labels。 | 用中间模型处理师生容量差距、教师数据不足和不可访问 logits，体现 student-aware adaptation。 | L3–L4 |
| 7 | [Skip-Thinking: Chunk-wise Chain-of-Thought Distillation Enable Smaller Language Models to Reason Better and Faster](https://aclanthology.org/2025.emnlp-main.610/). Xiaoshu Chen, Sihang Zhou, Ke Liang, Xiaoyu Sun, Xinwang Liu. National University of Defense Technology, College of Computer Science and Technology / College of Intelligence Science and Technology. EMNLP 2025 Main. | 将长 CoT 分为语义 chunks，分块训练并在推理时跳过已内化的中间块。 | 将蒸馏粒度从整条 rationale 改成 reasoning chunk，直接针对长 CoT 的梯度稀释和推理延迟。 | L4 |
| 8 | [CODI: Compressing Chain-of-Thought into Continuous Space via Self-Distillation](https://aclanthology.org/2025.emnlp-main.36/). Zhenyi Shen, Hanqi Yan, Linhai Zhang, Zhanghao Hu, Yali Du, Yulan He. King’s College London; The Alan Turing Institute. EMNLP 2025 Main. | 同一模型联合学习 explicit/implicit CoT，在答案前指定 token 的 hidden states 上自蒸馏；把自然语言 CoT 压进连续空间。 | 将“更短文本”提升为“连续思维内化”，在 GPT-2 规模匹配 explicit CoT 并报告 3.1× compression。 | L4 |
| 9 | [DART: Distilling Autoregressive Reasoning to Silent Thought](https://aclanthology.org/2025.emnlp-main.256/). Nan Jiang, Ziming Wu, De-Chuan Zhan, Fuming Lai, Shaobing Lian. Nanjing University; Tencent Inc. EMNLP 2025 Main. | 训练时使用 CoT/ST 双路径，以 Reasoning Evolvement Module 对齐 hidden states；部署只运行少量非自回归 silent-thought tokens。 | 直接改变推理计算图，以非自回归 latent tokens 解决显式 CoT 延迟，而非只压缩文本长度。 | L4 |

### 这一支的演化

`答案监督 → rationale 监督 → 自举 rationale → 忠实/反事实 rationale → 师生容量适配
→ 功能性 chunk → continuous/silent thought`。因此，今天仅做“用大模型生成长 CoT，
再 SFT 小模型”通常只有 L2；新的工作至少需要解决因果贡献、忠实性、student capacity
或推理计算成本中的一个硬问题。

## 3. 正式接收：textual memory / reusable workflow

| # | 论文、作者、机构、正式状态 | Skill 载体与更新 | 被接收时的核心创新 | 强度 |
|---:|---|---|---|---|
| 10 | [Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html). Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao. Northeastern University; MIT; Princeton University. NeurIPS 2023. | 环境反馈和结果被转为 verbal reflection，写入 episodic memory，下一轮重试注入；不更新权重。 | 把数值梯度替换为语言形式的 semantic feedback，建立行动—反馈—反思—再行动闭环。 | L5 |
| 11 | [ExpeL: LLM Agents Are Experiential Learners](https://ojs.aaai.org/index.php/AAAI/article/view/29936). Andrew Zhao, Daniel Huang, Quentin Xu, Matthieu Lin, Yong-Jin Liu, Gao Huang. Tsinghua University, BNRist / Department of Automation / Department of Computer Science and Technology. AAAI 2024 Technical Track. | 比较 failure→success trials 与多条成功 trajectories，抽取 cross-task insights；支持 ADD、EDIT、UPVOTE、DOWNVOTE，并检索 demonstrations。 | 从单任务反思推进到跨任务归纳和 insight 生命周期管理，使经验可累计而非一次性重试。 | L4 |
| 12 | [Agent Workflow Memory](https://proceedings.mlr.press/v267/wang25bx.html). Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, Graham Neubig. Carnegie Mellon University; MIT. ICML 2025. | 从成功 agent trajectories 中抽取带 slots 的可参数化 workflow；按任务选择性注入；支持 offline/online induction。 | 把 memory 单位从 episode 改成可复用 procedural workflow，并验证跨任务、网站和分布间迁移。 | L4 |
| 13 | [ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory](https://openreview.net/forum?id=jL7fwchScm). Siru Ouyang, Jun Yan, I-Hung Hsu, Yanfei Chen, Ke Jiang, Zifeng Wang, Rujun Han, Long T. Le, Samira Daruki, Xiangru Tang, Vishy Tirumalashetty, George Lee, Mahsan Rofouei, Hangfei Lin, Jiawei Han, Chen-Yu Lee, Tomas Pfister. UIUC; Google Cloud AI Research / Google Cloud AI; Yale University. ICLR 2026 Poster. | 对成功和失败经验做 self-judgment，蒸馏结构化 reasoning memories；与 memory-aware test-time scaling 形成循环。 | 将 memory learning 与 inference-time scaling 统一：更多探索产生更好对比经验，更好 memory 又引导后续探索。 | L4 |

### 这一支的演化

`episode → task-local reflection → cross-task insight → parameterized workflow →
structured reasoning strategy`。决定研究强度的不是总结文风，而是适用条件、参数化、
选择性调用、冲突处理和 held-out utility。

## 4. 正式接收：executable tool / programmatic skill

| # | 论文、作者、机构、正式状态 | Skill distillation 机制 | 被接收时的核心创新 | 强度 |
|---:|---|---|---|---|
| 14 | [Toolformer: Language Models Can Teach Themselves to Use Tools](https://proceedings.neurips.cc/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html). Timo Schick, Jane Dwivedi-Yu, Roberto Dessì, Roberta Raileanu, Maria Lomeli, Eric Hambro, Luke Zettlemoyer, Nicola Cancedda, Thomas Scialom. Meta AI Research; Universitat Pompeu Fabra. NeurIPS 2023. | 模型自行提出 API calls，执行后按 LM loss 改善过滤训练样本，再 SFT 到参数中。 | 自监督发现何时调用、调用什么、参数是什么及如何使用返回值；验证信号不是 LLM 自评。 | L5 |
| 15 | [CREATOR: Tool Creation for Disentangling Abstract and Concrete Reasoning of Large Language Models](https://aclanthology.org/2023.findings-emnlp.462/). Cheng Qian, Chi Han, Yi R. Fung, Yujia Qin, Zhiyuan Liu, Heng Ji. Tsinghua University; UIUC. Findings of EMNLP 2023. | 针对任务创建、执行和修正工具，把抽象求解逻辑固化为代码，再处理具体实例。 | 从使用已有工具推进到按题创建新工具，并显式分离 abstract reasoning 与 concrete computation。 | L4 |
| 16 | [Voyager: An Open-Ended Embodied Agent with Large Language Models](https://openreview.net/forum?id=ehfRiF0R3a). Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi “Jim” Fan, Anima Anandkumar. NVIDIA; Caltech; UT Austin; Stanford; Arizona State University. TMLR 2024. | 自动课程生成任务；把成功行为写成可执行代码 skill；结合环境错误、自验证和迭代修复持续扩库。 | 把 curriculum、环境反馈、可组合代码库和 lifelong learning 组成开放世界闭环。 | L5 |
| 17 | [Large Language Models as Tool Makers](https://proceedings.iclr.cc/paper_files/paper/2024/hash/ed91353f700d113e5d848c7e04a858b0-Abstract-Conference.html). Tianle Cai, Xuezhi Wang, Tengyu Ma, Xinyun Chen, Denny Zhou. Google DeepMind; Princeton University; Stanford University. ICLR 2024. | 强模型一次性创建并缓存 Python tools，弱模型重复调用；把创建成本在后续实例上摊销。 | 将 strong-maker/weak-user 分工和 functional cache 明确化，直接回答能力迁移与 amortized cost。 | L4 |
| 18 | [CRAFT: Customizing LLMs by Creating and Retrieving from Specialized Toolsets](https://proceedings.iclr.cc/paper_files/paper/2024/hash/af31604708f3e44b4de9fdfa6dcaa9d1-Abstract-Conference.html). Lifan Yuan, Yangyi Chen, Xingyao Wang, Yi R. Fung, Hao Peng, Heng Ji. University of Illinois Urbana-Champaign. ICLR 2024. | 从训练题生成 code solutions，经执行验证、抽象和去重形成大型专用 toolset；推理时多视角检索。 | 将单题工具创建扩展为可规模化的 domain toolset construction，并系统处理可复用性、正确性和检索。 | L4 |
| 19 | [ReGAL: Refactoring Programs to Discover Generalizable Abstractions](https://proceedings.mlr.press/v235/stengel-eskin24a.html). Elias Stengel-Eskin, Archiki Prasad, Mohit Bansal. University of North Carolina at Chapel Hill. ICML 2024. | 将已有 primitive programs 重构为共享 functions；通过执行反复验证、修正和剪枝；无梯度。 | 用“保持程序行为的重构”做 library learning，得到跨五域可复用且执行可验证的抽象。 | L4 |
| 20 | [TroVE: Inducing Verifiable and Efficient Toolboxes for Solving Programmatic Tasks](https://proceedings.mlr.press/v235/wang24az.html). Zora Zhiruo Wang, Graham Neubig, Daniel Fried. Carnegie Mellon University. ICML 2024 Poster. | 在解题过程中使用、增长并周期性裁剪 toolbox；不训练模型，工具和答案均可执行验证。 | 同时优化工具库正确性、简洁性和可人工验证性；把 skill lifecycle 中的 trimming 变成核心机制。 | L4 |
| 21 | [Inducing Programmatic Skills for Agentic Tasks](https://openreview.net/forum?id=lsAY6fWsog). Zora Zhiruo Wang, Apurva Gandhi, Graham Neubig, Daniel Fried. Carnegie Mellon University. COLM 2025. | Web agent 在线诱导、验证和调用 program-based skills；将 primitive actions 组合成高层操作并跨网站迁移/更新。 | 证明程序表示相对文本 skill 的验证保证和执行效率优势，并覆盖在线适应、复用与不兼容更新。 | L4 |

### 这一支的共同规律

代码不是天然更高级；它的论文价值来自三个属性：可执行验证、精确复用和可组合性。
仅把 advice 改写成 Python 不够。强工作通常还包含生成、验证、去重/裁剪、检索、版本
更新或 strong-to-weak amortization 中至少一项新机制。

## 5. 前沿池：截至核验日不是已正式接收的主会论文

| 论文、作者、机构、状态 | 方法与对本项目的意义 |
|---|---|
| [Implicit Chain of Thought Reasoning via Knowledge Distillation](https://arxiv.org/abs/2311.01460). Yuntian Deng, Kiran Prasad, Roland Fernandez, Paul Smolensky, Vishrav Chaudhary, Stuart Shieber. Harvard University; Microsoft Research. arXiv 2023；曾提交 ICLR 2024，未作为正式接收计入。 | 把显式 CoT 蒸馏进跨层 hidden states，使推理从“横向生成 token”变成“纵向内部计算”。是 token-efficient internalization 的早期直接先例。 |
| [Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills](https://arxiv.org/abs/2603.25158). Jingwei Ni, Yihao Liu, Xinpeng Liu, Yutao Sun, Mengyu Zhou, Pengyu Cheng, Dexin Wang, Erchao Zhao, Xiaoxi Jiang, Guanjun Jiang. Alibaba Qwen Large Model Application Team; ETH Zürich; University of Zurich; Peking University; Zhejiang University. arXiv 2026. | 并行分析成功/失败 trajectories，再层次合并为 portable skill directory；强调跨模型、跨规模和 OOD 转移。最接近“广 trace 汇总为 declarative skills”的强基线。 |
| [SkillOpt: Executive Strategy for Self-Evolving Agent Skills](https://arxiv.org/abs/2605.23904). Yifan Yang, Ziyang Gong, Weiquan Huang, Qihao Yang, Ziwei Zhou, Zisu Huang, Yan Li, Xuemei Gao, Qi Dai, Bei Liu, Kai Qiu, Yuqing Yang, Dongdong Chen, Xue Yang, Chong Luo. Microsoft; Shanghai Jiao Tong University; Tongji University; Fudan University. arXiv 2026. | 把外部 skill document 当可训练状态：bounded add/delete/replace、held-out gate、rejected-edit buffer、slow/meta update。直接抬高“文本 skill optimizer”的基线。 |
| [SkillRL: Evolving Agents via Recursive Skill-Augmented Reinforcement Learning](https://arxiv.org/abs/2602.08234). Peng Xia, Jianwen Chen, Hanyang Wang, Jiaqi Liu, Kaide Zeng, Yu Wang, Siwei Han, Yiyang Zhou, Xujiang Zhao, Haifeng Chen, Zeyu Zheng, Cihang Xie, Huaxiu Yao. University of North Carolina at Chapel Hill; University of Chicago; UC San Diego; NEC Labs America; UC Berkeley; UC Santa Cruz. arXiv 2026；ICLR 2026 MemAgents Workshop Oral，未计入主会接收池。 | 从经验构建分层 SkillBank，按 general/task-specific 检索，并让 skill library 与 RL policy 共同演化。是“外置后内化”的直接竞争线。 |
| [EvoSkill: Automated Skill Discovery for Multi-Agent Systems](https://arxiv.org/abs/2603.02766). Salaheddin Alzubi, Noah Provenzano, Jaydon Bingham, Weiyuan Chen, Tu Vu. Sentient; Virginia Tech. arXiv 2026；论文标注 preprint/work in progress. | 从失败分析产生或修改完整 skill folders，以 held-out validation 和 Pareto frontier 选择冻结模型的 agent programs。对“仅失败驱动的 skill evolution”构成强系统基线。 |
| [MetaSkill-Evolve: Recursive Self-Improvement of LLM Agents via Two-Timescale Meta-Skill Evolution](https://arxiv.org/abs/2607.05297). Zefeng Wang, Minxi Yan, Jinhe Bi, Sikuan Yan, Volker Tresp, Yunpu Ma. LMU Munich; The Chinese University of Hong Kong; Munich Center for Machine Learning; MemAgents Lab. arXiv 2026. | fast loop 更新 task skill，slow loop 更新控制 Analyzer/Retriever/Allocator/Proposer/Evolver 的 meta-skill。与本项目的 two-timescale 设想高度重叠，因此“一个会自改的 meta-prompt”已不够新。 |

## 6. 正式接收论文到底靠什么创新

| 可观察的创新类型 | 代表论文 | 审稿价值 |
|---|---|---|
| 新学习闭环 | STaR, Reflexion, Voyager | 改变经验如何变成后续能力，而不是替换单个 prompt |
| 命中关键 failure mode | SCOTT, Mentor-KD, Skip-Thinking | 明确诊断忠实性、student capacity 或冗余推理，并给专门机制 |
| 改变学习单位 | AWM, ReGAL, CODI/DART | episode→workflow、program→library abstraction、text CoT→latent computation |
| 外部验证信号 | Toolformer, CRAFT, ReGAL, TroVE, ASI | 用 loss、程序执行或环境 verifier 选择技能，而非 LLM 自评 |
| 完整生命周期 | ExpeL, TroVE, ReasoningBank | 生成之外还处理更新、投票、裁剪、检索、累积或 test-time scaling |
| 新迁移/效率规律 | Distilling Step-by-Step, SCoTD, LATM | 即使算法不极复杂，也以多设置证明可复用的新规律 |

### 非官方创新强度标尺

| 层级 | 典型贡献 | 现实发表判断 |
|---|---|---|
| L2 | 新 extraction prompt、多 agent critique、Markdown skill、embedding retrieval、单 benchmark 提升 | Workshop/Demo/系统报告更自然；单独支撑主会风险高 |
| L3 | 明确领域 failure mode；针对性机制；多个数据集或模型稳定复现 | Findings、应用型主会或领域会议具有竞争力 |
| L4 | 新 skill 表示、验证/credit objective、student-aware compiler、可执行/可组合更新；有 OOD 与强基线 | 主会方法论文的合理目标 |
| L5 | 新自举或持续学习范式，能改变领域如何定义学习单位和反馈闭环 | 顶会强稿、Oral/Outstanding 候选，但需要广泛且严密证据 |

**经验阈值：**正式接收的强工作通常至少改变 `学习单位、验证信号、更新机制`
中的一个，L4 以上往往改变两个。没有任何会议要求形式上的 L4；但在 2026 年拥挤的
agent skill 方向，单纯 trajectory summarization 已很难形成主会级方法贡献。

## 7. 元数据说明

- 作者和机构取论文发表时署名，非作者当前任职。
- 会议状态优先使用官方 proceedings、ACL Anthology、PMLR 或 OpenReview venue
  decision；项目页和 arXiv 只补充作者、方法或前沿状态。
- SCOTT 的 Outstanding Paper 由 Amazon Science 的 ACL 2023 官方项目报道交叉核验。
- ExpeL 计作 AAAI 2024 Technical Track；未把未核实的 “Oral” 标签写入。
- 本矩阵不把 citation count 当创新强度，也不以最终模型分数反推论文质量。
