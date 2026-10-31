#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
elite20_packager.py — Elite20 提交包自检器（elite20-packager 技能的核心脚本）

输入：一个 Elite20 提交包目录路径
输出：packager_report.md（总览 + 缺失矩阵 + 逐项修复建议）
      packager_report.xlsx（openpyxl，4 个 sheet）
      可选 --scaffold 为缺失项生成「待填」骨架文件

检查三层：
  L1 六件套命名     姓名_CX_*.md（方案草案/方案设计/G1背书/AI日志/拿来说明/Portfolio/AAR）
  L2 仓库结构       README/CHANGELOG/LICENSE/requirements.txt/scripts/reproduce.sh/tests/ docs/...
  L3 挑战专属交付物  从官方 challenge.json 的 required_deliverables 读取
三条红线自检：
  R1 AI 日志存在且含 >=3 个决策节点
  R2 拿来说明标了 License
  R3 有可复现脚本（reproduce.sh + 冒烟测试）

用法：
  python3 elite20_packager.py ~/Desktop/赵怡涵_C2_提交包
  python3 elite20_packager.py ~/Desktop/赵怡涵_C2_提交包 --challenge C2 --scaffold
  python3 elite20_packager.py <包目录> --json --outdir /tmp/out

退出码：0 = 无缺失项；1 = 有缺失项；2 = 用法/路径错误
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = SKILL_DIR / "references" / "challenges_index.yaml"
DEFAULT_CHECKLIST = SKILL_DIR / "references" / "checklist.yaml"

# 忽略这些路径片段（相对包目录）
IGNORE_PARTS = {".git", "__pycache__", ".pytest_cache", ".DS_Store", ".ipynb_checkpoints", "node_modules"}
IGNORE_SUFFIX = {".pyc", ".pyo", ".DS_Store"}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class Item:
    """一条检查项。"""

    def __init__(self, layer, key, label, status, detail, fix, evidence="", severity="error", scaffold=None):
        self.layer = layer          # L1 / L2 / L3 / R
        self.key = key
        self.label = label
        self.status = status        # OK / MISSING / WARN / INFO
        self.detail = detail
        self.fix = fix
        self.evidence = evidence
        self.severity = severity    # error / warn / info
        self.scaffold = scaffold or {}   # {relpath: template_text}

    @property
    def is_problem(self):
        if self.status == "MISSING":
            return True
        if self.status == "WARN" and self.severity == "error":
            return True
        return False

    def as_dict(self):
        return {
            "layer": self.layer, "key": self.key, "label": self.label,
            "status": self.status, "detail": self.detail, "fix": self.fix,
            "evidence": self.evidence, "severity": self.severity,
        }


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def rel_files(pkg: Path):
    """列出包内所有文件（相对路径，正斜杠），按字典序。"""
    out = []
    for root, dirs, files in os.walk(pkg):
        dirs[:] = [d for d in dirs if d not in IGNORE_PARTS]
        for name in files:
            if name in IGNORE_PARTS or Path(name).suffix in IGNORE_SUFFIX:
                continue
            full = Path(root) / name
            out.append(str(full.relative_to(pkg)).replace(os.sep, "/"))
    return sorted(out)


def rel_dirs(pkg: Path):
    out = []
    for root, dirs, _files in os.walk(pkg):
        dirs[:] = [d for d in dirs if d not in IGNORE_PARTS]
        for d in dirs:
            out.append(str((Path(root) / d).relative_to(pkg)).replace(os.sep, "/"))
    return sorted(out)


def match_files(files, globs):
    """用 fnmatch 在「相对路径」和「basename」两个层面匹配。"""
    hits = []
    for f in files:
        base = f.rsplit("/", 1)[-1]
        for g in globs:
            if fnmatch.fnmatch(f, g) or fnmatch.fnmatch(base, g):
                hits.append(f)
                break
    return hits


def rank_hits(hits, student=None, challenge=None):
    """把「像本包自己产物」的文件排前面。

    踩坑记录（v1.0 修的真实 bug）：六件套里的 `*设计*.md` 会匹配到
    `赵怡涵_C1_提交包/source/CS146S_offline/resources/w03-design-doc-template.md`
    ——那是**上游课程原始资料**，不是学生自己的方案设计。按字典序取 hits[0] 时
    它排在前面，导致误判「方案设计只有 237 字」。
    排序规则：顶层 > 有 `姓名_CX_` 前缀 > 路径短 > 字典序。
    """
    def score(f):
        base = f.rsplit("/", 1)[-1]
        depth = f.count("/")
        prefixed = 0
        if student and challenge and base.startswith("%s_%s" % (student, challenge)):
            prefixed = -2
        elif student and base.startswith("%s_" % student):
            prefixed = -1
        return (depth + prefixed, len(f), f)
    return sorted(hits, key=score)


def read_text(pkg: Path, rel, limit=None):
    p = pkg / rel
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        try:
            txt = p.read_text(encoding="gbk", errors="replace")
        except Exception:
            return ""
    return txt[:limit] if limit else txt


def strip_md(text):
    """粗略去掉 Markdown 标记后统计「中文字数 + 英文词数」。

    踩坑记录（v1.0 修过一次真实 bug）：最早用 `^\\s*[>#\\-*+|].*$` 删行，
    因为 `\\s` 会跨行匹配，把大段正文一起吃掉，导致《赵怡涵_C1_提交包》的
    `方案设计.md`（5595 字符）被算成 34 字、误报「字数偏少」。
    现在的做法只删「结构性噪音」（HTML 注释 / 代码块 / 表格分隔行），
    列表和表格里的正文照常计数。
    """
    t = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`\n]*`", "", t)
    t = re.sub(r"^[ \t]*\|[ \t\-:|]+\|[ \t]*$", "", t, flags=re.M)   # 表格分隔行（注意用 [ \t] 不用 \s，否则会跨行吞正文）
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[#>*_~\[\]()]", " ", t)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", t))
    words = len(re.findall(r"[A-Za-z][A-Za-z0-9'\-]+", t))
    return cjk + words


def count_decision_nodes(text):
    """启发式统计 AI 日志里的决策节点数。

    ⚠️ 这个函数改了 **三版**，每一版都是被真实文件打脸的（完整记录见 AI 日志决策节点 7）：

      v1  只数「决策节点」这四个字
          → 《赵怡涵_C1_提交包》的日志用 `### 决策 1 ·` 编号，8 个真实节点被算成 2 个，**误报红线**。

      v2  三种口径取最大值
          → 修好了 C1，但《赵怡涵_C4_提交包》自己的日志在正文里反复出现「见决策节点 4」
            这类交叉引用，10 个节点被算成 29 个（虚高）。

      v3  优先链（有小标题就只信小标题）
          → 修好了 C4，但把 C2 打回去了：《赵怡涵_C2_提交包》的日志用 `### D1-01 ｜ …`
            编号，小标题里根本没有「决策」二字，只算成 1 个，**又误报了一次红线**。

      v4（当前） 多路识别 + 取最大值，并识别「本日志共 N 个」这类自述计数：
        (a) 自述计数：`共 10 个` / `10 个决策节点` / `决策节点：10`
        (b) 编号小标题：含「决策/节点/Decision」且带数字的标题
        (c) 编号小标题（前缀式）：`### D1-01 ｜ …`、`### N-01` 这类「字母+数字-数字」编号
        (d) 「决策节点」小节下的 ### 子标题（不管子标题叫什么）
        (e) 正文里的 `决策 1` / `节点 2`
        不再使用「字面量出现次数」——它会被正文交叉引用污染。

    结论：**这类"数数"的判定在真实文件面前很脆弱**，所以报告里始终标注它是启发式，
    并且这个数只用来判断"是否 < 3"，不用来精确报告节点个数。
    """
    heads = re.findall(r"^#{2,6}\s*(.+)$", text, re.M)
    heads_lv2 = re.findall(r"^##\s*(.+)$", text, re.M)
    heads_lv3 = re.findall(r"^###\s*(.+)$", text, re.M)

    num = r"[0-9０-９一二三四五六七八九十]+"

    # (a) 自述计数
    declared = 0
    for pat in (r"(?:共|合计|总计|一共)\s*\**\s*(\d+)\s*\**\s*个",
                r"(\d+)\s*个\s*(?:关键)?决策(?:节点)?",
                r"决策节点\s*[:：]\s*(\d+)"):
        for m in re.finditer(pat, text):
            try:
                declared = max(declared, int(m.group(1)))
            except ValueError:
                pass

    # (b) 含「决策/节点/Decision」且带数字的标题
    numbered = [h for h in heads
                if re.search(r"决策|节点|decision", h, re.I) and re.search(num, h)]

    # (c) 前缀式编号标题：D1-01 / N-01 / 决策-01
    prefixed = [h for h in heads if re.match(r"^[A-Za-z]{1,3}\s*\d+\s*[-–—.]\s*\d+", h.strip())]

    # (d) 「决策节点」小节下的 ### 子标题
    under = 0
    for i, h in enumerate(heads_lv2):
        if re.search(r"决策|节点", h):
            after = text.split("## " + h, 1)[-1]
            after = after.split("\n## ", 1)[0]
            under = max(under, len(re.findall(r"^###\s+\S", after, re.M)))

    # (e) 正文里的 决策 1 / 节点 2 —— 只认「行首」或「加粗标签」形式。
    #     不能全篇乱抓：本包日志正文里"见决策节点 4""决策节点 3–7"这类交叉引用
    #     会被算成节点，v2 那一版就是这样把 10 个数成 29 个的。
    inline = 0
    inline += len(re.findall(r"(?:^|\n)[ \t]*(?:[-*+][ \t]*)?\**[ \t]*(?:决策|节点|Decision)[ \t]*" + num,
                             text, re.I))
    inline += len(re.findall(r"\*\*[ \t]*(?:决策|节点|Decision)[ \t]*" + num, text, re.I))

    return max(declared, len(numbered), len(prefixed), under, inline)


# ---------------------------------------------------------------------------
# 注册表 / 清单
# ---------------------------------------------------------------------------

def load_yaml(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    if yaml is None:
        raise RuntimeError("需要 pyyaml 才能读取 %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_registry(path: Path):
    data = load_yaml(path, {})
    return data.get("challenges", {})


def infer_student_challenge(pkg: Path, files, challenge_arg, student_arg):
    """从目录名 / 文件名推断学生姓名与挑战编号。"""
    base = pkg.name
    student = student_arg
    challenge = challenge_arg

    m = re.search(r"([\u4e00-\u9fff]{2,4})[_\-]?(C\d+[A-Z]?)?", base)
    if not student and m and m.group(1):
        student = m.group(1)
    if not challenge:
        m2 = re.search(r"(C\d+[A-Z]?)", base)
        if m2:
            challenge = m2.group(1).upper()

    if not challenge:
        # 退回到文件名里出现最多的 C?\d+ token
        counter = {}
        for f in files:
            for tok in re.findall(r"(?<![A-Za-z0-9])(C\d+[A-Z]?)(?![A-Za-z0-9])", f):
                counter[tok.upper()] = counter.get(tok.upper(), 0) + 1
        if counter:
            challenge = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    if not student:
        # 从 姓名_CX_xxx.md 里取前缀
        for f in files:
            mm = re.match(r"^([\u4e00-\u9fff]{2,4})_C\d", f.rsplit("/", 1)[-1])
            if mm:
                student = mm.group(1)
                break
    return student, challenge


# ---------------------------------------------------------------------------
# L1 六件套
# ---------------------------------------------------------------------------

SIX_PIECE = [
    # (key, label, globs, min_chars, content_probe, content_hint, template)
    ("方案草案", "方案草案", ["*方案草案*.md", "*proposal*.md", "*草案*.md"], 500,
     [r"关卡|问题|自问|Q\d|？|\?"], "≥500 字，含「四个关卡问题」式自问自答"),
    ("方案设计", "方案设计", ["*方案设计*.md", "*设计*.md", "*design*.md"], 800,
     [r"目标", r"架构|结构|模块|分层|组件|流程|pipeline", r"选型|技术|理由", r"风险"],
     "正式方案：目标 / 架构 / 技术选型理由 / 风险"),
    ("G1背书", "G1 群内发起背书", ["*G1*.md", "*背书*.md"], 200,
     [r"G1", r"群"], "群内发起模板 + 待填表格（发起动作只能本人做）"),
    ("AI日志", "AI 日志", ["*AI日志*.md", "*AI_?日志*.md", "*ai.?log*.md"], 600,
     [r"决策节点"], "≥3 个决策节点，格式见《交付规范》§4"),
    ("拿来说明", "拿来说明", ["*拿来说明*.md", "*说明来源*.md", "*credits*.md", "*attribution*.md"], 300,
     [r"License|许可证|MIT|Apache|AGPL|GPL|CC[ -]?BY|BSD|版权"], "复用来源表 + License + 改了什么"),
    ("Portfolio条目", "Portfolio 条目", ["*Portfolio*.md", "*PORTFOLIO*.md", "*作品集*.md"], 200,
     [r"证据|链接|http|path|文件"], "一句话价值 + 证据链接"),
    ("AAR", "AAR 复盘", ["*AAR*.md", "*复盘*.md"], 800,
     [r"七维|维度", r"重来|改进|下次"], "七维复盘（文首声明「七维为自拟」）"),
]


def check_six_piece(pkg, files, student, challenge):
    items = []
    prefix = ("%s_%s_" % (student, challenge)) if (student and challenge) else None
    for key, label, globs, min_chars, probes, hint in SIX_PIECE:
        hits = rank_hits(match_files(files, globs), student, challenge)
        if not hits:
            # 骨架文件名：有 姓名_CX 前缀就直接用，否则退回占位符
            tmpl_path = ("%s%s.md" % (prefix, key)) if prefix else ("姓名_CX_%s.md" % key)
            items.append(Item(
                "L1", key, label, "MISSING",
                "未找到匹配 %s 的文件" % "/".join(globs),
                "新建 `%s`：%s" % (tmpl_path, hint),
                scaffold={tmpl_path: scaffold_six_piece(key, hint, prefix, student, challenge)},
            ))
            continue

        rel = hits[0]
        text = read_text(pkg, rel)
        nchars = strip_md(text)
        notes = []
        status = "OK"

        if nchars < min_chars:
            status = "WARN"
            notes.append("字数偏少（约 %d 字 < 建议 %d 字）" % (nchars, min_chars))
        missing_probe = [p for p in probes if not re.search(p, text, re.I)]
        if missing_probe:
            if status == "OK":
                status = "WARN"
            notes.append("未检出关键内容：%s" % "、".join(missing_probe))

        # 命名规范检查（存在但命名不合规 → 单独 WARN）
        base = rel.rsplit("/", 1)[-1]
        if prefix and not base.startswith(prefix):
            items.append(Item(
                "L1", key + "#naming", label + "（命名规范）", "WARN",
                "文件 `%s` 未按 `%s` 前缀命名" % (base, prefix),
                "重命名为 `%s%s`（提交总则 §0 命名规范）" % (prefix, base),
                evidence=rel, severity="warn",
            ))

        ev = "%s（约 %d 字）" % (rel, nchars)
        if key == "AI日志":
            n = count_decision_nodes(text)
            ev += "；决策节点识别 %d 个（启发式）" % n
            if n < 3:
                status = "MISSING"
                notes.append("决策节点 < 3（识别到 %d）→ 触发红线 R1（rubric `no_ai_log`，封顶 5 分）" % n)

        items.append(Item("L1", key, label, status, "；".join(notes) or "通过", hint, evidence=ev))
    return items


def scaffold_six_piece(key, hint, prefix=None, student=None, challenge=None):
    banner = (
        "<!-- ⚠️ 本文件由 elite20-packager --scaffold 生成，全部字段为「待填」占位。\n"
        "     禁止直接提交本骨架。请本人用真实内容替换每一处「待填」。\n"
        "     生成时间：%s -->\n\n" % datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    bodies = {
        "方案草案": "# {name}_{cx}_方案草案\n\n> 要求：≥500 字，含「四个关卡问题」式自问自答。\n\n"
                    "## 一、我要解决什么问题\n\n待填\n\n## 二、四个关卡问题\n\n"
                    "**Q1 这件事真实存在吗？证据是什么？**\n\n待填\n\n"
                    "**Q2 为什么是我做？我有什么别人没有的条件？**\n\n待填\n\n"
                    "**Q3 做成的判定标准是什么？怎么证明做成了？**\n\n待填\n\n"
                    "**Q4 最大的风险是什么？失败了怎么办？**\n\n待填\n",
        "方案设计": "# {name}_{cx}_方案设计\n\n## 一、目标\n\n待填\n\n## 二、架构\n\n待填\n\n"
                    "## 三、技术选型与理由\n\n| 选项 | 候选 A | 候选 B | 我选 | 理由 |\n|---|---|---|---|---|\n| 待填 | 待填 | 待填 | 待填 | 待填 |\n\n"
                    "## 四、风险与应对\n\n| 风险 | 概率 | 影响 | 应对 |\n|---|---|---|---|\n| 待填 | 待填 | 待填 | 待填 |\n",
        "G1背书": "# {name}_{cx}_G1 群内发起背书\n\n"
                   "> ⚠️ 群内发起动作**只能本人做**。本文件只提供模板。\n\n"
                   "## 一、发起记录（待填）\n\n| 项目 | 内容 |\n|---|---|\n| 发起时间 | 待填 |\n| 发起群 | 待填 |\n| 消息截图/链接 | 待填 |\n\n"
                   "## 二、群内发起话术模板\n\n```\n大家好，我是{name}。我准备做 {cx}：<一句话说明>。\n"
                   "想确认三件事：1) 这个需求大家有没有？2) 有没有人已经在做，避免撞车？3) 有没有人愿意做我的第一批试用者？\n```\n\n"
                   "## 三、回应记录（待填）\n\n| 日期 | 群友 | 回应要点 |\n|---|---|---|\n| 待填 | 待填 | 待填 |\n",
        "AI日志": "# {name}_{cx}_AI 日志\n\n> 要求：≥3 个决策节点（建议 6–10 个）；每个节点必须写真实发生的命令、真实报错、真实返工。**宁少不假。**\n\n"
                   "### 决策节点 1：待填（一句话标题）\n\n- **背景**：待填\n- **AI 建议**：待填（附关键 prompt 原文）\n- **我的判断**：待填（采纳/修改/驳回，为什么）\n- **人工核验**：待填（实际跑的命令、查的文档、对的数据）\n- **结果**：待填（成功/失败/部分成功；失败要写清教训）\n\n"
                   "### 决策节点 2：待填\n\n（同上格式）\n\n### 决策节点 3：待填\n\n（同上格式）\n\n"
                   "---\n\n## AI 使用统计\n\n| 指标 | 数值 |\n|---|---|\n| 调用轮次 | 待填 |\n| 驳回次数 | 待填 |\n| 人为主导的关键决策数 | 待填 |\n| AI 最大帮助（1 例） | 待填 |\n| AI 最大误导（1 例） | 待填 |\n",
        "拿来说明": "# {name}_{cx}_拿来说明\n\n> 要求：复用来源表 + License + 改了什么。**不标 License = 红线。**\n\n"
                    "## 一、复用来源表\n\n| 来源 | 作者/组织 | 我拿了什么 | 原 License | 我的改动 |\n|---|---|---|---|---|\n| 待填 | 待填 | 待填 | 待填 | 待填 |\n\n"
                    "## 二、License 声明\n\n- 本包我原创部分：**待填（如 MIT / CC BY 4.0）**\n- 上游内容 License：**待填**\n"
                    "- 若上游为 AGPL 等强传染协议：另附 `LICENSE-CONTENT.md` 单独说明 —— 待填\n\n## 三、改了什么（可核验）\n\n| 我改了 | 原样 | 改后 | 为什么 |\n|---|---|---|---|\n| 待填 | 待填 | 待填 | 待填 |\n",
        "Portfolio条目": "# {name}_{cx}_Portfolio 条目\n\n**一句话价值**：待填（输入 ____，输出 ____，对谁有用）\n\n"
                         "**证据链接**\n\n| 证据 | 路径/链接 | 说明 |\n|---|---|---|\n| 包目录 | 待填 | 待填 |\n| 验证输出 | 待填 | 待填 |\n| 演示 | 待填 | 待填 |\n",
        "AAR": "# {name}_{cx}_AAR\n\n> 声明：七维为自拟维度，官方模板未随包提供。\n\n"
               "## 1. 接到挑战时我以为要做什么 vs 实际是什么\n\n待填\n\n## 2. 实际怎么做成的（时间线 + 关键转折）\n\n待填\n\n"
               "## 3. AI 在哪些环节最有用 / 哪些环节最不可靠\n\n待填\n\n## 4. 踩过的坑与修复\n\n待填\n\n"
               "## 5. 我对这套方法论的判断（可证伪的结论）\n\n待填\n\n## 6. 能力自评（1–5 分，逐项给证据）\n\n待填\n\n"
               "## 7. 如果重来一次会改变的三件事 + 尚未解决的问题\n\n待填\n",
    }
    body = bodies.get(key, "# {name}_{cx}_%s\n\n待填\n" % key)
    # 有真实姓名/挑战就把占位符换掉，避免同时生成 `姓名_CX_x.md` 和 `真名_CX_x.md` 两份
    name = student or "姓名"
    cx = challenge or "CX"
    body = body.replace("{name}", name).replace("{cx}", cx)
    return banner + body


# ---------------------------------------------------------------------------
# L2 仓库结构
# ---------------------------------------------------------------------------

def check_repo(pkg, files, dirs):
    items = []

    def need(key, label, globs, fix, severity="error", min_bytes=1, template=None):
        hits = match_files(files, globs)
        if not hits:
            sc = {template[0]: template[1]} if template else {}
            items.append(Item("L2", key, label, "MISSING",
                              "缺少 `%s`" % globs[0], fix, scaffold=sc))
            return None
        rel = hits[0]
        size = (pkg / rel).stat().st_size
        if size < min_bytes:
            items.append(Item("L2", key, label, "WARN",
                              "`%s` 只有 %d 字节，疑似空文件（红线信号：文件为空）" % (rel, size),
                              fix, evidence=rel))
        else:
            items.append(Item("L2", key, label, "OK", "通过", fix,
                              evidence="%s（%d 字节）" % (rel, size)))
        return rel

    need("README.md", "README", ["README.md"], "补 `README.md`，六段必备：是什么/解决什么问题/快速开始/示例/项目结构/技术栈 + AI 生成说明 + 借鉴来源",
         min_bytes=400, template=("README.md", scaffold_readme()))
    need("CHANGELOG.md", "CHANGELOG", ["CHANGELOG.md"], "补 `CHANGELOG.md`，写真实开发过程（含失败与返工），不要只写版本号",
         min_bytes=80, template=("CHANGELOG.md", scaffold_changelog()))
    lic = need("LICENSE", "LICENSE", ["LICENSE", "LICENSE.*", "LICENSE-*"], "补 `LICENSE`（代码 MIT）；若上游为 AGPL 等，另加 `LICENSE-CONTENT.md` 说明",
               min_bytes=200, template=("LICENSE", scaffold_license()))
    need("requirements.txt", "requirements.txt", ["requirements.txt"], "补 `requirements.txt`，只写真正用到的依赖，注明 Python 版本",
         min_bytes=10, template=("requirements.txt", "# Python 版本：待填（本项目实测 Python 3.9.6）\n# 每行一个依赖，只写真正用到的\n# 例：openpyxl>=3.1\n待填\n"))
    need("scripts/reproduce.sh", "scripts/reproduce.sh", ["scripts/reproduce.sh", "reproduce.sh"],
         "补 `scripts/reproduce.sh`：一条命令跑完全部自检，必须真跑通，输出贴进 README",
         min_bytes=80, template=("scripts/reproduce.sh", scaffold_reproduce()))
    need("tests/test_smoke.py", "tests/test_smoke.py", ["tests/test_smoke.py", "tests/*.py"],
         "补 `tests/test_smoke.py`：≥1 个冒烟测试，输出通过/失败计数，退出码非 0 表示失败",
         min_bytes=80, template=("tests/test_smoke.py", scaffold_smoke()))
    need("docs/文件对照表.md", "docs/文件对照表.md", ["docs/文件对照表.md", "*文件对照表*.md"],
         "补 `docs/文件对照表.md`：规范条目 ↔ 本包文件 一一对应",
         template=("docs/文件对照表.md", scaffold_generic("文件对照表",
                  "| 规范条目 | 本包对应文件 | 状态 |\n|---|---|---|\n| 待填 | 待填 | 待填 |\n")))
    need("docs/红线自测.md", "docs/红线自测.md", ["docs/红线自测.md", "*红线自测*.md"],
         "补 `docs/红线自测.md`：三条红线逐条自测 + 证据（命令 + 输出）",
         template=("docs/红线自测.md", scaffold_generic("红线自测",
                  "## 红线 1：AI 使用记录/迭代\n\n- 证据：待填\n- 自测结论：待填\n\n"
                  "## 红线 2：License 与拿来说明\n\n- 证据：待填\n- 自测结论：待填\n\n"
                  "## 红线 3：核心交付物齐全 + 可复现\n\n- 证据：待填\n- 自测结论：待填\n")))
    need("docs/群消息留痕.md", "docs/群消息留痕.md", ["docs/群消息留痕.md", "*群消息留痕*.md"],
         "补 `docs/群消息留痕.md`：G1/G3 群消息记录模板（**【待本人填】**，不许伪造）",
         template=("docs/群消息留痕.md", scaffold_generic("群消息留痕",
                  "> ⚠️ 本文件内容 **【待本人执行】填写**。禁止伪造群消息。\n\n"
                  "| 时间 | 群 | 动作 | 消息内容 | 截图 |\n|---|---|---|---|---|\n| 待填 | 待填 | 待填 | 待填 | 待填 |\n")))
    need("docs/demo.md", "docs/demo.md", ["docs/demo.md", "*demo*.md"],
         "补 `docs/demo.md`：演示步骤（别人照着能跑出来）",
         template=("docs/demo.md", scaffold_generic("demo",
                  "## 前置\n\n待填\n\n## 步骤\n\n```bash\n# 待填\n```\n\n## 预期输出\n\n待填\n")))
    need("G2验证报告_生成说明.md", "G2 验证报告生成说明", ["G2验证报告_生成说明.md", "*G2*.md"],
         "补 `G2验证报告_生成说明.md`：说明 G2 必须由官方 skill 产出，本包不提供手写版",
         template=("G2验证报告_生成说明.md", scaffold_g2()))
    need("00_先读我_待办清单.md", "00_先读我_待办清单", ["00_先读我*.md", "*待办清单*.md"],
         "补 `00_先读我_待办清单.md`：汇总全部 `【待赵怡涵执行】` 事项",
         template=("00_先读我_待办清单.md", scaffold_generic("先读我_待办清单",
                  "# 00 先读我 · 待办清单\n\n> 只有本人能做的动作，全部列在这里。**不许伪造已完成。**\n\n"
                  "- [ ] 【待本人执行】待填\n")))

    # 推荐项（缺失只 WARN）
    for key, label, globs, fix in [
        (".gitignore", ".gitignore（推荐）", [".gitignore"], "补 `.gitignore`（忽略 __pycache__/、.DS_Store、临时输出）"),
        ("LICENSE-CONTENT.md", "LICENSE-CONTENT.md（上游为 AGPL 等时必需）",
         ["LICENSE-CONTENT.md"], "若复用了 AGPL 等强传染协议内容，必须单列 `LICENSE-CONTENT.md` 说明"),
    ]:
        hits = match_files(files, globs)
        if not hits:
            items.append(Item("L2", key, label, "WARN", "未找到 `%s`" % globs[0], fix, severity="warn"))
        else:
            items.append(Item("L2", key, label, "OK", "通过", fix, evidence=hits[0]))

    # 内容级检查（WARN）
    items.extend(check_content_quality(pkg, files))
    return items


def check_content_quality(pkg, files):
    items = []

    readme = match_files(files, ["README.md"])
    if readme:
        text = read_text(pkg, readme[0])
        sections = {"是什么": r"是什么|what.{0,10}is",
                    "解决什么问题": r"解决.{0,6}问题|problem",
                    "快速开始": r"快速开始|快速上手|quick ?start|getting started|安装",
                    "示例": r"示例|例子|usage|example",
                    "项目结构": r"项目结构|目录结构|structure|tree",
                    "技术栈": r"技术栈|tech ?stack|依赖|依赖环境"}
        missing = [k for k, pat in sections.items() if not re.search(pat, text, re.I)]
        if missing:
            items.append(Item("L2", "README#sections", "README 六段必备", "WARN",
                              "未检出小节：%s" % "、".join(missing),
                              "《交付规范》§2 要求 README 含六段：是什么/解决什么问题/快速开始/示例/项目结构/技术栈",
                              evidence=readme[0], severity="warn"))
        else:
            items.append(Item("L2", "README#sections", "README 六段必备", "OK", "六段齐全",
                              "", evidence=readme[0]))
        if not re.search(r"AI\s*生成|AI\s*辅助|生成说明", text, re.I):
            items.append(Item("L2", "README#ai", "README 含 AI 生成说明", "WARN",
                              "未检出「AI 生成说明」",
                              "README 必须声明哪些部分由 AI 生成、人做了什么核验",
                              evidence=readme[0], severity="warn"))
        if not re.search(r"借鉴|参考|复用|来源", text):
            items.append(Item("L2", "README#credit", "README 含借鉴来源", "WARN",
                              "未检出「借鉴来源」",
                              "README 必须写明借鉴了谁的东西（并与 `拿来说明.md` 对齐）",
                              evidence=readme[0], severity="warn"))

    repro = match_files(files, ["scripts/reproduce.sh", "reproduce.sh"])
    if repro:
        text = read_text(pkg, repro[0])
        if re.search(r"^\s*exit\s+0\s*$", text, re.M) and not re.search(r"set -e", text):
            items.append(Item("L2", "reproduce#exit0", "reproduce.sh 未硬编码成功", "WARN",
                              "脚本里出现裸 `exit 0` 且没有 `set -e`",
                              "`exit 0` 会让失败也返回成功；改用 `set -euo pipefail` 并让退出码真实反映结果",
                              evidence=repro[0], severity="warn"))
        if not re.search(r"python3|pytest|bash|sh ", text):
            items.append(Item("L2", "reproduce#content", "reproduce.sh 内容有效性", "WARN",
                              "未检出任何实际执行命令",
                              "reproduce.sh 必须真的跑检查（至少调用 tests/ 下的测试）",
                              evidence=repro[0], severity="warn"))

    # .skill / 可执行产物结构
    for skill_file in match_files(files, ["*.skill"]):
        size = (pkg / skill_file).stat().st_size
        if size < 1024:
            items.append(Item("L2", "skill#size", ".skill 体积检查", "WARN",
                              "`%s` 仅 %d 字节，疑似空包或损坏" % (skill_file, size),
                              "用 `tar -tzf` 确认包含 SKILL.md 后再提交", evidence=skill_file, severity="warn"))
    return items


# ---------------------------------------------------------------------------
# L3 挑战专属交付物
# ---------------------------------------------------------------------------

def check_challenge_deliverables(pkg, files, registry, challenge):
    items = []
    if not challenge:
        items.append(Item("L3", "challenge#unknown", "挑战编号", "WARN",
                          "无法推断挑战编号",
                          "用 `--challenge CX` 显式指定，或把包目录命名为 `姓名_CX_提交包`", severity="warn"))
        return items
    entry = registry.get(challenge)
    if not entry:
        items.append(Item("L3", "challenge#noreg", "挑战注册表", "WARN",
                          "注册表中没有 %s 的定义" % challenge,
                          "在 `references/challenges_index.yaml` 里补充该挑战，或核对编号是否正确", severity="warn"))
        return items

    for req in entry.get("required", []):
        globs = req.get("globs") or []
        hits = rank_hits(match_files(files, globs))
        label = "挑战交付物：%s" % req.get("key", globs[0] if globs else "?")
        desc = req.get("desc", "")
        if hits:
            items.append(Item("L3", "C.%s" % req.get("key"), label, "OK", "通过", desc,
                              evidence="；".join(hits[:3]) + ("…" if len(hits) > 3 else "")))
        else:
            sc = {}
            if req.get("scaffold_name"):
                sc[req["scaffold_name"]] = scaffold_generic(
                    req.get("key", ""),
                    "> ⚠️ 本骨架由 elite20-packager 生成，全部为「待填」占位。\n\n待填\n")
            if any(g.endswith(".skill") for g in globs):
                sc.update(scaffold_skill_pack())
            items.append(Item("L3", "C.%s" % req.get("key"), label, "MISSING",
                              "%s 的专属交付物缺失（匹配 %s）" % (challenge, "/".join(globs)),
                              desc or "按 CHALLENGE.md「提交内容」表补齐", scaffold=sc))

    for note in entry.get("notes", []) or []:
        items.append(Item("L3", "note", "挑战提示", "INFO", str(note), ""))
    return items


# ---------------------------------------------------------------------------
# 三条红线
# ---------------------------------------------------------------------------

def check_redlines(pkg, files, prefix=None, student=None, challenge=None):
    items = []
    log_name = ("%sAI日志.md" % prefix) if prefix else "姓名_CX_AI日志.md"
    cred_name = ("%s拿来说明.md" % prefix) if prefix else "姓名_CX_拿来说明.md"

    # R1 AI 日志 + >=3 决策节点
    logs = match_files(files, ["*AI日志*.md", "*ai.?log*.md"])
    if not logs:
        items.append(Item("R", "R1", "红线 1：AI 日志与迭代痕迹", "MISSING",
                          "包内没有 AI 日志文件 → 触发 rubric `no_ai_log`（封顶 5 分）",
                          "补 `姓名_CX_AI日志.md`，≥3 个决策节点，写真实命令/报错/返工",
                          scaffold={log_name: scaffold_six_piece("AI日志", "", prefix, student, challenge)}))
    else:
        text = "\n".join(read_text(pkg, f) for f in logs)
        n = count_decision_nodes(text)
        iterations = len(re.findall(r"v2|v3|第[二三四]轮|迭代|返工|重跑", text))
        if n < 3:
            items.append(Item("R", "R1", "红线 1：AI 日志与迭代痕迹", "MISSING",
                              "决策节点只识别到 %d 个（要求 ≥3）→ 触发 rubric `no_ai_log`" % n,
                              "补足到 ≥3 个；每个节点写：背景 / AI 建议 / 我的判断 / 人工核验 / 结果",
                              evidence="；".join(logs[:2])))
        else:
            items.append(Item("R", "R1", "红线 1：AI 日志与迭代痕迹", "OK",
                              "决策节点识别 %d 个（启发式），迭代/返工词命中 %d 处" % (n, iterations),
                              "保持", evidence="；".join(logs[:2])))

    # R2 拿来说明标 License
    creds = match_files(files, ["*拿来说明*.md", "*credits*.md"])
    lic_files = match_files(files, ["LICENSE", "LICENSE.*", "LICENSE-*"])
    if not creds:
        items.append(Item("R", "R2", "红线 2：拿来说明标明 License", "MISSING",
                          "包内没有 `拿来说明.md`",
                          "补 `姓名_CX_拿来说明.md`：复用来源表 + License + 改了什么",
                          scaffold={cred_name: scaffold_six_piece("拿来说明", "", prefix, student, challenge)}))
    else:
        text = "\n".join(read_text(pkg, f) for f in creds)
        has_lic_word = bool(re.search(r"License|许可证|MIT|Apache|AGPL|GPL|CC[ -]?BY|BSD|版权|公有领域", text, re.I))
        if not has_lic_word:
            items.append(Item("R", "R2", "红线 2：拿来说明标明 License", "MISSING",
                              "`%s` 里没有任何 License / 许可证字样" % creds[0],
                              "写明：我原创部分是 MIT / CC BY 4.0；上游内容是什么 License；改了哪些",
                              evidence=creds[0]))
        elif not lic_files:
            items.append(Item("R", "R2", "红线 2：拿来说明标明 License", "WARN",
                              "拿来说明写了 License，但包内没有 `LICENSE` 文件",
                              "补一份 `LICENSE`（代码 MIT；上游 AGPL 等另加 `LICENSE-CONTENT.md`）",
                              evidence=creds[0]))
        else:
            items.append(Item("R", "R2", "红线 2：拿来说明标明 License", "OK",
                              "拿来说明含 License 声明，且包内有 %s" % lic_files[0],
                              "保持", evidence="%s + %s" % (creds[0], lic_files[0])))

    # R3 可复现脚本
    repro = match_files(files, ["scripts/reproduce.sh", "reproduce.sh"])
    tests = match_files(files, ["tests/*.py", "*test_smoke*.py"])
    if not repro:
        items.append(Item("R", "R3a", "红线 3：可复现脚本", "MISSING",
                          "没有 `scripts/reproduce.sh`",
                          "补一条命令跑完全部自检的脚本，并真实执行一次把输出贴进 README",
                          scaffold={"scripts/reproduce.sh": scaffold_reproduce()}))
    else:
        size = (pkg / repro[0]).stat().st_size
        items.append(Item("R", "R3a", "红线 3：可复现脚本", "OK" if size >= 80 else "WARN",
                          "`%s`（%d 字节）" % (repro[0], size),
                          "脚本必须真跑通；把真实终端输出贴进 README「验证」一节",
                          evidence=repro[0]))
    if not tests:
        items.append(Item("R", "R3b", "红线 3：冒烟测试", "MISSING",
                          "没有 tests/ 下的冒烟测试",
                          "补 `tests/test_smoke.py`：≥1 个用例，打印通过/失败计数，失败时退出码非 0",
                          scaffold={"tests/test_smoke.py": scaffold_smoke()}))
    else:
        items.append(Item("R", "R3b", "红线 3：冒烟测试", "OK",
                          "找到 %d 个测试文件" % len(tests),
                          "保持；脚本全绿 ≠ 东西是对的，内容正确性另写说明",
                          evidence="；".join(tests[:3])))
    return items


# ---------------------------------------------------------------------------
# 骨架模板
# ---------------------------------------------------------------------------

SCAFFOLD_BANNER = (
    "<!-- ⚠️ 本文件由 elite20-packager --scaffold 生成，内容全部为「待填」占位。\n"
    "     这不是可直接提交的成品。请本人用真实内容逐项替换。\n"
    "     生成时间：{ts} -->\n\n"
)


def scaffold_generic(title, body):
    return SCAFFOLD_BANNER.format(ts=datetime.now().strftime("%Y-%m-%d %H:%M")) + "# %s\n\n%s" % (title, body)


def scaffold_readme():
    return SCAFFOLD_BANNER.format(ts=datetime.now().strftime("%Y-%m-%d %H:%M")) + """# 待填（项目名）

## 是什么

待填

## 解决什么问题

待填

## 快速开始

```bash
# 待填
```

## 示例

待填

## 项目结构

```
待填
```

## 技术栈

待填

## 验证

```
待填（reproduce.sh 的真实输出）
```

## AI 生成说明

待填（哪些由 AI 生成、人做了什么核验）

## 借鉴来源

待填（与 `拿来说明.md` 对齐）
"""


def scaffold_changelog():
    return SCAFFOLD_BANNER.format(ts=datetime.now().strftime("%Y-%m-%d %H:%M")) + """# CHANGELOG

> 写真实开发过程，包括失败与返工，不要只写版本号。

## [未发布] 待填

### 新增
- 待填

### 修复
- 待填（写清真实报错）

### 返工
- 待填（哪一步推翻重做，为什么）
"""


def scaffold_license():
    year = datetime.now().year
    return "MIT License\n\nCopyright (c) %d 待填（姓名）\n\n" % year + \
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n" \
        "of this software and associated documentation files (the \"Software\"), to deal\n" \
        "in the Software without restriction, including without limitation the rights\n" \
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" \
        "copies of the Software, and to permit persons to whom the Software is\n" \
        "furnished to do so, subject to the following conditions:\n\n" \
        "The above copyright notice and this permission notice shall be included in all\n" \
        "copies or substantial portions of the Software.\n\n" \
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" \
        "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" \
        "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" \
        "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" \
        "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" \
        "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n" \
        "SOFTWARE.\n"


def scaffold_reproduce():
    return """#!/usr/bin/env bash
# 待填（由 elite20-packager --scaffold 生成的骨架：把下面的占位换成真实命令，跑通后再提交）
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/3 环境 =="
python3 -V
# 待填：依赖检查

echo "== 2/3 冒烟测试 =="
python3 tests/test_smoke.py

echo "== 3/3 主流程 =="
# 待填：真正跑一次主产物

echo "全部自检通过"
"""


def scaffold_smoke():
    return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""待填（由 elite20-packager --scaffold 生成的骨架）

跑法：python3 tests/test_smoke.py
约定：全绿退出码 0，有失败退出码 1，并打印 通过/失败 计数。
"""

import sys

PASSED = 0
FAILED = 0


def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("PASS  %s %s" % (name, detail))
    else:
        FAILED += 1
        print("FAIL  %s %s" % (name, detail))


def main():
    # 待填：把下面换成对真实产物的断言
    check("骨架存在", True, "(占位用例，请替换)")

    print("-" * 40)
    print("通过 %d / 失败 %d" % (PASSED, FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
'''


def scaffold_skill_pack():
    """给「可执行技能包」这一项生成最小可用的技能源码骨架 + 打包脚本。"""
    name = "你的技能名"
    d = "skill_src/%s" % name
    skill_md = '''
---
name: your-skill-name        # 待填：kebab-case，与目录名一致
description: >
  待填：一段话说明「输入什么、输出什么、什么时候该触发」。
  把 3-5 个触发短语写进去（中英文都要），例如：
  "整理提交包", "检查我缺什么文件", "package self-check"。
  描述写得好不好，直接决定这个技能会不会被触发 —— 这是最容易翻车的一环。
---

# 待填（技能标题）

## Purpose（为什么需要这个技能）

待填：谁在什么场景下会痛，现在怎么凑合，这个技能省掉哪一步。

## Input

待填：接受什么（路径 / 文件 / 一句话），有没有可选参数。

## Workflow（分步骤）

### Step 1 — 待填
### Step 2 — 待填
### Step 3 — 待填

## Output

待填：产出什么文件、什么格式、放在哪。

## Edge Cases（边界情况）

- 输入路径不存在 → 待填
- 输入为空 → 待填
- 依赖缺失 → 待填

## Examples（使用示例）

```
待填：一句真实可复制的调用示例
```
'''

    build_sh = """#!/usr/bin/env bash
# 待填：把技能名改掉，确认路径对，然后跑通。
set -euo pipefail
NAME="%s"
cd "$(dirname "$0")/.."
test -f "skill_src/$NAME/SKILL.md" || { echo "缺少 skill_src/$NAME/SKILL.md"; exit 1; }
tar -czf "$NAME.skill" -C skill_src "$NAME"
echo "已生成 $NAME.skill"
tar -tzf "$NAME.skill"
""" % name

    return {
        "%s/SKILL.md" % d: skill_md,
        "%s/scripts/.gitkeep" % d: "",
        "%s/references/.gitkeep" % d: "",
        "scripts/build_skill.sh": build_sh,
    }


def scaffold_g2():
    return SCAFFOLD_BANNER.format(ts=datetime.now().strftime("%Y-%m-%d %H:%M")) + """# G2 验证报告 · 生成说明

## 为什么本包不提供手写版 G2

《提交总则》§9 明确：**G2 禁止手写**，必须由官方 skill 产出。

## 获取方式

1. 待填（官方 skill 的获取路径 / 群内文件）
2. 待填（运行命令）

## 真实运行记录（**【待本人执行】**）

| 项目 | 内容 |
|---|---|
| 运行时间 | 待填 |
| 命令 | 待填 |
| 输出文件 | 待填 |

> ⚠️ 未运行前，本表保持「待填」，不得伪造。
"""


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

STATUS_MARK = {"OK": "✅", "WARN": "⚠️", "MISSING": "❌", "INFO": "ℹ️"}
LAYER_NAME = {"L1": "L1 六件套", "L2": "L2 仓库结构", "L3": "L3 挑战专属交付物", "R": "红线自检"}


def summarize(items):
    s = {"OK": 0, "WARN": 0, "MISSING": 0, "INFO": 0}
    for it in items:
        s[it.status] = s.get(it.status, 0) + 1
    return s


def render_markdown(pkg, student, challenge, registry, items, generated_at):
    s = summarize(items)
    problems = [i for i in items if i.is_problem]
    total_checked = len([i for i in items if i.status != "INFO"])
    pass_rate = (100.0 * s["OK"] / total_checked) if total_checked else 0.0

    L = []
    L.append("# Elite20 提交包自检报告 · `%s`\n" % pkg.name)
    L.append("> 由 **elite20-packager** 生成 · 生成时间 %s" % generated_at)
    L.append("> 自检口径：《Elite20 挑战提交总则》§3 六件套 / §5.1 仓库结构 / 本挑战 `rubric.json` 红线")
    L.append("> ⚠️ 本报告是**结构自检**，只证明「文件在、命名对、关键内容有」；**内容正确性必须另外验证**（脚本全绿 ≠ 东西是对的）。\n")
    L.append("| 项目 | 值 |")
    L.append("|---|---|")
    L.append("| 包路径 | `%s` |" % pkg)
    L.append("| 学生姓名（推断） | %s |" % (student or "未识别"))
    L.append("| 挑战编号（推断） | %s |" % (challenge or "未识别"))
    L.append("| 检查项总数 | %d |" % total_checked)
    L.append("| ✅ 通过 | %d |" % s["OK"])
    L.append("| ⚠️ 警告 | %d |" % s["WARN"])
    L.append("| ❌ 缺失/不合格 | %d |" % s["MISSING"])
    L.append("| 通过率（启发式，非官方评分） | %.1f%% |" % pass_rate)
    L.append("")

    if problems:
        L.append("## 一、总览：必须先修的 %d 项\n" % len(problems))
        L.append("| # | 层级 | 检查项 | 状态 | 问题 |")
        L.append("|---|---|---|---|---|")
        for n, it in enumerate(problems, 1):
            L.append("| %d | %s | %s | %s | %s |" % (
                n, LAYER_NAME.get(it.layer, it.layer), it.label,
                STATUS_MARK.get(it.status, "?"), it.detail.replace("|", "\\|")))
        L.append("")
    else:
        L.append("## 一、总览：无缺失项 🎉\n")
        L.append("结构层全绿。**注意：这只说明文件账本齐了，不说明内容是对的。**\n")

    L.append("## 二、缺失矩阵（按层展开）\n")
    for layer in ["L1", "L2", "L3", "R"]:
        group = [i for i in items if i.layer == layer]
        if not group:
            continue
        L.append("### %s\n" % LAYER_NAME[layer])
        L.append("| 状态 | 检查项 | 证据 | 说明 |")
        L.append("|---|---|---|---|")
        for it in group:
            L.append("| %s | %s | %s | %s |" % (
                STATUS_MARK.get(it.status, "?"), it.label,
                (it.evidence or "—").replace("|", "\\|"),
                (it.detail or "—").replace("|", "\\|")))
        L.append("")

    L.append("## 三、逐项修复建议\n")
    if problems:
        for n, it in enumerate(problems, 1):
            L.append("### %d. [%s] %s\n" % (n, it.status, it.label))
            L.append("- **问题**：%s" % it.detail)
            L.append("- **怎么修**：%s" % (it.fix or "见《交付规范》对应章节"))
            if it.scaffold:
                L.append("- **可用骨架**（`--scaffold` 会生成，内容全是「待填」占位，**不许直接提交**）：")
                for rp in it.scaffold:
                    L.append("  - `%s`" % rp)
            L.append("")
    else:
        L.append("无需修复。建议继续做**内容级**复核：\n")
        L.append("1. 逐字读一遍 AI 日志，确认每个决策节点都有真实命令输出佐证；")
        L.append("2. 让一个没参与的人按 `docs/demo.md` 跑一遍；")
        L.append("3. 核对 `docs/文件对照表.md` 与挑战 `CHALLENGE.md`「提交内容」表是否一一对应。\n")

    L.append("## 四、挑战交付物清单（来自官方 `challenge.json`）\n")
    if challenge and challenge in registry:
        entry = registry[challenge]
        L.append("- 挑战：**%s**" % entry.get("title", challenge))
        L.append("- 官方原始 `required_deliverables`：`%s`" % entry.get("raw_deliverables", "—"))
        L.append("- 来源：`%s`\n" % entry.get("source_json", "—"))
        L.append("| 官方要求 | 匹配规则 | 本包命中 |")
        L.append("|---|---|---|")
        for req in entry.get("required", []):
            L.append("| %s | `%s` | %s |" % (
                req.get("key", ""), "` / `".join(req.get("globs", [])),
                "✅" if req.get("_hit") else "❌"))
        L.append("")
    else:
        L.append("未识别挑战编号，跳过。用 `--challenge CX` 显式指定可启用本表。\n")

    L.append("## 五、三条红线结论\n")
    red = [i for i in items if i.layer == "R"]
    for it in red:
        L.append("- %s **%s** — %s" % (STATUS_MARK.get(it.status, "?"), it.label, it.detail))
    L.append("")
    L.append("---")
    L.append("*elite20-packager v1.0 · 本报告可重复生成：`python3 scripts/elite20_packager.py <包目录> --challenge %s`*" % (challenge or "CX"))
    return "\n".join(L)


def render_xlsx(path, pkg, student, challenge, items, generated_at):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        return False, "未安装 openpyxl，跳过 Excel 输出"

    wb = Workbook()
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="2F5597")
    status_fill = {
        "OK": PatternFill("solid", fgColor="D9EAD3"),
        "WARN": PatternFill("solid", fgColor="FFF2CC"),
        "MISSING": PatternFill("solid", fgColor="F4CCCC"),
        "INFO": PatternFill("solid", fgColor="EFEFEF"),
    }

    def style_header(ws, ncol):
        for c in range(1, ncol + 1):
            cell = ws.cell(row=1, column=c)
            cell.font = head_font
            cell.fill = head_fill
            cell.alignment = Alignment(vertical="center")
        ws.freeze_panes = "A2"

    def autosize(ws, widths):
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    s = summarize(items)

    # Sheet 1 总览
    ws = wb.active
    ws.title = "总览"
    ws.append(["项目", "值"])
    rows = [
        ("包路径", str(pkg)), ("学生姓名", student or "未识别"), ("挑战编号", challenge or "未识别"),
        ("生成时间", generated_at), ("检查项总数", s["OK"] + s["WARN"] + s["MISSING"]),
        ("通过 OK", s["OK"]), ("警告 WARN", s["WARN"]), ("缺失 MISSING", s["MISSING"]),
        ("必须先修的问题数", len([i for i in items if i.is_problem])),
        ("口径", "提交总则 §3 六件套 / §5.1 仓库结构 / rubric 红线；结构自检，不等于内容正确"),
    ]
    for r in rows:
        ws.append(list(r))
    style_header(ws, 2)
    autosize(ws, [26, 96])

    # Sheet 2 缺失矩阵
    ws2 = wb.create_sheet("缺失矩阵")
    ws2.append(["层级", "检查项", "状态", "严重度", "问题/说明", "证据"])
    for it in items:
        ws2.append([LAYER_NAME.get(it.layer, it.layer), it.label, it.status,
                    it.severity, it.detail, it.evidence])
        ws2.cell(row=ws2.max_row, column=3).fill = status_fill.get(it.status, status_fill["INFO"])
    style_header(ws2, 6)
    autosize(ws2, [18, 34, 10, 10, 62, 40])

    # Sheet 3 修复建议
    ws3 = wb.create_sheet("修复建议")
    ws3.append(["优先级", "检查项", "怎么修", "可生成的骨架文件"])
    problems = [i for i in items if i.is_problem]
    for n, it in enumerate(problems, 1):
        ws3.append([n, it.label, it.fix or "见《交付规范》", "；".join(it.scaffold.keys())])
    style_header(ws3, 4)
    autosize(ws3, [8, 34, 70, 34])

    # Sheet 4 挑战清单
    ws4 = wb.create_sheet("挑战交付物清单")
    ws4.append(["挑战", "标题", "官方 required_deliverables", "匹配规则", "本包命中"])
    if challenge and challenge in load_registry(DEFAULT_REGISTRY):
        entry = load_registry(DEFAULT_REGISTRY)[challenge]
        for req in entry.get("required", []):
            ws4.append([challenge, entry.get("title", ""), entry.get("raw_deliverables", ""),
                        " / ".join(req.get("globs", [])), "是" if req.get("_hit") else "否"])
    style_header(ws4, 5)
    autosize(ws4, [10, 26, 40, 40, 10])

    wb.save(path)
    return True, "已写出 %s" % path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_checks(pkg: Path, registry, challenge_arg=None, student_arg=None):
    files = rel_files(pkg)
    dirs = rel_dirs(pkg)
    student, challenge = infer_student_challenge(pkg, files, challenge_arg, student_arg)

    prefix = ("%s_%s_" % (student, challenge)) if (student and challenge) else None

    items = []
    items.extend(check_six_piece(pkg, files, student, challenge))
    items.extend(check_repo(pkg, files, dirs))
    items.extend(check_challenge_deliverables(pkg, files, registry, challenge))
    items.extend(check_redlines(pkg, files, prefix, student, challenge))

    # 给注册表条目补 _hit 标记，供报告表格使用
    if challenge and challenge in registry:
        for req in registry[challenge].get("required", []):
            req["_hit"] = bool(match_files(files, req.get("globs") or []))
    return items, student, challenge, files


def do_scaffold(pkg: Path, items, dry_run=False):
    """为缺失项生成骨架。已存在的文件绝不覆盖。"""
    created, skipped = [], []
    seen = set()
    for it in items:
        if it.status != "MISSING" or not it.scaffold:
            continue
        for relpath, content in it.scaffold.items():
            if relpath in seen:      # 同一路径被多条检查项提到 → 只生成一次
                continue
            seen.add(relpath)
            target = pkg / relpath
            if target.exists():
                skipped.append(relpath)
                continue
            created.append(relpath)
            if dry_run:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            if relpath.endswith(".sh"):
                os.chmod(target, 0o755)
    return created, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="elite20_packager.py",
        description="Elite20 提交包自检器：三层结构检查 + 三条红线自检 + 双格式报告 + 骨架生成")
    ap.add_argument("package", help="提交包目录路径")
    ap.add_argument("--challenge", "-c", default=None, help="挑战编号，如 C2 / C4 / C10H（不填则自动推断）")
    ap.add_argument("--student", "-s", default=None, help="学生姓名（不填则从目录名推断）")
    ap.add_argument("--outdir", "-o", default=None, help="报告输出目录（默认 <包目录>/reports）")
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="挑战清单 YAML 路径")
    ap.add_argument("--scaffold", action="store_true", help="为缺失项生成「待填」骨架文件（不覆盖已存在文件）")
    ap.add_argument("--dry-run", action="store_true", help="配合 --scaffold：只列出会生成什么，不写盘")
    ap.add_argument("--no-xlsx", action="store_true", help="不生成 Excel，只生成 Markdown")
    ap.add_argument("--json", action="store_true", help="额外输出机器可读 JSON 到 stdout")
    ap.add_argument("--quiet", "-q", action="store_true", help="安静模式")
    args = ap.parse_args(argv)

    pkg = Path(args.package).expanduser().resolve()
    if not pkg.exists():
        print("[错误] 路径不存在：%s" % pkg, file=sys.stderr)
        return 2
    if not pkg.is_dir():
        print("[错误] 不是目录：%s" % pkg, file=sys.stderr)
        return 2

    registry_path = Path(args.registry).expanduser()
    registry = load_registry(registry_path)

    items, student, challenge, files = run_checks(pkg, registry, args.challenge, args.student)
    s = summarize(items)
    problems = [i for i in items if i.is_problem]

    outdir = Path(args.outdir).expanduser() if args.outdir else (pkg / "reports")
    outdir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md_path = outdir / "packager_report.md"
    md_path.write_text(render_markdown(pkg, student, challenge, registry, items, generated_at), encoding="utf-8")

    xlsx_path = outdir / "packager_report.xlsx"
    xlsx_ok, xlsx_msg = (False, "已用 --no-xlsx 跳过")
    if not args.no_xlsx:
        xlsx_ok, xlsx_msg = render_xlsx(xlsx_path, pkg, student, challenge, items, generated_at)

    created, skipped = ([], [])
    if args.scaffold:
        created, skipped = do_scaffold(pkg, items, dry_run=args.dry_run)

    if not args.quiet:
        print("elite20-packager v1.0 · 包自检")
        print("包路径   : %s" % pkg)
        print("学生/挑战: %s / %s   （扫描到 %d 个文件）" % (student or "未识别", challenge or "未识别", len(files)))
        print("-" * 64)
        for layer in ["L1", "L2", "L3", "R"]:
            group = [i for i in items if i.layer == layer]
            if not group:
                continue
            real = [i for i in group if i.status != "INFO"]   # INFO 是提示，不是检查项
            ok = len([i for i in real if i.status == "OK"])
            print("%-28s 通过 %2d / %2d" % (LAYER_NAME[layer], ok, len(real)))
            for it in group:
                if it.is_problem:
                    print("   %s %s — %s" % (STATUS_MARK[it.status], it.label, it.detail))
        print("-" * 64)
        print("合计：✅ %d  ⚠️ %d  ❌ %d   |  必须先修 %d 项" % (s["OK"], s["WARN"], s["MISSING"], len(problems)))
        print("Markdown : %s" % md_path)
        print("Excel    : %s" % (xlsx_path if xlsx_ok else "（%s）" % xlsx_msg))
        if args.scaffold:
            print("骨架生成 : 新建 %d 个%s" % (len(created), "" if not args.dry_run else "（dry-run，未写盘）"))
            for c in created:
                print("   + %s" % c)
            for sk in skipped:
                print("   = %s（已存在，跳过，绝不覆盖）" % sk)
        if problems:
            print("\n下一步：查看报告的「三、逐项修复建议」，或加 --scaffold 生成待填骨架。")
        else:
            print("\n结构层全绿。注意：这只说明文件账本齐了，不说明内容是对的。")

    if args.json:
        print(json.dumps({
            "package": str(pkg), "student": student, "challenge": challenge,
            "generated_at": generated_at, "summary": s,
            "problem_count": len(problems),
            "items": [i.as_dict() for i in items],
            "reports": {"markdown": str(md_path), "xlsx": str(xlsx_path) if xlsx_ok else None},
            "scaffold_created": created,
        }, ensure_ascii=False, indent=2))

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
