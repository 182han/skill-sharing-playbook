#!/usr/bin/env bash
# build_skill.sh — 把 skill_src/elite20-packager 打包成可安装的 赵怡涵_C4_elite20-packager.skill
#
# .skill 就是一个 tar.gz，顶层目录名必须等于 SKILL.md frontmatter 里的 name。
# 打完包后自动调用 verify_skill_package.py 做结构校验。
#
# 用法：bash scripts/build_skill.sh [--quiet]
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

SRC_DIR="skill_src/elite20-packager"
OUT="赵怡涵_C4_elite20-packager.skill"
QUIET="${1:-}"

test -f "$SRC_DIR/SKILL.md" || { echo "[错误] 缺少 $SRC_DIR/SKILL.md"; exit 1; }

# 归档前清掉 macOS / Python 垃圾，保证包干净
find "$SRC_DIR" -name '.DS_Store' -delete 2>/dev/null || true
find "$SRC_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

rm -f "$OUT"

# 关键 1：用 -C skill_src 让归档顶层正好是 elite20-packager/
# 关键 2：COPYFILE_DISABLE=1 —— macOS 的 bsdtar 默认会给每个文件塞一个
#         AppleDouble 兄弟条目 `._文件名`，导致归档顶层出现两个条目、
#         verify_skill_package.py 的「顶层单目录」检查直接失败。
#         这个坑是校验脚本抓出来的，不是猜的。
# 关键 3：EXCLUDE 掉 ._ / .DS_Store 兜底。
COPYFILE_DISABLE=1 tar --disable-copyfile -czf "$OUT" \
    --exclude='._*' --exclude='.DS_Store' --exclude='__pycache__' \
    -C skill_src elite20-packager

SIZE=$(wc -c < "$OUT" | tr -d ' ')
echo "已生成 $OUT（$SIZE 字节）"

if [ "$QUIET" != "--quiet" ]; then
  echo "--- 归档内容 ---"
  tar -tzf "$OUT"
fi

echo "--- 结构校验 ---"
python3 "$ROOT/scripts/verify_skill_package.py" "$OUT"
