#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_external_benchmark_kb.py
------------------------------
把 WHITEOONE/pm-interview-review-plugin 的公开脱敏案例（cases_public）中间文件
汇编成 pm-interview-prep 的「外部标杆 L3」KB 文档。

用法：
  python build_external_benchmark_kb.py --src <中间文件目录> --out <KB.md>

中间文件默认存档目录（随 skill 携带，可直接重跑）：
  scripts/_raw_external_benchmark/
  （共 47 个文件：22 个 09_case_*.json + 25 个 03_*.json，344KB）

中间文件约定（由抓取阶段生成，均已去 markdown 围栏）：
  09_case_XXX.json  -> {case_id, candidate_chains:[...]}   面试官提问链
  03_<project>.json -> 标准项目事实卡（多种 schema 并存）   标杆叙事

上游更新后的重跑方式：
  1) 用 WebFetch 重新抓 `cases_public/` 下的 09_/03_ 文件，落盘到 --src（去掉 ```json 围栏）；
  2) 重跑本脚本即可，无需改代码（渲染器对未知键会做通用降级）。

设计原则：
  - 全量、不筛选、不改写原意，只做结构化呈现。
  - 上游内部证据 ID（如 47B-OUT-C00005）对读者无行动价值，统一剥离并在头部说明。
  - 输出按「公司/业务线」分组，公司由 project_id 前缀推断；
    project_id 为空的链（岗位匹配/公司研究/AI 工具类）回落到该 case 的主导公司。
"""
import argparse
import glob
import json
import os
import re
import sys

# ---------------------------------------------------------------- 标签映射
KEY_LABELS = {
    "business_background": "业务背景",
    "business_background_and_users": "业务背景与用户",
    "business_goals": "业务目标",
    "business_goal": "业务目标",
    "user_problems": "用户问题",
    "user_and_problem": "用户与问题",
    "problem_evidence": "问题证据",
    "specific_problem": "具体问题",
    "core_problem": "核心问题",
    "problem": "问题",
    "baseline_and_problem": "基线与问题",
    "baseline": "基线",
    "business_problem": "业务问题",
    "solution_overview": "方案概览",
    "solution": "方案",
    "strategy": "策略",
    "key_decisions": "关键决策",
    "decision_rationales": "决策依据",
    "experiment_designs": "实验设计",
    "experiment": "实验",
    "experiment_and_result": "实验与结果",
    "experiment_results": "实验结果",
    "experiment_boundary": "实验边界",
    "result_metrics": "结果指标",
    "result": "结果",
    "results": "结果",
    "ownership_boundaries": "职责与贡献边界",
    "responsibility_boundary": "职责边界",
    "responsibility": "职责分工",
    "roles": "角色分工",
    "candidate_role": "候选人角色",
    "other_roles": "其他角色",
    "human_participation": "人工参与环节",
    "dependencies": "依赖",
    "ambiguities": "口径歧义（上游课件内部冲突）",
    "not_covered": "上游未覆盖",
    "not_implemented": "一期未实现",
    "not_implemented_in_v1": "一期未实现",
    "implemented_in_v1": "一期已实现",
    "metrics": "指标",
    "metric_definition": "指标定义",
    "metric_definitions": "指标定义",
    "metric_boundaries": "指标边界",
    "fact_card": "事实卡",
    "facts": "项目事实",
    "full_business_flow": "完整业务链路",
    "full_flow": "完整链路",
    "end_to_end_flow": "端到端链路",
    "system_flow": "系统链路",
    "input_output": "输入输出",
    "stages": "阶段",
    "stage_note": "阶段口径说明",
    "boundaries": "边界",
    "boundary": "边界",
    "scope": "范围",
    "key_rules": "关键规则",
    "strategy_stages": "策略阶段",
    "team_metric_ownership": "团队指标归属",
    "business_metric_relation": "业务指标关系",
    "brand_effect_value_relation": "品牌与效果的价值关系",
    "sales_and_delivery_boundary": "售卖与交付边界",
    "capability_boundary": "能力边界（通用 / 定制）",
    "ai_release_standard": "AI 上线门槛",
    "ai_quality_lifecycle": "AI 质量闭环时序",
    "prompt_strategy": "Prompt 策略",
    "financial_ledger": "资金流账本",
    "extraction_limitations": "提取限制",
    "data_conclusion": "数据结论",
    "feasibility": "可行性",
    "diagnosis": "诊断",
    "problem_and_evidence": "问题与证据",
    "root_causes": "根因",
    "benefit_and_boundary": "收益与边界",
    "future_boundary": "后续（非一期）方向",
    "future_design_constraint": "迁移设计约束",
    "related_but_separate_project_boundary": "相邻但独立的项目边界",
    "result_boundary": "结果口径边界",
    "source_documents": "上游来源（已脱敏）",
    "estimate": "收益预估",
    "validation": "验证路径",
    "gsb": "GSB 评测",
    "time_window": "时间窗口结论",
    "historical": "历史实验结论",
    "final_ab": "最终 AB 结论",
    # ---- 补齐各 schema 变体里出现的键 ----
    "business_background_and_goal": "业务背景与目标",
    "business_context": "业务语境",
    "role_boundary": "角色边界",
    "team_goal": "团队目标",
    "project_goal": "项目目标",
    "team_metric_ownership": "团队指标归属",
    "incremental_orders": "增量完单",
    "activity_cost": "活动成本",
    "order_efficiency": "钱效（活动成本 / 增量完单）",
    "roi": "ROI",
    "item": "名称",
    "payer": "付款方",
    "receiver": "收款方",
    "definition": "口径定义",
    "uncertainties": "不确定项",
    "applicable": "是否适用",
    "reusable": "可复用（通用）",
    "business_specific": "业务定制",
    "ai_model": "AI 模型",
    "product": "产品",
    "operations": "运营",
    "engineering": "工程",
    "algorithm": "算法",
    "big_data_and_engineering": "大数据与工程",
    "notes": "备注",
    "stage": "阶段",
    "role": "角色",
    "evidence": "证据",
}

# 降噪键：不输出到正文
SKIP_KEYS = {
    "schema_version", "project_id", "project_name", "case_id",
    "mining_prompt_version", "generated_from", "course_evidence_ids",
    "evidence_ids", "evidence", "source_document_ids", "sha256", "path",
    "candidate_chains", "non_extractable_reasons", "_case", "_company",
    "notes", "confidence", "teacher_review_required", "bank_status",
    "source_documents",
}

COMPANY_MAP = [
    ("bytedance", "字节跳动"),
    ("tencent_video", "腾讯视频"),
    ("tmall", "天猫 · 猫超与顺买"),
    ("baidu_map", "百度地图"),
    ("baijiahao", "百家号"),
    ("kuaishou", "快手"),
    ("iqiyi", "爱奇艺"),
    ("jd_", "京东"),
    ("meituan", "美团"),
    ("gaode", "高德"),
    ("douyin", "抖音"),
    ("shopee", "Shopee · 跨境电商"),
    ("generic", "通用方法 · 场景题"),
]

CHAIN_LABELS = {
    "main_question": "主问",
    "follow_up_path": "追问路径",
    "trigger_condition": "触发条件",
    "interviewer_intent": "面试官意图",
    "evidence_sought": "要的证据",
    "stop_condition": "停止条件",
    "domain_modules": "领域模块",
    "candidate_strategy_title": "应对策略标题",
}

# 上游部分 03_ 文件没有 project_name 字段。此处补的是**编辑者摘要名**（非上游原文），
# 目的是让 KB 标题可读；真实内容仍以该文件的事实字段为准。
PROJECT_NAME_ZH = {
    "baijiahao_homepage_ad_revenue_antifraud": "作者主页广告分润反作弊",
    "douyin_ai_brand_proposal": "抖音 AI 品牌提案工具",
    "douyin_merchant_growth_incentive_visibility": "商家成长流量激励效果可见",
    "gaode_chauffeur_navigation_dwell_coupon": "高德代驾：到达驻留触发补贴",
    "gaode_growth_ai_activity_audit": "高德增长 AI 活动审核平台",
    "jd_ai_technician_qa": "京东养车 AI 技师问答",
    "jd_ai_technician_workorder_embedding": "京东养车：AI 问答嵌入工单上下文",
    "kuaishou_address_query_order": "快手寻址词店铺直达",
    "kuaishou_new_user_search_conversion": "快手新用户搜索转化",
    "kuaishou_query_product_relevance": "快手搜索商品相关性治理",
    "meituan_powerbank_replenishment_workbench": "美团共享充电宝补宝工作台",
    "meituan_powerbank_third_party_dispatch": "美团共享充电宝三方运力调度",
}


def dir_text(d):
    """把 direction 压成一行，丢掉 basis 这类元信息。"""
    if not d:
        return ""
    if isinstance(d, str):
        return d
    parts = []
    p = d.get("primary_direction")
    if p:
        parts.append(str(p))
    sec = d.get("secondary_directions") or []
    if sec:
        parts.append("← " + "、".join(str(x) for x in sec))
    tags = d.get("scenario_tags") or []
    if tags:
        parts.append("（场景：" + "、".join(str(x) for x in tags) + "）")
    return " ".join(parts)


def lab(k):
    if k in KEY_LABELS:
        return KEY_LABELS[k]
    return k.replace("_", " ")


def company_of(pid):
    if not pid:
        return None
    p = str(pid).lower()
    for key, name in COMPANY_MAP:
        if p.startswith(key):
            return name
    return "其他"


def as_text(v):
    """把任意标量/浅层结构压成一行文本。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "；".join(as_text(x) for x in v if as_text(x))
    if isinstance(v, dict):
        if "value" in v and isinstance(v["value"], str):
            return v["value"].strip()
        parts = []
        for k2, v2 in v.items():
            if k2 in SKIP_KEYS:
                continue
            t = as_text(v2)
            if t:
                parts.append("%s：%s" % (lab(k2), t))
        return "；".join(parts)
    return str(v)


def render_node(key, val, depth=0):
    """把 03_ 文件的一个顶层键渲染成 markdown 行列表。"""
    lines = []
    h = "#" * min(6, 5 + depth) if False else None  # 正文不用标题层级，用加粗
    head = "**%s**" % lab(key)

    # 字符串
    if isinstance(val, str):
        val = val.strip()
        if val:
            lines.append("- %s：%s" % (head, val))
        return lines

    # 数字/布尔
    if isinstance(val, (int, float, bool)):
        lines.append("- %s：%s" % (head, as_text(val)))
        return lines

    # dict
    if isinstance(val, dict):
        # {value, evidence_ids}
        if "value" in val and isinstance(val["value"], str):
            lines.append("- %s：%s" % (head, val["value"].strip()))
            return lines
        # 全部子值是 {value,...} 的结构
        if val and all(isinstance(x, dict) and "value" in x for x in val.values()):
            lines.append("- %s：" % head)
            for k2, v2 in val.items():
                if k2 in SKIP_KEYS:
                    continue
                lines.append("  - **%s**：%s" % (lab(k2), as_text(v2.get("value"))))
            return lines
        # financial_ledger
        if "applicable" in val or "items" in val:
            lines.append("- %s：" % head)
            if not val.get("applicable", True):
                lines.append("  - 不适用")
            for it in val.get("items", []) or []:
                if isinstance(it, dict):
                    seg = []
                    for k2 in ("item", "payer", "receiver", "role", "definition"):
                        if it.get(k2):
                            seg.append("%s：%s" % (lab(k2), it[k2]))
                    if seg:
                        lines.append("  - " + "；".join(seg))
            for u in val.get("uncertainties", []) or []:
                lines.append("  - 不确定项：%s" % as_text(u))
            return lines
        # 标量字典
        lines.append("- %s：" % head)
        for k2, v2 in val.items():
            if k2 in SKIP_KEYS:
                continue
            t = as_text(v2)
            if t and not isinstance(v2, (list, dict)):
                lines.append("  - %s：%s" % (lab(k2), t))
            elif isinstance(v2, (list, dict)):
                sub = render_node(k2, v2, depth + 1)
                for s in sub:
                    lines.append("  " + s)
        return lines

    # list
    if isinstance(val, list):
        if not val:
            return lines
        lines.append("- %s：" % head)
        for item in val:
            if isinstance(item, str):
                t = item.strip()
                if t and t not in ("\u200b", ""):
                    lines.append("  - %s" % t)
            elif isinstance(item, dict):
                if "node_id" in item:  # 09_ 的 question_nodes，此处不用
                    continue
                if "item" in item and len(item) <= 6:
                    seg = []
                    for k2 in ("item", "payer", "receiver", "role", "definition"):
                        if item.get(k2):
                            seg.append("%s：%s" % (lab(k2), item[k2]))
                    lines.append("  - " + "；".join(seg))
                elif "stage" in item and "fact" in item:
                    lines.append("  - **%s**：%s" % (item["stage"], str(item["fact"]).strip()))
                elif "fact" in item:
                    t = str(item.get("fact", "")).strip()
                    extra = []
                    for k2 in ("notes", "role"):
                        if item.get(k2):
                            extra.append("%s：%s" % (lab(k2), item[k2]))
                    suffix = ("（" + "；".join(extra) + "）") if extra else ""
                    lines.append("  - %s%s" % (t, suffix))
                elif "step" in item:
                    lines.append("  - %s" % as_text(item.get("step")))
                elif "stage" in item:
                    rest = {k2: v2 for k2, v2 in item.items()
                            if k2 != "stage" and k2 not in SKIP_KEYS}
                    lines.append("  - **%s**：%s" % (item["stage"], as_text(rest)))
                elif "role" in item or "boundary" in item:
                    lines.append("  - %s：%s" % (item.get("role", ""), item.get("boundary", "")))
                else:
                    t = as_text(item)
                    if t:
                        lines.append("  - %s" % t)
            elif isinstance(item, (list, dict)):
                t = as_text(item)
                if t:
                    lines.append("  - %s" % t)
        return lines

    return lines


def render_03(doc):
    lines = []
    for key, val in doc.items():
        if key in SKIP_KEYS:
            continue
        if val in (None, "", [], {}):
            continue
        lines.extend(render_node(key, val))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = args.src
    chains_files = sorted(glob.glob(os.path.join(src, "09_*.json")))
    bench_files = sorted(glob.glob(os.path.join(src, "03_*.json")))
    if not chains_files:
        print("ERROR: no 09_*.json found in %s" % src, file=sys.stderr)
        sys.exit(1)

    # ---- 载入提问链
    cases = []          # [(case_id, [chains])]
    all_chains = []
    for f in chains_files:
        d = json.load(open(f, encoding="utf-8"))
        cid = d.get("case_id") or os.path.basename(f).replace(".json", "")
        cs = d.get("candidate_chains", []) or []
        for c in cs:
            c["_case"] = cid
            all_chains.append(c)
        cases.append((cid, cs))

    # ---- 载入标杆叙事
    benches = {}
    for f in bench_files:
        d = json.load(open(f, encoding="utf-8"))
        pid = d.get("project_id") or os.path.basename(f)[3:-5]
        benches[pid] = d

    # ---- 推断每个 case 的主导公司（优先非“通用”公司）
    GENERIC = "通用方法 · 场景题"
    case_company = {}
    case_companies = {}
    for cid, cs in cases:
        counter = {}
        order_co = []
        for c in cs:
            co = company_of(c.get("project_id"))
            if not co:
                continue
            if co not in order_co:
                order_co.append(co)
            counter[co] = counter.get(co, 0) + 1
        specific = [co for co in order_co if co != GENERIC]
        case_companies[cid] = specific or ([GENERIC] if order_co else [])
        if specific:
            case_company[cid] = max(specific, key=lambda k: counter[k])
        elif order_co:
            case_company[cid] = order_co[0]
        else:
            case_company[cid] = GENERIC

    # ---- 给每条链定公司并分组（保持出现顺序）
    groups = {}   # company -> [chain]
    order = []
    for c in all_chains:
        co = company_of(c.get("project_id")) or case_company.get(c.get("_case"), "其他")
        c["_company"] = co
        if co not in groups:
            groups[co] = []
            order.append(co)
        groups[co].append(c)

    def case_num(cid):
        m = re.search(r"(\d+)", cid or "")
        return int(m.group(1)) if m else 999

    out = []
    A = out.append

    files_note = "22 个 case / %d 条提问链 / %d 篇标杆叙事" % (len(all_chains), len(benches))
    n_general = sum(1 for c in all_chains if c.get("genericity") == "generalizable")
    n_dir = sum(1 for c in all_chains if c.get("genericity") == "direction_specific")

    # ================= 头部 =================
    A("# 外部标杆 · 真实面经提问链（WHITEOONE 公开脱敏案例 · 全量版）")
    A("")
    A("> 本文件是 `pm-interview-prep` 的**外部标杆 L3 溯源资产**（见 SKILL.md §6.1）。")
    A("> 来源：GitHub `WHITEOONE/pm-interview-review-plugin` → `cases_public/` 公开脱敏导出（抽取于 2026-09-11）。")
    A("> **全量规模**：%s。" % files_note)
    A("> **定位**：只进 L3 模式层 / 考察意图溯源层，**不进 L0/L1、不押题、不背答案、不声称“真题”**。")
    A("> 这里的“具体题目”只用来反推“面试官在验证什么”。")
    A("")
    A("## 0. 授权与边界（务必先看）")
    A("")
    A("- **上游仓库无 LICENSE 文件**（实测 404）。默认“保留所有权利”。")
    A("- 本文件内容仅限**你个人备考自用**：不得外发、不得二次发布、不得用于商业或培训场景。")
    A("- 如上游未来补充 LICENSE，以 LICENSE 条款为准。")
    A("- 案例均为脱敏数据，不含个人隐私。")
    A("- **编辑说明**：上游内部证据 ID（形如 `项目代号-序号`）已统一剥离——")
    A("  它们指向上游课程库，对读者没有行动价值；正文中原本嵌在句子里的 ID 统一替换为“该处”。")
    A("  除此之外，事实、数值、口径、边界均按原文保留，未改写。")
    A("- **口径纪律**：上游课件本身存在内部冲突（尤其指标分母/命名）。凡 `口径歧义` 小节列出的，")
    A("  一律**不得**当成“标准答案”去背，只能当作“这里本来就有歧义”的提醒。")
    A("")
    A("## 1. 怎么用这个文件（4 条）")
    A("")
    A("1. **T10 现场搜题 / T9 出题映射**：拿到目标公司业务线 → 去 §3 找对应分组 → 看“面试官真实怎么问、追问什么、要什么证据”。")
    A("2. **T3 复盘方法增强**：§5 的 5 项技术并入你现有的“事实/分析/推测三色 + 原话 100% 保留”纪律。")
    A("3. **数据口径防火墙**：§5 第 5 项（资金流账本）+ 每篇叙事的 `口径歧义` 小节，与你 B 维度口径纪律同源互证。")
    A("4. **对照自查**：§4 的标杆叙事是“他人项目的标准答法骨架”，用来对照“一场好复盘该覆盖什么”，**不是你的简历内容**。")
    A("")
    A("## 2. 全量导航（case → 业务线 → 链数）")
    A("")
    A("| case | 主导公司 / 业务线 | 提问链 | 覆盖项目（project_id） |")
    A("|---|---|---|---|")
    for cid, cs in sorted(cases, key=lambda x: case_num(x[0])):
        pids = []
        for c in cs:
            p = c.get("project_id")
            if p and p not in pids:
                pids.append(p)
        comp = "、".join(case_companies.get(cid) or [GENERIC])
        A("| %s | %s | %d | %s |" % (
            cid, comp, len(cs),
            "、".join("`%s`" % p for p in pids) if pids else "—（岗位匹配 / 概念题）"))
    A("")
    A("- 全量提问链 **%d** 条：其中 `generalizable`（跨方向可迁移）**%d** 条，`direction_specific`（方向专用）**%d** 条。"
      % (len(all_chains), n_general, n_dir))
    A("- 标杆叙事 **%d** 篇，见 §4。" % len(benches))
    A("")

    # ================= §3 提问链 =================
    A("## 3. 面试官提问链（全量 %d 条，按公司 / 业务线分组）" % len(all_chains))
    A("")
    A("每条格式：**主问 → 追问路径 → 触发条件 → 面试官意图 → 要的证据 → 停止条件**。")
    A("")
    gi = 0
    for co in order:
        cs = groups[co]
        gi += 1
        A("### 3.%d %s（%d 条）" % (gi, co, len(cs)))
        A("")
        for c in cs:
            cid = c.get("_case", "")
            cn = case_num(cid)
            title = c.get("candidate_strategy_title") or c.get("main_question") or ""
            pid = c.get("project_id") or "—"
            A("#### ▸ %s" % title)
            meta = "`%s` ｜ 项目：`%s`" % (cid, pid)
            if c.get("chain_id"):
                meta += " ｜ 链 ID：`%s`" % c["chain_id"]
            A("*%s*" % meta)
            A("")
            if c.get("main_question"):
                A("- **主问**：%s" % c["main_question"])
            fu = c.get("follow_up_path") or []
            if fu:
                A("- **追问路径**：%s" % " → ".join(fu))
            # question_nodes（case_037 新版 schema）
            for node in c.get("question_nodes", []) or []:
                if isinstance(node, dict) and node.get("literal_question"):
                    A("- **原话节点**（%s，%s）：%s" % (
                        node.get("question_id", ""),
                        node.get("interviewer_move", ""),
                        node["literal_question"]))
            if c.get("trigger_condition"):
                A("- **触发条件**：%s" % c["trigger_condition"])
            if c.get("interviewer_intent"):
                A("- **面试官意图**：%s" % c["interviewer_intent"])
            ev = c.get("evidence_sought") or []
            if ev:
                A("- **要的证据**：%s" % "；".join(ev))
            if c.get("stop_condition"):
                A("- **停止条件**：%s" % c["stop_condition"])
            dm = c.get("domain_modules") or []
            d = c.get("direction") or {}
            dstr = dir_text(d)
            tail = []
            if dm:
                tail.append("领域模块：%s" % "、".join(dm))
            if dstr:
                tail.append("方向：%s" % dstr)
            gen = c.get("genericity") or (d.get("genericity") if isinstance(d, dict) else None)
            if gen:
                tail.append("通用性：%s" % gen)
            if tail:
                A("- *%s*" % " ｜ ".join(tail))
            if c.get("notes"):
                A("- *备注：%s*" % c["notes"])
            A("")

    # ================= §4 标杆叙事 =================
    A("## 4. 标准项目逻辑 · 标杆叙事范本（全量 %d 篇）" % len(benches))
    A("")
    A("> 这些是**他人真实项目**的事实卡，用来对照“一场好复盘该覆盖什么”。")
    A("> **不是你的简历内容，不要混进你的逐字稿。**")
    A("")
    bi = 0
    for pid in sorted(benches.keys()):
        doc = benches[pid]
        bi += 1
        name = doc.get("project_name") or PROJECT_NAME_ZH.get(pid) or pid
        A("### 4.%d %s" % (bi, name))
        A("*`%s` ｜ 归属：%s*" % (pid, company_of(pid) or "通用"))
        A("")
        out.extend(render_03(doc))
        A("")

    # ================= §5 复盘方法增强 =================
    A("## 5. 复盘方法增强（5 项，与你现有纪律同源）")
    A("")
    A("你 T3 复盘已有“事实/分析/推测三色 + 原话 100% 保留”。本插件额外给出 5 个可命名的技术：")
    A("")
    A("1. **对话语境卡**：题面投影前先剥离候选人身份，只留“前序话题 / 面试官为何在此刻问 / 直接回答重点”。→ 防止“把通用题改写成项目题”的偏差。")
    A("2. **答题卡纯度**：答题目标 / 完成测试 / 首回应形状必须同时覆盖“字面任务”和“语境卡直接重点”；只命中一个分支却未承接追问重点 = 对话连续性不足。")
    A("3. **回声防火墙**：检测“参考回答”是否只是复述候选人原话。→ 自检：你的“标准答法”是不是在 parrot 自己草稿，而非独立成立的论证。")
    A("4. **独立参考回答**：不看候选人回答先生成标杆答法，再盲审比对。→ 先有独立标杆，再比对自己的块。")
    A("5. **商业化资金流账本**：出现 ROI / 收入 / 成本 / 利润 / eCPM / 分润 / 补贴 / 结算时，先建账本（付款方 / 收款方 / 角色 / 口径 / 周期），课件无最终收入不得用局部数反推真实收入。→ 与 B 维度数据口径防火墙同源。")
    A("")

    # ================= §6 对接点 =================
    A("## 6. 与你现有 skill 的对接点")
    A("")
    A("- → `kb/真实面试题库.md`：本文件提问链 = 这些公司“考察意图”的溯源补充。")
    A("- → `kb/模块_岗位业务知识讲解.md` 出题映射表：每条提问链都可反推“这条业务链路 / 指标 / 策略”对应什么面试题。")
    A("- → T3 复盘：§5 的 5 项技术并入三色纪律。")
    A("- → B 维度数据口径：§5 第 5 项 + 各篇 `口径歧义` 小节直接强化口径防火墙。")
    A("- **红线**：本文件是他人案例，只作溯源与标杆，绝不作为你自己的经历写进逐字稿。")
    A("")

    txt = "\n".join(out).rstrip() + "\n"
    # 兜底：正文中嵌在句子里的上游证据 ID（如“课件C00031写…”）统一替换为“该处”
    txt = re.sub(r"C\d{4,5}(?:-R\d+)?", "该处", txt)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)

    print("OK  ->  %s" % args.out)
    print("      chains=%d (cases=%d)  benchmarks=%d  companies=%d"
          % (len(all_chains), len(cases), len(benches), len(order)))
    print("      lines=%d  chars=%d" % (txt.count("\n"), len(txt)))
    print("      companies: %s" % ", ".join("%s(%d)" % (c, len(groups[c])) for c in order))


if __name__ == "__main__":
    main()
