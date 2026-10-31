#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_challenge_index.py — 从官方挑战资料包生成 `references/challenges_index.yaml`

数据来源（只读，不修改官方文件）：
  1) <PACKS_ROOT>/*/challenge.json  的 `required_deliverables` 字段（逗号分隔的通配符串）
  2) <PACKS_ROOT>/*/CHALLENGE.md    的「提交内容」表（用于补充精确命名与说明）
  3) 内置的少量人工注解（CURATED），只写「匹配规则怎么解释」和「修复建议」，
     不改变官方要求本身。

用法：
  python3 build_challenge_index.py --packs-root "~/Desktop/EduSeed挑战资料包" \
                                   --out ../references/challenges_index.yaml
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

# 人工注解。
#
# ⚠️ 踩坑记录（v1.0 修的真实错误）：
#   我最初给 C1 加了 `*翻译方法*.md`、给 C2 加了 `paper.pdf` 作为「额外要求」，
#   自以为是地从 CHALLENGE.md 正文推出来的。实际核对 C1/C2 的「提交内容」表后确认：
#   **官方没有这两项**（C1 只要求 README/*AI日志*/*AAR*/*拿来说明*；
#   C2 只要求 paper.tex/references.bib/*AI日志*/*AAR*）。
#   结果是对《赵怡涵_C1_提交包》误报了一条「挑战交付物缺失」。
#   → 教训：**自检器绝不能发明官方要求**。extras 只允许用来「细化已有 token 的匹配规则」
#     和「补充说明文字」，不允许新增要求项。下面的 `refine` 走的是合并路径，
#     不是追加路径，且最终有 assert 兜底。
CURATED = {
    "C4": {
        # 把官方 token 细化成「更贴近 CHALLENGE.md 提交内容表」的匹配规则；
        # 每一项都必须能对上 required_deliverables 里的某个 token，否则生成时报错。
        "refine": [
            {"token": "*skill说明*", "key": "Skill 说明文档",
             "globs": ["*skill说明*.md"],
             "desc": "解决什么问题 / 使用场景 / 输入输出 / 使用步骤 / 真实案例"},
            {"token": "*.skill", "key": "可执行技能包",
             "globs": ["*技能名*.py"],
             "desc": "可安装的 .skill（tar.gz）或等价 .py / .md；必须真能装、能跑"},
            {"token": "*教学说明*", "key": "教学说明",
             "globs": ["*教学说明*.md"],
             "desc": "如何上手、常见坑、优化技巧——关键是教别人用"},
            {"token": "*demo*", "key": "Demo",
             "globs": ["*demo*.mp4", "*demo*.png", "*demo*.jpg", "*demo*"],
             "desc": "视频 / 截图 / live demo；无法录制的写清待办并给录屏脚本"},
        ],
        "notes": [
            "C4 评分不看技能多厉害，看「被使用次数」——交付包必须包含传播动作证据（群内发布 + 试用邀请 + 反馈收集）。",
            "传播动作只能本人做：缺口请写成 `【待本人执行】`，不得伪造使用次数。",
        ],
    },
}

GENERIC_DESC = "官方 challenge.json 的 required_deliverables 要求项"


def token_to_globs(token: str):
    t = token.strip()
    if not t:
        return []
    if "*" in t or "?" in t:
        return [t]
    return [t]


def human_key(token: str):
    t = token.strip().strip("*")
    return t or token.strip()


def parse_deliverables(raw: str):
    if not raw:
        return []
    return [p for p in re.split(r"[,\n]", raw) if p.strip()]


def read_challenge_md_table(md_path: Path):
    """粗读 CHALLENGE.md 的「提交内容」表，返回 [(文件, 命名格式, 说明)]。"""
    if not md_path.exists():
        return []
    txt = md_path.read_text(encoding="utf-8", errors="replace")
    rows = []
    for line in txt.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if set(cells[0]) <= set("-: ") or cells[0] in ("文件", "挑战"):
            continue
        if cells[1].startswith("命名格式") or cells[1].startswith("---"):
            continue
        if re.search(r"姓名|YourName|Name_", cells[1] + cells[0]):
            rows.append(tuple(cells[:3]))
    return rows


def build(packs_root: Path):
    challenges = {}
    for cj in sorted(packs_root.glob("*/challenge.json")):
        try:
            data = json.loads(cj.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = data.get("title", cj.parent.name)
        m = re.match(r"\s*(C\d+[A-Z]?)", title)
        if not m:
            m = re.match(r"\s*(C\d+[A-Z]?)", cj.parent.name)
        if not m:
            continue
        cid = m.group(1)
        raw = data.get("required_deliverables") or data.get("deliverables") or ""
        curated = CURATED.get(cid, {})

        required = []
        by_token = {}
        for token in parse_deliverables(raw):
            entry = {
                "key": human_key(token), "globs": token_to_globs(token),
                "desc": GENERIC_DESC,
                "source": "challenge.json:required_deliverables",
                "origin_token": token.strip(),
            }
            required.append(entry)
            by_token[token.strip()] = entry

        def norm(s):
            return s.replace("*", "").replace("?", "").strip().lower()

        # refine 只做「细化已有 token」，绝不新增官方没写的要求
        for extra in curated.get("refine", []):
            token = extra["token"]
            target = by_token.get(token)
            if target is None:
                raise SystemExit(
                    "[生成中止] CURATED.refine 里的 token %r 不在 %s 的 required_deliverables 中：%r\n"
                    "自检器不允许发明官方要求，请先核对 CHALLENGE.md 再改。" % (token, cid, raw))
            for gg in extra["globs"]:
                if not any(norm(x) == norm(gg) for x in target["globs"]):
                    target["globs"].append(gg)
            if extra.get("key"):
                target["key"] = extra["key"]
            if extra.get("desc"):
                target["desc"] = extra["desc"]
            target["source"] = "challenge.json + CHALLENGE.md:提交内容表"

        # 兜底：官方 token 数 == 检查项数，一条不多一条不少
        n_tokens = len(parse_deliverables(raw))
        if len(required) != n_tokens:
            raise SystemExit("[生成中止] %s 的检查项数 %d != 官方 required_deliverables token 数 %d"
                             % (cid, len(required), n_tokens))

        md_rows = read_challenge_md_table(cj.parent / "CHALLENGE.md")

        challenges[cid] = {
            "title": title,
            "source_json": str(cj.relative_to(packs_root)),
            "raw_deliverables": raw,
            "submit_table": [{"文件": r[0], "命名格式": r[1], "说明": r[2]} for r in md_rows],
            "required": required,
            "notes": curated.get("notes", []),
        }

    out = {
        "version": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_from": str(packs_root),
        "note": "本文件由 build_challenge_index.py 从官方 challenge.json + CHALLENGE.md 生成；"
                "人工只加了「匹配规则解释」与「C4 传播机制提示」，未改动官方要求。",
        "challenges": challenges,
    }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成 challenges_index.yaml")
    ap.add_argument("--packs-root", required=True, help="官方挑战资料包根目录")
    ap.add_argument("--out", required=True, help="输出 YAML 路径")
    args = ap.parse_args(argv)

    root = Path(args.packs_root).expanduser().resolve()
    if not root.is_dir():
        print("[错误] 资料包根目录不存在：%s" % root)
        return 2

    data = build(root)
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    import yaml
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Elite20 挑战交付物注册表（自动生成，勿手改）\n")
        fh.write("# 重新生成：python3 scripts/build_challenge_index.py --packs-root <资料包> --out <本文件>\n")
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False, width=1000)

    n = len(data["challenges"])
    print("已写出 %s" % out)
    print("收录挑战 %d 个：%s" % (n, ", ".join(sorted(data["challenges"]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
