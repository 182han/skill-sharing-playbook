---
name: elite20-packager
description: >
  Elite20 submission-package self-checker. Give it ONE folder path (a student's
  `姓名_CX_提交包` directory) and it audits that package against three layers —
  (1) the seven "六件套" Markdown deliverables named `姓名_CX_*.md`,
  (2) the repo structure (README / CHANGELOG / LICENSE / requirements.txt /
  scripts/reproduce.sh / tests/ / docs/ …),
  (3) the challenge-specific required deliverables read from the official
  `challenge.json` `required_deliverables` + `CHALLENGE.md` submission table —
  then runs the three red-line self-checks (AI log with ≥3 decision nodes,
  attribution file with a License, reproducible script + smoke test) and writes
  `packager_report.md` + `packager_report.xlsx`. With `--scaffold` it creates
  skeleton files for everything missing, filled with 「待填」 placeholders only —
  never fake content.
  Use whenever someone says "check my submission package", "what am I missing",
  "提交包自检", "帮我看看缺什么文件", "这个包能不能交", "package self-check",
  "audit my C2 folder", "Elite20 交付检查", "六件套齐了吗", "红线自测",
  "missing artifacts", "rubric red flags", or points at a 提交包 directory and
  asks whether it is complete / compliant / submittable. Also use before every
  submission, after renaming or restructuring a package, when a grader flagged
  `missing_artifacts`, or when you want to bootstrap an empty package from
  scratch. Works for every Elite20 challenge (C1–C10H), not just one.
---

# elite20-packager — Elite20 提交包自检器

## Purpose

Every Elite20 challenge asks for the same evidence ledger: the seven 六件套
Markdown files, a repo skeleton, and a few challenge-specific artifacts. In
practice the single most common way to lose points is simply **not having a
file** — the rubric's `missing_artifacts` red flag caps the score at 5.

This skill is a **receipt checker**. You hand it a folder; it tells you exactly
what is missing, which red line is tripped, and how to fix each item. It can
also hand you blank-but-correctly-shaped skeletons so you never start from an
empty directory again.

Analogy: like a tax-preparation checklist. It does not file your taxes and it
does not verify that your numbers are truthful — it tells you which forms are
missing from the envelope before you seal it.

## What this skill is NOT

- It is **not** a grader. The pass rate it prints is a heuristic bookkeeping
  number, **not** a prediction of the rubric score.
- It does **not** verify that content is true. `reproduce.sh` going green only
  proves "the files exist and run" — content correctness needs separate evidence.
- It will **never** invent an official requirement. Every challenge-specific
  check traces back to a token in the official `challenge.json`
  `required_deliverables`; the generator hard-fails otherwise.
- `--scaffold` **never** writes fake content. Every generated file is a `待填`
  placeholder with a banner saying "do not submit this skeleton as-is".

## Prerequisites

- Python 3.8+ (tested on 3.9.6, macOS arm64)
- `openpyxl` for the Excel report (`pip install openpyxl`) — without it the
  Markdown report still works; add `--no-xlsx` to skip Excel explicitly
- `pyyaml` for reading the challenge registry (`pip install pyyaml`)
- No network access is required at run time

Verify:

```bash
python3 -c "import openpyxl, yaml; print('deps ok')"
```

## Input

Accept **one** required argument and optional flags:

| Argument | Meaning |
|---|---|
| `<PACKAGE_DIR>` | path to the submission package folder, e.g. `~/Desktop/赵怡涵_C2_提交包` |
| `--challenge CX` | force the challenge id (`C1`…`C10H`); otherwise inferred from the folder name or from the most common `_CX_` token in filenames |
| `--student NAME` | force the student name; otherwise inferred from the folder name |
| `--outdir DIR` | where to write reports (default: `<PACKAGE_DIR>/reports`) |
| `--scaffold` | also create `待填` skeletons for missing items (never overwrites existing files) |
| `--dry-run` | with `--scaffold`: list what would be created, write nothing |
| `--no-xlsx` | Markdown only |
| `--json` | also print a machine-readable JSON summary |
| `--registry PATH` | alternate challenge registry YAML |

## Output

| File | Contents |
|---|---|
| `packager_report.md` | overview + missing matrix by layer + per-item fix advice + red-line verdict |
| `packager_report.xlsx` | 4 sheets: 总览 / 缺失矩阵 / 修复建议 / 挑战交付物清单 |
| (optional) skeletons | only with `--scaffold` |

Exit codes: `0` = no blocking problems · `1` = at least one missing/unqualified
item · `2` = bad usage or path.

## Workflow

### Step 1 — Confirm the target folder

Ask for the folder path if it was not given. Expand `~`, check it is a directory.
If the folder name does not contain a `CX` token and the contents are ambiguous,
ask which challenge it is rather than guessing wrong.

```bash
PKG="<user-provided-path>"
ls -la "$PKG" | head -30
```

### Step 2 — Run the checker

```bash
python3 scripts/elite20_packager.py "$PKG" --challenge C4
```

Omit `--challenge` when the folder is already named `姓名_CX_提交包`.

### Step 3 — Read the three layers

**L1 六件套** — every package needs these seven, named `姓名_CX_*.md`:
方案草案 / 方案设计 / G1背书 / AI日志 / 拿来说明 / Portfolio条目 / AAR.
The checker also probes content: 方案草案 ≥500 字 with the "四个关卡问题"
self-Q&A, 方案设计 ≥800 字 covering 目标/架构/选型理由/风险, AI日志 with ≥3
decision nodes, 拿来说明 carrying a License statement, AAR ≥800 字. A file that
exists but is 3 lines long is reported as a warning, not a pass.

**L2 仓库结构** — README.md (six required sections + AI-generation note +
attribution), CHANGELOG.md, LICENSE, requirements.txt, scripts/reproduce.sh,
tests/test_smoke.py, docs/{文件对照表,红线自测,群消息留痕,demo}.md,
G2验证报告_生成说明.md, 00_先读我_待办清单.md, plus recommended .gitignore and
LICENSE-CONTENT.md. Empty or near-empty files are flagged — "文件为空" is an
explicit negative signal in the rubric.

**L3 挑战专属交付物** — read from `references/challenges_index.yaml`, which is
generated from the official `challenge.json` files. For C4 that means
`*skill说明*`, `*.skill`, `*教学说明*`, `*demo*`, `*AI日志*` — nothing more.

### Step 4 — Read the red-line verdict

Three red lines, each worth up to 5 points of damage in the rubric:

| Red line | Rule |
|---|---|
| R1 | an AI log exists **and** ≥3 decision nodes are detectable |
| R2 | 拿来说明 states a License **and** a `LICENSE` file exists |
| R3 | `scripts/reproduce.sh` exists and is non-trivial, and `tests/` has a smoke test |

Decision-node detection is deliberately generous, because people label them
differently: the script counts numbered `### 决策 N` / `### 节点 N` headings,
inline `决策 1` mentions, and the literal phrase `决策节点`, then takes the
maximum.

### Step 5 — Fix, then re-run

Work down the "三、逐项修复建议" section in order. After fixing, run the
checker again — the report is fully reproducible and safe to re-run.

### Step 6 — (optional) Bootstrap an empty package

```bash
python3 scripts/elite20_packager.py ~/Desktop/赵怡涵_C5_提交包 \
    --challenge C5 --student 赵怡涵 --scaffold --dry-run   # preview first
python3 scripts/elite20_packager.py ~/Desktop/赵怡涵_C5_提交包 \
    --challenge C5 --student 赵怡涵 --scaffold             # then write
```

Every generated file opens with:

```html
<!-- ⚠️ 本文件由 elite20-packager --scaffold 生成，全部字段为「待填」占位。
     禁止直接提交本骨架。请本人用真实内容替换每一处「待填」。 -->
```

`--scaffold` never overwrites an existing file; it prints `= path（已存在，跳过）`.

## Regenerating the challenge registry

The registry is bundled so the skill works offline. Refresh it when the
official challenge packs change:

```bash
python3 scripts/build_challenge_index.py \
    --packs-root ~/Desktop/EduSeed挑战资料包 \
    --out references/challenges_index.yaml
```

The generator refuses to add a requirement that is not a token of the official
`required_deliverables`, and asserts that the number of checks equals the number
of official tokens. This is intentional: a self-checker that invents
requirements produces false "missing" reports and destroys trust.

## Edge Cases

- **Path does not exist / is a file** → exits 2 with a clear message.
- **Folder name has no `CX` token** → falls back to the most frequent `_CX_`
  token in filenames; if still ambiguous, emits a warning and skips L3. Tell the
  user to pass `--challenge`.
- **Openpyxl missing** → Markdown still written, Excel skipped with a message.
- **Package contains vendored source (e.g. a whole downloaded course folder)** →
  candidate files are ranked so the package's own top-level artifacts win over
  nested third-party files. This matters: `*设计*.md` would otherwise match a
  downloaded `w03-design-doc-template.md`.
- **Empty package** → 28 missing items, `--scaffold` produces 23 skeletons.
- **`.skill` file smaller than 1 KB** → flagged as a suspected empty archive.
- **Non-UTF8 Markdown** → falls back to GBK before giving up.
- **Very large package** → file walking skips `.git`, `__pycache__`,
  `node_modules`, and binary caches.

## Honesty Rules (read before using the output)

1. Never report "已发布 / 已截图 / 已提交" from this tool's output. It only sees
   files on disk.
2. Actions only the student can perform — posting to the group (G1/G3), running
   the official G2 skill, real user trials, anything needing API keys or GPUs —
   must be written as `【待本人执行】` in `00_先读我_待办清单.md`, never faked.
3. A green report means the *ledger* balances. It does not mean the content is
   correct.
4. Degraded implementations (no GPU, no API key, offline fallback) must be
   declared in README「已知缺口」and in the AAR.

## Examples

```bash
# 最常用：检查一个已经存在的包
python3 scripts/elite20_packager.py ~/Desktop/赵怡涵_C2_提交包

# 显式指定挑战 + 只看 Markdown
python3 scripts/elite20_packager.py ~/Desktop/赵怡涵_C1_提交包 --challenge C1 --no-xlsx

# 给别人做批量巡检（20 个挑战包）
for d in ~/Desktop/*_提交包; do
  python3 scripts/elite20_packager.py "$d" -q -o /tmp/audit/$(basename "$d")
done
grep -l "必须先修" /tmp/audit/*/packager_report.md

# 从零起一个新包
python3 scripts/elite20_packager.py ~/Desktop/赵怡涵_C5_提交包 \
    --challenge C5 --student 赵怡涵 --scaffold
```

Real run against an actually-passing package looks like:

```
elite20-packager v1.0 · 包自检
包路径   : /Users/zhanghao/Desktop/赵怡涵_C2_提交包
学生/挑战: 赵怡涵 / C2   （扫描到 37 个文件）
----------------------------------------------------------------
L1 六件套                       通过  7 /  7
L2 仓库结构                      通过 14 / 15
L3 挑战专属交付物                   通过  4 /  4
红线自检                         通过  4 /  4
----------------------------------------------------------------
合计：✅ 29  ⚠️ 1  ❌ 0   |  必须先修 0 项
```

## Files

```
elite20-packager/
├── SKILL.md                            （本文件，主指令）
├── scripts/
│   ├── elite20_packager.py             （核心：三层检查 + 红线 + 报告 + scaffold）
│   └── build_challenge_index.py        （从官方 challenge.json 生成注册表）
├── references/
│   ├── challenges_index.yaml           （C1–C10H 官方交付物注册表，自动生成）
│   └── checklist.yaml                  （六件套/仓库/红线规则的人类可读镜像）
└── examples/
    ├── README.md                       （真实运行记录索引）
    └── run_demo.sh                      （一条命令复现 examples 里的输出）
```
