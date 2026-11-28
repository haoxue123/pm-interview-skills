# AI 面试准备专家 · 技术方案文档（Technical Design）

> **版本**：v0.1（草案）
> **日期**：2026-07-25
> **作者**：WorkBuddy
> **调研窗口**：近半年（2026-01 ～ 2026-07）
> **资料依据**：联网检索的 18 个高质量资源（9 开源项目 + 5 篇 arXiv 论文 + 4 篇 LLM-as-Judge 技术参考，见附录 A）
> **上下游关系**：本方案是 `产品经理面试准备专家_产品文档.md`（PRD）的**技术落地版**，并复用 `产品经理面试真实考点蒸馏库.md`（v3，L0–L5）作为知识内核。目标：据此可开发一个「面试准备 Skill」。

---

## 0. 文档信息

| 项 | 内容 |
|---|---|
| 产品目标 | 从第一性原理构建**可成长**的面试准备系统：不押题，建结构；每次面试经验反哺系统成长 |
| 技术定位 | 以 LLM + RAG + 状态机为核心，优先本地隐私部署，可选云端提质的混合架构 |
| 交付形态 | 一套挂载知识库的 Skill（对话式触发）+ 可本地运行的轻量服务 |
| 设计红线 | 存「原理/模式/反模式/人设状态」而非「题目」；L5 否决层持续收割过度预测 |

---

## 1. 调研综述：18 个高质量资源（近半年）

> 检索日 2026-07-25。资源编号（#1–#18）在后续章节引用。日期依据：GitHub 最后提交日期、arXiv 提交编号（2601=2026-01 … 2606=2026-06）、技术文章 2026 年发布。

### 1.1 开源项目（9 个）

**#1 TakPrince/LLM-Based-Technical-Interview-Simulator**（2026-01-04）
- 核心方案：Streamlit + Ollama 本地推理的 Mock 技术面试模拟器，候选人建档（经历/技能/目标岗/公司）后由 AI 逐题提问，固定轮次后给 1–10 总分与结构化反馈。
- 架构思路：角色化 Prompt（system/user/assistant）严格分离「面试模式（只提问）」与「反馈模式（只评分）」，用 token 上限（num_predict）控速；会话状态由 Streamlit session_state 管理。
- 技术点：角色 Prompt 隔离防 AI 越俎代庖；Ollama 本地模型（Phi-3）零 API 成本；评分与提问解耦。

**#2 hi2brain/second-brain**（2026-06-21）
- 核心方案：隐形桌面 AI 面试 Copilot，后台实时听面试、基于本人简历 + JD 生成第一人称回答建议。
- 架构思路：Electron 桌面端 + Groq 极速 Llama-3 推理 + Whisper-large-v3 语音转写；简历/JD/API Key 仅存本地 localStorage（隐私优先）；多语言本地化。
- 技术点：Whisper 实时转写 → 对话上下文 + 简历/JD 检索 → 建议生成，毫秒级；隐形模式（可最小化）；隐私-first 设计。

**#3 LilRind/interview-guide**（2026-01-14）
- 核心方案：集简历智能分析、AI 模拟面试、知识库 RAG 检索于一体的智能面试辅助平台（Java 技术栈，适合学习）。
- 架构思路：Spring Boot 4 + Java 21 + Spring AI + PostgreSQL + pgvector + Redis；简历分析/知识库向量化/报告生成用 **Redis Stream 异步处理**（PENDING→PROCESSING→COMPLETED/FAILED 状态机），前端轮询。
- 技术点：pgvector 向量库；Tika 简历解析（已优化去图片引用）；异步消息驱动解耦；状态机流转。

**#4 AloysiusSundar/TheodoreTheChatBot**（2026-01-21）
- 核心方案：对话式 AI 招聘助理，按候选人角色/技术栈逐步收集画像并定制技术问题。
- 架构思路：Streamlit + SQLite + 本地 Ollama（mistral-small）；显式 **phase-based 状态机**（profile→technical→done）；session_state 管状态；全本地推理无外部 API。
- 技术点：阶段化状态机；轻量 SQLite 持久化；本地推理可离线。

**#5 yang66/ai-interview-assistant**（2026）
- 核心方案：AI 驱动的面试问题生成 + 报告生成系统，自动分析 JD 与简历，为每场面试定制问题，面试后按对话生成总结报告（含能力维度 1–5 评分 + 雷达图）。
- 架构思路：FastAPI 后端 + Streamlit 前端 + MySQL（SQLAlchemy/Alembic）+ LangChain + OpenAI；JD 分析 → 简历解析 → 问题生成 → 多轮对话记录 → 报告生成（能力维度评分 + 雷达图）完整生命周期。
- 技术点：能力维度 1–5 量化评分 + 雷达图可视化；多轮对话与预生成问题关联；Docker Compose 一键起服务。

**#6 leoin2012/ResumeRoaster**（2026）
- 核心方案：基于 RAG 的智能模拟面试，AI 扮演刁钻面试官，依据简历内容深度技术追问（含缓存穿透/击穿/雪崩等连环追问示例）。
- 架构思路：微服务 + Redis 缓存；Embedding 双选（本地 sentence-transformers/MiniLM 免费中文 / DeepSeek API）；config.ini 与 template 分离防 Key 泄漏。
- 技术点：RAG 简历检索驱动追问；多级缓存；本地 Embedding 零成本中文支持。

**#7 huihuihengiang/Cluely-interview（InterviewBot）**（2026）
- 核心方案：PyQt 透明界面面试辅助，GPT 对话模拟 + 百度语音识别 + OCR + RAG 知识库（Excel 导入）+ 简历个性化回答。
- 架构思路：纯 Python + PyQt；OCR（Tesseract）+ 语音识别 + 多线程保稳定；Excel 构建 Q&A 知识库，可与大模型并列检索。
- 技术点：截图识别编程题返回代码；知识库可等同大模型效果；全 Python 低门槛（作者自述稳定性一般，作思路参考）。

**#8 llx9826/llm-interview-coach**（2026）
- 核心方案：开源（MIT）AI 练习伙伴，按目标岗/题型（行为/技术/情景）生成个性化练习会话并给反馈。
- 架构思路：**干净模块化**，可插拔多模型后端（本地/云端）；易于扩展题库与反馈风格。
- 技术点：MIT 许可可商用；模型后端可切换；早期项目文档偏中文、缺评测指标（局限性参考）。

**#9 wangzhongyang Go AI 面试助手**（2026，Claude Code 3 天写成）
- 核心方案：程序员专属 AI 智能面试助手，Go + Eino 大模型 Agent 框架。
- 架构思路：**模块化分层**——简历解析模块 / 面试 Agent 模块 / 报告生成模块 / 用户管理模块解耦；预留多模型、自定义题库、新场景接口；纯本地隐私部署。
- 技术点：Eino Agent 多轮对话 + 上下文记忆 + 智能追问 + 意图识别；Go 高并发低延迟；私有化部署护隐私。

### 1.2 研究论文（5 篇 arXiv）

**#10 Rubric-ARROW**（arXiv:2605.29156，2026-05）
- 核心方案：让 LLM「考官」自我进化的评分框架，解决开放任务打分不准。
- 架构思路：「出题人」（评分细则生成器）+「判卷员」（条件判断模型）双人搭档，两阶段成长；把评分细则拆成可逐条检查的标准，**修复了「满足/不满足」二元细则导致不同质量答案同分的缺陷**（用更细粒度刻度）。
- 技术点：细则自生成 + 条件判断分离；细粒度 rubric；越用越准的自进化闭环。

**#11 Interview-Informed Generative Agents**（arXiv:2603.29890，CHI 2026）
- 核心方案：用深度工作流访谈构建个性化生成式 Agent，模拟用户对新产品概念的反馈。
- 架构思路：基于真实访谈 grounding 的个性化 Agent；与真人回应做分布校准对比。
- 技术点：结论「分布校准但个体不精确」——Agent 适合早期概念筛选/迭代（population 级），**不能替代个体级洞察**。对「能力画像」模块有方法论启示：用 Agent 模拟面试官可行，但需标注置信区间。

**#12 TCR：Evaluating Multi-turn Human-AI Interaction**（arXiv:2605.18660，2026-05）
- 核心方案：用教育类 LLM 助手为例，提出评估多轮人机交互的结构化框架。
- 架构思路：TCR 三维度——**Transparency（透明）/ Consistency（跨轮一致）/ Refinement（迭代精炼）**，配结构化评估 Prompt 与交互样例。
- 技术点：多轮交互不能只看 aggregate 指标；强调一致性（同问题多轮回答不自相矛盾）与迭代精炼能力——直接指导「模拟面试对话」与「回答评估」模块。

**#13 PeerRank**（arXiv:2602.02589，2026-02）
- 核心方案：完全自主的端到端 LLM 评估框架，模型自生成任务、带实时网络 grounding 作答、互评并聚合成相对排名，无需人工/黄金答案。
- 架构思路：多 Agent 对称参与（出题人/作答人/评估人），web-grounded 回答 + 偏见控制（去 position/identity 偏见）；12 个商用模型 × 420 题大规模研究。
- 技术点：去偏见 peer review；web grounding 防幻觉；相对排名稳健且与人评 Elo 相关——可作为「回答评估」的无参考答案评测参考。

**#14 LLM 会议轮次转换 / 下一发言人预测**（arXiv:2606.17542，2026-06）
- 核心方案：评估 LLM 在多方对话中处理受话人、轮次转换、下一发言人预测的能力。
- 架构思路：三任务评估框架（受话人检测/轮次转换预测/下一发言人预测），对比监督模型、文本 LLM、多模态 LLM、人类。
- 技术点：对话上下文对轮次预测至关重要；缺乏多模态时 LLM 在「下一发言人」上超人类——对话上下文建模对「模拟面试多轮状态」有参考。

### 1.3 LLM-as-Judge 技术参考（4 篇）

**#15 QASkills LLM-as-a-Judge 指南 2026**
- 核心方案：pointwise（单样本 1–5）/ pairwise（A vs B）/ reference-based（对照金标）三模式；rubric 设计、偏见缓解、Cohen's Kappa 人评一致性、成本权衡。
- 技术点：点式易接入 CI 闸门但易漂移；配对需交换顺序取平均； Judge 模型应强于被评模型。

**#16 futureagi LLM Judge Prompting 2026**
- 核心方案：Judge Prompt 五要素——角色定义 / 数值锚定 rubric（1–4 带每档具体行为）/ 校准样例（每档 1 例降噪 30–50%）/ CoT 先推理后打分（提 10–20% 人评一致）/ 结构化 JSON 输出（score+reasoning+confidence+flags）。
- 技术点：rubric 数值锚定是关键契约；校准样例降本降噪；CoT 提升一致性；JSON 使可解析。

**#17 CSDN LLM 裁判五维评分**
- 核心方案：准确性 / 指令遵循 / 逻辑性 / 完整性 / 流畅性 五维 1–5 评分 JSON 输出；安全场景第五维替换为 Safety。
- 技术点：位置偏见（交换顺序）、长度偏见（ rubric 注明「长度不影响分」）、自增强偏见（换模型族）的缓解清单。

**#18 callsphere LLM-as-Judge Agent 评估**
- 核心方案：Rubric 代码化（Correctness/Completeness/Clarity 各档行为锚定）；对人标子集做 Spearman 校准；async 批量并发评测；按场景加权（客服 correctness 0.5 / 创意 clarity 0.6）。
- 技术点：rubric 必须行为锚定；校准必须有；并发评测；加权总分。

---

## 2. 整体架构设计

### 2.1 设计原则（第一性原理）
1. **存原理不存题目**：知识内核 = L0–L5（原始/萃取/原理/模式/人设/否决），原子单位是「原理+模式+反模式+状态」，不是题。
2. **可成长反哺**：每次上传新面试都走「解析→打标签→更新人设状态机→写模式库→预测偏差回流否决层→版本+1」。
3. **本地隐私优先，云端提质可选**：简历/面试记录默认本地；提质时可切云端强模型，但 Key 不落盘明文。
4. **评估可校准**：任何打分走 LLM-as-Judge +  rubric 锚定 + 偏见缓解 + 人标校准子集。

### 2.2 系统分层架构
```
┌──────────────────────────────────────────────────────────┐
│ 应用层（Skill 对话触发 / 可选 Web UI / 可选桌面端）      │
├──────────────────────────────────────────────────────────┤
│ 引擎层                                                          │
│  M4 模拟面试 Agent ──多轮状态机──┐                        │
│  M3 问题生成 ──┐              │                        │
│  M5 回答评估(LLM-Judge) ─┤              │                        │
│  M6 能力画像 ───────────────┴─→ 结构化输出          │
│  M7 反哺迭代（否决层/触发规则/版本+1）                    │
├──────────────────────────────────────────────────────────┤
│ 知识层（L0–L5，挂载 蒸馏库v3）                          │
│  L0 原始(append-only)│L1 萃取(schema)│L2 原理(5维)    │
│  L3 模式(GOOD/BAD)│L4 人设(A–F状态机)│L5 否决(面不到)│
│  + 向量库(pgvector/Chroma)：简历/知识库/标杆案例嵌入    │
├──────────────────────────────────────────────────────────┤
│ 接入层                                                          │
│  M1 简历解析(Tika/LLM) │ M2 知识库RAG │ ASR(可选)      │
│  模型后端：本地 Ollama(Phi-3/MiniLM) ⇄ 云端(GPT-4o/Gemini/DeepSeek) │
└──────────────────────────────────────────────────────────┘
```
> 架构思路综合自 #3（Spring AI + pgvector + Redis Stream 异步状态机）、#4/#1（phase/session 状态机）、#9（模块化分层解耦）、#5（FastAPI+前端+向量+生命周期）。

### 2.3 与既有资产的关系
- 本方案 = PRD 的**技术实现**；L0–L5 直接复用 `产品经理面试真实考点蒸馏库.md` v3（6 真实 + 3 标杆，5 维度，A–F 人设）。
- 模块 M1–M7 一一对应 PRD 的「思维框架/反哺流水线/评估迭代」，此处给出可落地的技术选型与接口。

---

## 3. 核心模块划分与实现要点

### M1 简历解析模块（Resume Parsing）
- **职责**：把 PDF/Word/文本简历转成结构化 JSON（姓名/经历/项目/技能/教育/时间线），为问题生成与个性化回答供数。
- **技术选型**：① 轻量：LLM 直接抽取（参考 #5 的 AI-powered resume parsing）；② 精准：Apache Tika 抽取文本（#3 已验证去图片引用）+ LLM 结构化（schema 约束 JSON 输出）。
- **实现要点**：
  - 定义 Pydantic schema：`projects[]: {name, role, actions[], metrics[], tech[], decisions[]}`——**每个项目强制抽「数据口径」与「关键决策」**，直击用户人设 B（数据口径经不起追问）。
  - 中文分词用 Jieba（#7 思路）提升字段切分准确率。
  - 隐私：解析在本地完成，产物存本地向量库，不传第三方。

### M2 知识库与 RAG 模块（Knowledge + RAG）
- **职责**：把 L0–L5 + 用户项目 + 标杆案例向量化，供问题生成/模拟面试/个性化回答检索。
- **技术选型**：向量库见 §4.2；Embedding 见 §4.1（本地 MiniLM 中文免费 / 云端 text-embedding-3-small）。
- **实现要点**（综合 #3 pgvector、#6 RAG 追问、#7 Excel KB）：
  - 切片策略：按「维度 + 标签」元数据过滤检索，而非纯向量最近邻，提升召回相关性。
  - 受控删除（参考 #4 二次确认、#6 config 分离）：知识库条目删除需二次确认，防误删。
  - 标杆案例 GOOD/BAD 单独建集合，模拟面试时按「反模式」检索做避坑提示。

### M3 面试问题生成模块（Question Generation）
- **职责**：依据 JD + 简历 + 目标岗，生成**贴合岗位且能深挖**的问题集（非通用题库）。
- **技术选型**：LLM + RAG（检索 L2 原理层 5 维度 + L3 模式层 + L5 否决层）。
- **实现要点**（综合 #5 JD分析+问题生成、#6 RAG简历追问、#11 grounding Agent）：
  - Prompt 模板：`基于 JD 的 X 个维度 + 候选人简历的 Y 个项目 + 该岗真实高频考点(L2)，生成 N 道可深挖问题，每道标注考察维度与预期追问链`。
  - **否决层约束**：生成时显式排除 L5「面不到的问题」，避免退化成押题。
  - 输出结构：`{dimension, question, followups[], intent}` 便于 M5 评估对齐。

### M4 模拟面试对话模块（Interview Agent / Multi-turn）
- **职责**：扮演面试官，按状态机逐题提问、维持上下文、做连环深挖。
- **技术选型**：Agent 框架（LangChain / Eino，见 §4.3）+ 多轮状态机（#4 phase 状态机、#14 对话上下文建模、#12 多轮一致性与精炼）。
- **实现要点**：
  - 状态机：`INTRO → PER_PROJECT(deep-dive) → BEHAVIOR → CASE → REVERSE_Q → FEEDBACK`，每态可跳。
  - **深挖链**：每答完一题，检索该项目的「数据口径/决策细节」做追问（仿 #6 缓存穿透连环追问），直击真实性。
  - 一致性（TCR #12）：同一候选人信息跨轮不自相矛盾；CoT 记忆摘要压缩长上下文。
  - 语气：参考 GOOD 标杆「场景化、不官方」，规避 BAD-1「过度 personal/压力」与用户人设 D（官方）。

### M5 回答评估模块（Answer Evaluation / LLM-as-Judge）
- **职责**：对候选人回答给可解释、可校准的多维评分与改进建议。
- **技术选型**：LLM-as-Judge（#15–#18），**绝不**用二元 rubric（#10 教训）。
- **实现要点**：
  - **Rubric 锚定**（#16/#18）：每维度 1–5 带行为锚定，例：
    ```
    逻辑性: 5=结论先行+假设驱动+数据支撑; 3=部分碎片化; 1=凭感觉无框架
    ```
  - **五维评分**（#17）：准确性 / 指令遵循 / 逻辑性 / 完整性 / 流畅性（安全场景换 Safety）。
  - **偏见缓解**（#15/#17）：pairwise 交换顺序取平均；rubric 注明「长度不影响分」；Judge 模型强于面试 Agent 模型。
  - **CoT + 结构化 JSON**（#16）：`{scores{}, reasoning{}, confidence, flags[]}`。
  - **校准**（#18）：取 ~30 份人标子集算 Spearman，未达标不上线。
  - 结合 TCR（#12）：额外评「跨轮一致性」「迭代精炼度」。

### M6 能力画像模块（Capability Profiling）
- **职责**：把多场评估聚合成候选人能力雷达（5 维度 + A–F 人设状态机）。
- **技术选型**：参考 #5（1–5 维度 + 雷达图）；L4 人设状态机（升级/降级）。
- **实现要点**：
  - 维度评分聚合：`weighted_avg` 按岗加权（客服 correctness 0.5 / 创意 clarity 0.6，#18）。
  - A–F 状态机：每次真实面试复现某问题→状态降级并触发对应准备模块（对应 PRD 触发规则）。
  - **置信标注**（#11 启示）：Agent 模拟画像标注置信区间，不替代人工判断。

### M7 反哺与迭代模块（Feedback Loop / 否决层）
- **职责**：把每场新面试转成系统成长（L0–L5 更新 + 版本+1 + 反哺 diff）。
- **技术选型**：异步流水线（#3 Redis Stream 状态机）；触发规则（PRD §6.3）。
- **实现要点**：
  - 端到端：`上传→L0落库→L1萃取(打维度/人设标签)→L4状态机更新→L3写/更新模式→L5预测偏差回流→版本+1→生成反哺diff`。
  - 三防火墙（PRD §6.4）：存原理非题目 + L5 收割过度预测 + 人设状态机驱动方向。

---

## 4. 关键技术选型与对比

### 4.1 模型后端：本地 vs 云端
| 维度 | 本地（Ollama + Phi-3 / MiniLM） | 云端（GPT-4o / Gemini / DeepSeek） |
|---|---|---|
| 成本 | 零 API（#1/#4/#6） | 按 token（#15 千次~$2–5） |
| 隐私 | 简历/记录不出本机（#2/#9） | Key 需管理，数据出网 |
| 质量 | 轻量模型反馈较浅（#8 局限） | 强模型评分离线高（#15/#18） |
| 延迟 | 受本机算力 | Groq 极速（#2 毫秒级） |
| **选型建议** | 模拟面试/个性化默认可本地 | 回答评估 Judge 用云端强模型（#15 需强于被评） |

### 4.2 向量库对比
| 选项 | 适用 | 来源 |
|---|---|---|
| pgvector | 已有 PG / 需 SQL 联动 | #3 已用 |
| Chroma | 轻量本地原型、Python 友好 | 通用 |
| FAISS | 海量、纯向量高性能 | 通用 |
| Milvus | 大规模生产 | 通用 |
| **选型建议** | MVP 用 Chroma（零运维）；成长后转 pgvector（复用 #3 栈） | — |

### 4.3 Agent 框架对比
| 选项 | 特点 | 来源 |
|---|---|---|
| LangChain | 生态全、RAG/工具链成熟 | #5 已用 |
| Eino（Go） | 企业级、高并发、Agent 原语清晰 | #9 已用 |
| 原生 + 状态机 | 可控、无框架负担 | #4 phase 状态机 |
| **选型建议** | Python 系 MVP 用 LangChain + 显式状态机；重并发/私有化参考 #9 Go+Eino | — |

### 4.4 评分方式对比
| 方式 | 优劣 | 选型 |
|---|---|---|
| LLM-as-Judge | 懂语义、可规模化、需校准+偏见缓解 | **主选**（#15–#18） |
| 规则/正则 | 快但只能评格式 | 仅做格式校验 |
| 人工 | 最准但不可规模化 | 仅做校准子集 |
| **红线** | 禁用二元 rubric（#10 教训） | — |

### 4.5 语音/实时（可选）
- ASR：Whisper（#2 极速精准）/ 百度语音（#7 中文）。
- 端：Electron 桌面隐形（#2）/ Web（#5/#1）。隐私敏感场景优先本地 + 桌面端。

---

## 5. 数据流程设计

### 5.1 一次完整面试准备的数据流
```
用户上传(简历/JD/往期面试记录)
  → M1 解析简历→结构化JSON(含数据口径/决策)→入L0+L1
  → M2 向量化(简历/项目/标杆案例)→向量库
  → M3 生成问题集(排除L5否决层)→展示给用户练习
  → M4 模拟面试(状态机+深挖链)→对话日志
  → M5 逐答评估(LLM-Judge+rubric)→评分JSON
  → M6 聚合能力画像(5维+雷达+A–F状态)
  → M7 反哺:更新L3/L4/L5→版本+1→反哺diff
```

### 5.2 模拟面试实时数据流（参考 #2/#3）
```
[面试官提问]→Agent(状态机)→[候选人作答]
  →(可选)ASR转写→RAG检索(简历/标杆反模式)
  →M5实时或结束后评估→流式反馈
  →对话上下文压缩(CoT摘要)维持多轮一致(#12/#14)
```

### 5.3 反哺流水线（端到端，异步 #3 Redis Stream）
```
上传请求→存文件→发消息到Stream→立即返回
  Consumer消费→L1萃取→L4状态机→L3模式→L5回流→DB状态更新
  前端轮询最新状态(PENDING→PROCESSING→COMPLETED)
```

---

## 6. 各模块实现要点（可落地清单）

### 6.1 MVP 实现路径（最小可跑通）
1. **M1 简历解析**：LLM + Pydantic schema 抽取（不引入 Tika，MVP 够用）。
2. **M2 知识库**：Chroma 本地向量库 + MiniLM 中文 Embedding（#6 方案），切片带维度元数据。
3. **M3 问题生成**：单一 Prompt（JD+简历+L2 原理层），输出 `{dimension,question,followups[],intent}`，排除 L5。
4. **M4 模拟面试**：LangChain + 显式状态机（仿 #4），单 Agent 扮演。
5. **M5 回答评估**：实现 §3 M5 的 rubric + 五维 + CoT + JSON（#16/#17/#18），Judge 用云端强模型。
6. **M6 能力画像**：聚合 5 维分数 + A–F 状态机，输出雷达图（仿 #5）。
7. **M7 反哺**：同步版 MVP（先不做 Redis Stream），跑通「上传→反哺 diff」。

### 6.2 关键接口定义（草案）
```python
# M1
parse_resume(raw: bytes | str) -> ResumeSchema  # Pydantic, 含 projects[].metrics/decisions
# M3
gen_questions(jd: str, resume: ResumeSchema, exclude: L5Set) -> list[Question]
# M4
InterviewAgent.run(state: FSM, history: list[Turn]) -> Turn  # 状态机驱动
# M5
judge_answer(answer: str, rubric: Rubric, ref: Optional[str]) -> ScoreJSON  # {scores,reasoning,confidence,flags}
# M6
profile(scores: list[ScoreJSON]) -> CapabilityRadar + PersonaState(A_F)
# M7
feedback_loop(new_record: InterviewRecord) -> Diff  # 更新 L0-L5 + 版本+1
```

### 6.3 评分 Rubric 示例（接入 M5，锚定版）
```
## 逻辑性 (Logic) 1-5
5 = 结论先行(总-分-总) + 假设驱动 + 有数据/案例支撑
3 = 有框架但部分碎片化、缺数据
1 = 凭感觉、意识流、无结构
## 数据口径 (Data Rigor) 1-5   # 直击人设B
5 = 数字能答出口径/样本/对比基准/归因/置信度
3 = 有数字但口径模糊
1 = 数字经不起追问(如"95%怎么得出")
```

---

## 7. 可落地路线图
- **MVP（v0.1）**：§6.1 七模块最小闭环，本地 Chroma + 云端 Judge，跑通单场模拟 + 评估 + 反哺。
- **v2**：接入 #3 Redis Stream 异步反哺；#2 实时 ASR + 桌面端（隐形模式）；rubric 人标校准子集上线。
- **v3**：RAG 标杆案例反模式实时避坑；A–F 状态机与 JD 自动对齐生成 1 页业务速览；多模型后端可插拔（#8）；报告导出 PDF（#1 规划）。

---

## 8. 风险与开放问题
- **R1 评估可信度**：LLM-Judge 需持续校准（#18），未达 Spearman 阈值的评分不可直接展示给用户。
- **R2 个体不精确**：生成式 Agent 模拟面试官/画像仅 population 级可靠（#11），须标注置信区间、不替代人工。
- **R3 资源时效性**：GitHub 项目活跃度差异大（#8 早期、#2 近期）；落地时以「架构思路」为借鉴，「具体依赖版本」需重新核对。
- **R4 隐私合规**：实时 Copilot（#2/#7）涉及面试现场使用，须明确「练习用途」边界，避免作弊风险（#7 已声明 condemns cheating）。

---

## 附录 A：资源索引表（18 个）

| # | 名称 | 类型 | 月份 | 贡献模块 |
|---|---|---|---|---|
| 1 | TakPrince/LLM-Interview-Simulator | GitHub | 2026-01 | M4/M5 角色Prompt隔离 |
| 2 | hi2brain/second-brain | GitHub | 2026-06 | M2/M4 实时ASR+隐私 |
| 3 | LilRind/interview-guide | GitHub | 2026-01 | M1/M2 异步状态机+pgvector |
| 4 | AloysiusSundar/TheodoreTheChatBot | GitHub | 2026-01 | M4 阶段状态机 |
| 5 | yang66/ai-interview-assistant | GitHub | 2026 | M1/M3/M5/M6 全生命周期+雷达 |
| 6 | leoin2012/ResumeRoaster | GitHub | 2026 | M2/M3 RAG追问+本地Embedding |
| 7 | huihuihengiang/Cluely-interview | GitHub | 2026 | M1/M2 ASR+OCR+Excel KB |
| 8 | llx9826/llm-interview-coach | GitHub | 2026 | 整体 模块化+多模型后端 |
| 9 | wangzhongyang Go AI面试助手 | 技术文 | 2026 | 整体 模块化分层+Eino Agent |
| 10 | Rubric-ARROW (arXiv:2605.29156) | 论文 | 2026-05 | M5 细粒度rubric自进化 |
| 11 | Interview-Informed Gen Agents (2603.29890) | 论文 | 2026-03 | M4/M6 grounding+置信 |
| 12 | TCR Multi-turn Eval (2605.18660) | 论文 | 2026-05 | M4/M5 一致性+精炼 |
| 13 | PeerRank (2602.02589) | 论文 | 2026-02 | M5 无参考peer评估 |
| 14 | LLM Meeting Turn-taking (2606.17542) | 论文 | 2026-06 | M4 多轮上下文 |
| 15 | QASkills LLM-as-Judge 2026 | 技术文 | 2026 | M5 三模式+偏见 |
| 16 | futureagi LLM Judge Prompting 2026 | 技术文 | 2026 | M5 rubric锚定+CoT+JSON |
| 17 | CSDN LLM裁判五维评分 | 技术文 | 2026 | M5 五维+偏见清单 |
| 18 | callsphere LLM-as-Judge Agent | 技术文 | 2026 | M5 rubric代码+校准+并发 |

## 附录 B：与既有资产一致性
- 本技术方案 = `产品经理面试准备专家_产品文档.md`（PRD）的技术落地；知识内核复用 `产品经理面试真实考点蒸馏库.md` v3（L0–L5 / 5 维度 / A–F 人设 / GOOD·BAD 标杆）。
- 下一步：待用户确认无更多面试记录后，将 PRD + 本方案落成实际 Skill（SKILL.md + 知识库挂载 + 触发词 + 反哺流水线脚本化），并删除早期预测文档中「面不到的问题」。
