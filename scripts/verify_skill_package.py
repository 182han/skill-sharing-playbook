#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_skill_package.py — 校验 `.skill` 包结构是否真的「能装能用」

检查项（任何一项 FAIL 都会让退出码非 0）：
  S1 是合法的 gzip tar 归档（tarfile 能打开）
  S2 顶层只有一个目录，且目录名 == SKILL.md frontmatter 的 name
  S3 包内存在 SKILL.md（且不在子目录深处）
  S4 SKILL.md 有 YAML frontmatter，且含非空 name + description
  S5 name 是 kebab-case
  S6 description 长度合理（>=80 字符）且含触发短语线索
  S7 SKILL.md 正文行数 < 500（三层加载机制的「渐进披露」要求）
  S8 体积合理（1 KB ~ 5 MB）
  S9 归档内没有绝对路径 / `..` 路径穿越 / 隐藏垃圾文件（.DS_Store/__pycache__）
  S10 归档内每个 .py 文件都能通过语法编译（py_compile），保证「装上就能跑」
  S11 若声明了 scripts/ 或 references/ 目录，则目录内非空

用法：
  python3 scripts/verify_skill_package.py <path/to/xxx.skill>
  python3 scripts/verify_skill_package.py <path/to/skill_src/技能名>   # 也支持校验源码目录

退出码：0 = 全部 PASS；1 = 有 FAIL
"""

from __future__ import annotations

import io
import py_compile
import re
import sys
import tarfile
import tempfile
from pathlib import Path

PASS, FAIL, WARN = [], [], []


def ok(name, detail=""):
    PASS.append((name, detail))
    print("PASS  %-46s %s" % (name, detail))


def bad(name, detail=""):
    FAIL.append((name, detail))
    print("FAIL  %-46s %s" % (name, detail))


def warn(name, detail=""):
    WARN.append((name, detail))
    print("WARN  %-46s %s" % (name, detail))


def parse_frontmatter(text):
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)
    if len(parts) < 3:
        return None, text
    try:
        import yaml
        fm = yaml.safe_load(parts[1]) or {}
    except ImportError:
        fm = {}
        for line in parts[1].splitlines():
            m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
            if m:
                fm[m.group(1)] = m.group(2).strip()
    except Exception:
        return None, parts[2]
    return fm, parts[2]


def verify_dir(skill_dir: Path, label):
    """校验解压后的技能目录。"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        bad("S3 SKILL.md 存在", "在 %s 里没找到 SKILL.md" % skill_dir)
        return None

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(text)
    if fm is None:
        bad("S4 YAML frontmatter", "SKILL.md 开头没有 `---` 包裹的 frontmatter")
        return None

    name = (fm.get("name") or "").strip() if isinstance(fm.get("name"), str) else fm.get("name")
    desc = (fm.get("description") or "").strip() if isinstance(fm.get("description"), str) else fm.get("description")

    if name:
        ok("S4a frontmatter.name 非空", name)
    else:
        bad("S4a frontmatter.name 非空", "name 缺失或为空")

    if desc:
        ok("S4b frontmatter.description 非空", "长度 %d 字符" % len(desc))
    else:
        bad("S4b frontmatter.description 非空", "description 缺失或为空")

    if name and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        ok("S5 name 是 kebab-case", name)
    elif name:
        bad("S5 name 是 kebab-case", "%r 含大写/下划线/空格" % name)

    if desc and len(desc) >= 80:
        ok("S6 description 足够具体", "%d 字符" % len(desc))
    elif desc:
        warn("S6 description 足够具体", "只有 %d 字符，容易不触发" % len(desc))

    trigger_hits = len(re.findall(r"Use whenever|trigger|when the user|说|当用户|whenever someone", desc or "", re.I))
    if trigger_hits:
        ok("S6b description 含触发短语", "%d 处触发语线索" % trigger_hits)
    else:
        warn("S6b description 含触发短语", "没看到明显的触发条件描述")

    body_lines = len(body.strip().split("\n"))
    if body_lines < 500:
        ok("S7 正文 < 500 行", "%d 行" % body_lines)
    else:
        bad("S7 正文 < 500 行", "%d 行，违反渐进披露" % body_lines)

    for sub in ("scripts", "references", "examples"):
        d = skill_dir / sub
        if d.is_dir():
            n = len([p for p in d.rglob("*") if p.is_file()])
            if n:
                ok("S11 %s/ 非空" % sub, "%d 个文件" % n)
            else:
                warn("S11 %s/ 非空" % sub, "目录存在但是空的")

    # S10：所有 .py 语法可编译
    pyfiles = sorted(skill_dir.rglob("*.py"))
    if not pyfiles:
        warn("S10 脚本可编译", "包内没有 .py（纯指令技能也合法）")
    else:
        broken = []
        for py in pyfiles:
            try:
                py_compile.compile(str(py), cfile=str(Path(tempfile.gettempdir()) / "vc.pyc"),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                broken.append("%s: %s" % (py.name, str(exc).splitlines()[0]))
        if broken:
            bad("S10 脚本可编译", "；".join(broken))
        else:
            ok("S10 脚本可编译", "%d 个 .py 全部通过 py_compile" % len(pyfiles))
    return name


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    target = Path(argv[0]).expanduser().resolve()
    if not target.exists():
        print("[错误] 路径不存在：%s" % target)
        return 2

    print("=" * 70)
    print("verify_skill_package.py — .skill 结构校验")
    print("目标：%s" % target)
    print("=" * 70)

    if target.is_dir():
        print("（输入是目录，按技能源码目录校验）")
        verify_dir(target, target.name)
    else:
        size = target.stat().st_size
        print("体积：%d 字节（%.1f KB）" % (size, size / 1024.0))

        # S1 合法 tar.gz
        try:
            tar = tarfile.open(target, "r:gz")
        except Exception as exc:
            bad("S1 合法 gzip tar 归档", str(exc))
            tar = None
        else:
            ok("S1 合法 gzip tar 归档", "成员 %d 个" % len(tar.getmembers()))

        if tar is not None:
            names = [m.name for m in tar.getmembers()]

            # S9 路径安全 + 垃圾文件
            unsafe = [n for n in names if n.startswith("/") or ".." in Path(n).parts]
            # `._xxx` 是 macOS AppleDouble 影子文件，会让 .skill 顶层多出条目
            junk = [n for n in names
                    if ".DS_Store" in n or "__pycache__" in n or n.endswith(".pyc")
                    or Path(n).name.startswith("._")]
            if unsafe:
                bad("S9 路径安全", "含绝对路径/穿越：%s" % unsafe[:3])
            else:
                ok("S9 路径安全", "无绝对路径、无 ..")
            if junk:
                bad("S9b 无归档垃圾", "含 %s" % junk[:3])
            else:
                ok("S9b 无归档垃圾", "无 .DS_Store/__pycache__/.pyc")

            # S2 顶层单目录
            tops = sorted({n.split("/")[0] for n in names if n.strip()})
            if len(tops) == 1:
                ok("S2 顶层单目录", tops[0])
            else:
                bad("S2 顶层单目录", "顶层有 %d 个条目：%s" % (len(tops), tops[:5]))

            # 解压到临时目录做内容校验
            with tempfile.TemporaryDirectory() as td:
                try:
                    tar.extractall(td)
                except Exception as exc:
                    bad("S2b 可解压", str(exc))
                else:
                    ok("S2b 可解压", "解压成功")
                    roots = list(Path(td).iterdir())
                    if len(roots) == 1 and roots[0].is_dir():
                        inner = roots[0]
                        top_name = verify_dir(inner, top_name_of(target))
                        if top_name and inner.name != top_name:
                            bad("S2c 顶层目录名 == frontmatter.name",
                                "目录 %r != name %r" % (inner.name, top_name))
                        elif top_name:
                            ok("S2c 顶层目录名 == frontmatter.name", top_name)
                    else:
                        bad("S2b 可解压", "解压后顶层不是单个目录")
            tar.close()

        if 1024 <= size <= 5 * 1024 * 1024:
            ok("S8 体积合理", "%.1f KB" % (size / 1024.0))
        else:
            bad("S8 体积合理", "%.1f KB 超出 1KB–5MB 区间" % (size / 1024.0))

    print("-" * 70)
    print("结果：PASS %d / FAIL %d / WARN %d" % (len(PASS), len(FAIL), len(WARN)))
    for n, d in FAIL:
        print("  FAIL %s — %s" % (n, d))
    print("-" * 70)
    return 1 if FAIL else 0


def top_name_of(p: Path):
    return p.stem.replace(".skill", "")


if __name__ == "__main__":
    sys.exit(main())
