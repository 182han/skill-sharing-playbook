#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_smoke.py — 赵怡涵_C4_提交包 冒烟测试

跑法：python3 tests/test_smoke.py
约定：全绿退出码 0；有失败退出码 1；末尾打印 通过/失败 计数。

覆盖 10 组断言：
  T1  包内六件套 + 仓库通用文件齐全
  T2  AI 日志决策节点 >= 3（红线 R1）
  T3  拿来说明含 License（红线 R2）
  T4  scripts/reproduce.sh 存在且可执行（红线 R3）
  T5  .skill 是合法 tar.gz，顶层目录 == frontmatter.name
  T6  SKILL.md frontmatter 有 name/description，正文 < 500 行
  T7  挑战注册表：C4 检查项数 == 官方 required_deliverables token 数
  T8  自检器能在一个空包上正确报缺失，且在完整包上返回 0
  T9  --scaffold 生成的骨架只含「待填」占位、绝不覆盖已有文件
  T10 Excel 报告 4 个 sheet；.skill 与 skill_src 同步（防止发旧包）
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG_NAME = "赵怡涵_C4_提交包"

PASSED = 0
FAILED = 0
DETAILS = []


def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("PASS  %s %s" % (name, ("— " + detail) if detail else ""))
    else:
        FAILED += 1
        print("FAIL  %s %s" % (name, ("— " + detail) if detail else ""))
        DETAILS.append("%s %s" % (name, detail))


def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def run(args, **kw):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, **kw)


# ---------------------------------------------------------------------------
# T1 文件账本
# ---------------------------------------------------------------------------

def t1_files_present():
    six = ["方案草案", "方案设计", "G1背书", "AI日志", "拿来说明", "Portfolio条目", "AAR"]
    for key in six:
        hits = list(ROOT.glob("*_C4_*%s*.md" % key))
        check("T1 六件套 %s" % key, bool(hits), hits[0].name if hits else "缺失")
    for rel in ["README.md", "CHANGELOG.md", "LICENSE", "requirements.txt",
                "scripts/reproduce.sh", "tests/test_smoke.py",
                "docs/文件对照表.md", "docs/红线自测.md", "docs/群消息留痕.md", "docs/demo.md",
                "G2验证报告_生成说明.md", "00_先读我_待办清单.md",
                "赵怡涵_C4_skill说明.md", "赵怡涵_C4_教学说明.md"]:
        p = ROOT / rel
        check("T1 文件 %s" % rel, p.is_file(), "%d 字节" % p.stat().st_size if p.is_file() else "缺失")


# ---------------------------------------------------------------------------
# T2 / T3 / T4 红线
# ---------------------------------------------------------------------------

def t2_ai_log():
    logs = list(ROOT.glob("*_C4_AI日志.md"))
    check("T2 AI 日志存在", bool(logs))
    if not logs:
        return
    text = logs[0].read_text(encoding="utf-8", errors="replace")
    # 直接复用生产代码的计数函数，而不是在测试里重写一遍。
    # （早期版本这里是自己写的一份简化计数，结果和 生产代码 漂移了：
    #   它把正文里的交叉引用也算上，打印出 34 个，而真实是 10 个。
    #   测试里复制生产逻辑＝迟早对不上。）
    sys.path.insert(0, str(ROOT / "skill_src" / "elite20-packager" / "scripts"))
    from elite20_packager import count_decision_nodes
    n = count_decision_nodes(text)
    check("T2 决策节点 >= 3（红线 R1）", n >= 3, "识别到 %d 个" % n)
    check("T2 未把正文交叉引用算成节点（应与真实节点数一致）", n <= 15,
          "识别到 %d 个；若远超真实节点数说明计数被交叉引用污染" % n)
    check("T2 AI 使用统计段存在", "AI 使用统计" in text or "使用统计" in text)


def t3_credits():
    hits = list(ROOT.glob("*_C4_拿来说明.md"))
    check("T3 拿来说明存在", bool(hits))
    if not hits:
        return
    text = hits[0].read_text(encoding="utf-8", errors="replace")
    check("T3 含 License 声明（红线 R2）",
          bool(re.search(r"License|许可证|MIT|Apache|AGPL|GPL|CC[ -]?BY|BSD", text, re.I)))
    check("T3 引用了 materials 里的两个 .skill",
          "skill-explainer" in text and "wechat-doc-mapper" in text)
    check("T3 LICENSE 文件存在", (ROOT / "LICENSE").is_file())


def t4_reproduce():
    p = ROOT / "scripts" / "reproduce.sh"
    check("T4 reproduce.sh 存在（红线 R3）", p.is_file())
    if not p.is_file():
        return
    check("T4 reproduce.sh 可执行位", os.access(p, os.X_OK), oct(p.stat().st_mode)[-3:])
    text = p.read_text(encoding="utf-8", errors="replace")
    check("T4 用 set -euo pipefail", "set -euo pipefail" in text)
    check("T4 会跑冒烟测试", "test_smoke.py" in text)
    # 早期版本这里写的是"脚本里不能出现 exit 0"——太naive：合法的成功路径本来就要 exit 0。
    # 真正要防的是「无论成败都返回 0」。判据改为：必须有失败退出路径，且不是无条件 exit 0。
    check("T4 有失败退出路径（exit 1）", "exit 1" in text)
    check("T4 成功/失败退出码分离",
          "exit 0" in text and "exit 1" in text)


# ---------------------------------------------------------------------------
# T5 / T6 .skill 结构
# ---------------------------------------------------------------------------

def t5_skill_archive():
    skills = list(ROOT.glob("*_C4_*.skill"))
    check("T5 .skill 存在", bool(skills), skills[0].name if skills else "缺失")
    if not skills:
        return None
    path = skills[0]
    try:
        tf = tarfile.open(path, "r:gz")
    except Exception as exc:
        check("T5 是合法 tar.gz", False, str(exc))
        return None
    check("T5 是合法 tar.gz", True, "%.1f KB" % (path.stat().st_size / 1024.0))
    names = tf.getnames()
    tops = sorted({n.split("/")[0] for n in names})
    check("T5 顶层单目录", len(tops) == 1, str(tops))
    check("T5 无 AppleDouble 垃圾", not any(Path(n).name.startswith("._") for n in names))
    check("T5 含 SKILL.md", "elite20-packager/SKILL.md" in names)
    check("T5 含 scripts/", any(n.startswith("elite20-packager/scripts/") and n.endswith(".py") for n in names))
    check("T5 含 references/", any(n.startswith("elite20-packager/references/") and n.endswith(".yaml") for n in names))
    check("T5 含 examples/", any(n.startswith("elite20-packager/examples/") and n.count("/") == 2 for n in names))
    tf.close()
    return path


def t6_skill_md():
    md = ROOT / "skill_src" / "elite20-packager" / "SKILL.md"
    check("T6 SKILL.md 存在", md.is_file())
    if not md.is_file():
        return
    text = md.read_text(encoding="utf-8")
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)
    check("T6 有 YAML frontmatter", len(parts) >= 3)
    if len(parts) < 3:
        return
    fm = parts[1]
    check("T6 frontmatter 有 name", bool(re.search(r"^name:\s*\S+", fm, re.M)))
    check("T6 frontmatter 有 description", bool(re.search(r"^description:", fm, re.M)))
    check("T6 name 是 kebab-case", bool(re.search(r"^name:\s*elite20-packager\s*$", fm, re.M)))
    body_lines = len(parts[2].strip().split("\n"))
    check("T6 正文 < 500 行", body_lines < 500, "%d 行" % body_lines)
    for sec in ["Purpose", "Workflow", "Edge Cases", "Examples"]:
        check("T6 含 %s 小节" % sec, sec.lower() in parts[2].lower())


# ---------------------------------------------------------------------------
# T7 注册表
# ---------------------------------------------------------------------------

def t7_registry():
    try:
        import yaml
    except ImportError:
        check("T7 pyyaml 可用", False, "未安装 pyyaml，跳过")
        return
    reg = ROOT / "skill_src" / "elite20-packager" / "references" / "challenges_index.yaml"
    check("T7 注册表存在", reg.is_file())
    if not reg.is_file():
        return
    d = yaml.safe_load(reg.read_text(encoding="utf-8"))
    ch = d.get("challenges", {})
    check("T7 覆盖 >= 20 个挑战", len(ch) >= 20, "实际 %d 个" % len(ch))

    c4 = ch.get("C4", {})
    raw = c4.get("raw_deliverables", "")
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    reqs = c4.get("required", [])
    check("T7 C4 检查项数 == 官方 token 数",
          len(reqs) == len(tokens), "%d vs %d" % (len(reqs), len(tokens)))
    origins = [r.get("origin_token") for r in reqs]
    check("T7 每个检查项都能追溯到官方 token",
          all(o in tokens for o in origins), str(origins))
    check("T7 未发明官方要求（C1 不含翻译方法）",
          "翻译方法" not in json.dumps(ch.get("C1", {}), ensure_ascii=False))
    check("T7 未发明官方要求（C2 不含论文 PDF 必填）",
          all(r.get("origin_token") in
              [t.strip() for t in ch.get("C2", {}).get("raw_deliverables", "").split(",") if t.strip()]
              for r in ch.get("C2", {}).get("required", [])))


# ---------------------------------------------------------------------------
# T8 自检器行为
# ---------------------------------------------------------------------------

def build_fixture(root: Path):
    """造一个「账本齐全」的假包，用于验证自检器返回 0。"""
    # 夹具必须「真的够厚」，否则会踩到字数阈值的 WARN——
    # 而这本身是对的：一个 AAR 只有 610 字的包，确实不该被判为「账本齐全」。
    FILL = "这是一段用于填充夹具的正文内容，用来把字数抬到规范建议线以上。" * 40
    six = {
        "方案草案": "## 一\n关卡问题 自问自答 " + FILL,
        "方案设计": "## 目标\n架构 模块 分层 技术选型理由 风险 流程 pipeline\n" + FILL,
        "G1背书": "G1 群内发起 背书 模板 " + FILL,
        "AI日志": "".join("### 决策节点 %d：标题\n- 背景：x\n- AI 建议：y\n- 我的判断：z\n- 人工核验：跑命令\n- 结果：成功\n" % i
                       for i in range(1, 5)) + "## AI 使用统计\n" + FILL,
        "拿来说明": "复用来源表 License MIT 改了什么 " + FILL,
        "Portfolio条目": "一句话价值 证据 链接 /path 文件 " + FILL,
        "AAR": "## 1 维度 七维\n重来 改进 下次\n" + FILL,
    }
    who = root.name.split("_")[0]          # 从目录名取学生名，保证与 --student 推断一致
    for k, v in six.items():
        (root / ("%s_C4_%s.md" % (who, k))).write_text(v, encoding="utf-8")

    (root / "README.md").write_text(
        "# 是什么\n## 解决什么问题\n## 快速开始\n## 示例\n## 项目结构\n## 技术栈\n"
        "AI 生成说明\n借鉴来源\n" + "内容。" * 100, encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# CHANGELOG\n## 1.0\n- 新增" + "内容。" * 30, encoding="utf-8")
    (root / "LICENSE").write_text("MIT License\n" + "Permission is hereby granted. " * 20, encoding="utf-8")
    (root / "requirements.txt").write_text("openpyxl>=3.1\npyyaml>=6.0\n", encoding="utf-8")
    (root / "G2验证报告_生成说明.md").write_text("G2 禁止手写\n" + "内容。" * 30, encoding="utf-8")
    (root / "00_先读我_待办清单.md").write_text("# 待办\n- 【待本人执行】x\n", encoding="utf-8")

    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / "reproduce.sh").write_text(
        "#!/usr/bin/env bash\n"
        "# 夹具用的最小可复现脚本：一条命令跑完冒烟测试，退出码真实反映结果\n"
        "set -euo pipefail\n"
        "cd \"$(dirname \"$0\")/..\"\n"
        "echo '== 环境 =='\n"
        "python3 -V\n"
        "echo '== 冒烟测试 =='\n"
        "python3 tests/test_smoke.py\n"
        "echo '全部自检通过'\n", encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_smoke.py").write_text(
        "#!/usr/bin/env python3\n"
        "# 夹具用的最小冒烟测试：打印通过/失败计数，失败时退出码非 0\n"
        "import sys\n"
        "PASSED = 0\n"
        "FAILED = 0\n"
        "def check(name, cond):\n"
        "    global PASSED, FAILED\n"
        "    if cond:\n"
        "        PASSED += 1\n"
        "    else:\n"
        "        FAILED += 1\n"
        "    print(('PASS  ' if cond else 'FAIL  ') + name)\n"
        "def main():\n"
        "    check('夹具占位断言', True)\n"
        "    print('通过 %d / 失败 %d' % (PASSED, FAILED))\n"
        "    return 1 if FAILED else 0\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n", encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    for f, body in [("文件对照表.md", "| 规范条目 | 文件 |\n|---|---|\n| a | b |\n"),
                    ("红线自测.md", "## 红线 1\n证据\n## 红线 2\n证据\n## 红线 3\n证据\n"),
                    ("群消息留痕.md", "| 时间 | 群 |\n|---|---|\n| 待填 | 待填 |\n"),
                    ("demo.md", "## 前置\n## 步骤\n```bash\nls\n```\n")]:
        (root / "docs" / f).write_text(body, encoding="utf-8")

    # C4 专属交付物
    (root / "李四_C4_skill说明.md").write_text("# skill 说明\n" + "内容。" * 30, encoding="utf-8")
    (root / "李四_C4_教学说明.md").write_text("# 教学说明\n" + "内容。" * 30, encoding="utf-8")
    (root / "李四_C4_demo").mkdir(exist_ok=True)
    (root / "李四_C4_demo" / "记录.md").write_text("demo 记录\n", encoding="utf-8")
    with tarfile.open(root / "李四_C4_x.skill", "w:gz") as tf:
        p = root / "_tmp_skill" / "x" / "SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_text("x", encoding="utf-8")
        tf.add(p.parent, arcname="x")
    shutil.rmtree(root / "_tmp_skill")


def t8_checker_behaviour():
    checker = ROOT / "skill_src" / "elite20-packager" / "scripts" / "elite20_packager.py"
    check("T8 自检器脚本存在", checker.is_file())
    if not checker.is_file():
        return

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 8a：空包必须报缺失
        empty = tmp / "王五_C4_提交包"
        empty.mkdir()
        r = run([str(checker), str(empty), "--challenge", "C4", "--no-xlsx", "-q",
                 "-o", str(tmp / "out_empty")])
        check("T8a 空包退出码为 1", r.returncode == 1, "exit=%d" % r.returncode)
        (tmp / "out_empty").mkdir(exist_ok=True)
        r2 = run([str(checker), str(empty), "--challenge", "C4", "--no-xlsx", "-q",
                  "--json", "-o", str(tmp / "out_empty")])
        try:
            payload = json.loads(r2.stdout)
        except Exception:
            payload = {}
        check("T8a JSON 可解析", bool(payload), "items=%d" % len(payload.get("items", [])))
        check("T8a 空包缺失项 >= 20", payload.get("summary", {}).get("MISSING", 0) >= 20,
              str(payload.get("summary")))
        check("T8a 报告文件已生成", (tmp / "out_empty" / "packager_report.md").is_file())

        # 8b：账本齐全的包必须返回 0
        full = tmp / "李四_C4_提交包"
        full.mkdir()
        build_fixture(full)
        r3 = run([str(checker), str(full), "--challenge", "C4", "--no-xlsx", "-q",
                  "--json", "-o", str(tmp / "out_full")])
        try:
            p3 = json.loads(r3.stdout)
        except Exception:
            p3 = {}
        problems = [i for i in p3.get("items", []) if i["status"] == "MISSING"]
        check("T8b 齐全包退出码为 0", r3.returncode == 0,
              "exit=%d 缺失=%s" % (r3.returncode, [i["label"] for i in problems][:5]))

        # 8c：Excel 报告
        r4 = run([str(checker), str(full), "--challenge", "C4", "-q", "-o", str(tmp / "out_full")])
        xlsx = tmp / "out_full" / "packager_report.xlsx"
        check("T10a Excel 报告已生成", xlsx.is_file())
        if xlsx.is_file():
            try:
                from openpyxl import load_workbook
                wb = load_workbook(xlsx)
                check("T10a Excel 4 个 sheet", len(wb.sheetnames) == 4, str(wb.sheetnames))
            except ImportError:
                check("T10a openpyxl 可用", False, "未安装 openpyxl")

        # 8d：--scaffold 只写「待填」占位，且不覆盖已有文件
        blank = tmp / "赵六_C4_提交包"
        blank.mkdir()
        keep = blank / "README.md"
        keep.write_text("# 我自己写的，不许被覆盖\n", encoding="utf-8")
        run([str(checker), str(blank), "--challenge", "C4", "--student", "赵六",
             "--scaffold", "--no-xlsx", "-q", "-o", str(tmp / "out_scaffold")])
        check("T8d README 未被覆盖", "不许被覆盖" in keep.read_text(encoding="utf-8"))
        made = sorted(p for p in blank.rglob("*") if p.is_file() and p.name != "README.md")
        check("T8d 生成了骨架文件", len(made) >= 15, "%d 个" % len(made))
        check("T8d 骨架含真实姓名前缀",
              (blank / "赵六_C4_AI日志.md").is_file(),
              str([p.name for p in made if p.name.startswith("赵六")][:3]))
        scaffold_text = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                                  for p in made if p.suffix in (".md", ".sh", ".py"))
        check("T8d 骨架标了「待填」占位", "待填" in scaffold_text)
        check("T8d 骨架标了禁止直接提交", "禁止直接提交" in scaffold_text)
        check("T8d 骨架没被算成已完成（再跑一次仍报缺失）",
              run([str(checker), str(blank), "--challenge", "C4", "--no-xlsx", "-q",
                   "-o", str(tmp / "out_scaffold2")]).returncode == 1)


# ---------------------------------------------------------------------------
# T10 .skill 与 skill_src 同步
# ---------------------------------------------------------------------------

def t10_sync(skill_path):
    if not skill_path:
        check("T10b .skill 与源码同步", False, "没有 .skill 可校验")
        return
    with tempfile.TemporaryDirectory() as td:
        with tarfile.open(skill_path, "r:gz") as tf:
            tf.extractall(td)
        packed = Path(td) / "elite20-packager"
        src = ROOT / "skill_src" / "elite20-packager"
        diffs = []
        for f in sorted(src.rglob("*")):
            if not f.is_file() or "__pycache__" in str(f) or f.name == ".DS_Store":
                continue
            rel = f.relative_to(src)
            other = packed / rel
            if not other.is_file():
                diffs.append("缺 %s" % rel)
            elif other.read_bytes() != f.read_bytes():
                diffs.append("内容不一致 %s" % rel)
        check("T10b .skill 与 skill_src 同步（不是发旧包）", not diffs, "；".join(diffs[:4]))


# ---------------------------------------------------------------------------
# T9 诚实性
# ---------------------------------------------------------------------------

def t9_honesty():
    plan = ROOT / "赵怡涵_C4_传播计划.md"
    check("T9 传播计划存在", plan.is_file())
    if plan.is_file():
        text = plan.read_text(encoding="utf-8")
        check("T9 传播动作标了【待赵怡涵执行】", "【待赵怡涵执行】" in text)
    todo = read("00_先读我_待办清单.md")
    check("T9 待办清单标了【待赵怡涵执行】", "【待赵怡涵执行】" in todo)
    # 不许出现伪造的使用记录
    # 只在「断言句」里找伪造痕迹；带否定/警告语境的行不算
    # （早期版本没做这层过滤，把「如果这里出现"已发布"那一定是造假」这种警告句也误判成伪造）
    NEG = re.compile(r"不许|不得|禁止|造假|伪造|如果|一旦|绝不能|❌|红线|模板|待执行|未开始|保持为空|暂时|暂无")
    CLAIM = re.compile(r"已有\s*\d+\s*人使用|使用次数[:：]\s*[1-9]\d*|已发布|已截图|已提交|反馈良好")
    fake = []
    for rel in ["README.md", "赵怡涵_C4_skill说明.md", "赵怡涵_C4_传播计划.md",
                "赵怡涵_C4_Portfolio条目.md", "赵怡涵_C4_方案草案.md", "赵怡涵_C4_方案设计.md"]:
        for line in read(rel).splitlines():
            if CLAIM.search(line) and not NEG.search(line):
                fake.append("%s: %s" % (rel, line.strip()[:60]))
    check("T9 未伪造使用次数/发布记录", not fake, str(fake[:3]))


def main():
    print("=" * 70)
    print("赵怡涵_C4_提交包 · 冒烟测试")
    print("包根目录：%s" % ROOT)
    print("=" * 70)
    t1_files_present()
    t2_ai_log()
    t3_credits()
    t4_reproduce()
    skill = t5_skill_archive()
    t6_skill_md()
    t7_registry()
    t8_checker_behaviour()
    t9_honesty()
    t10_sync(skill)

    print("-" * 70)
    print("通过 %d / 失败 %d" % (PASSED, FAILED))
    if FAILED:
        print("失败清单：")
        for d in DETAILS:
            print("  - %s" % d)
    print("-" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
