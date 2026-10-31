#!/usr/bin/env bash
# run_demo.sh — 复现 examples/README.md 里的三组真实运行
#
# 跑法：bash examples/run_demo.sh [PACKAGE_DIR]
#   PACKAGE_DIR 省略时，自动尝试 ~/Desktop 下最常见的 `*_提交包` 目录。
#
# 这个脚本只做两件事：跑检查、把输出打出来。不改任何提交包内容。
set -uo pipefail
cd "$(dirname "$0")/.."
SKILL_DIR="$(pwd)"
CHECKER="$SKILL_DIR/scripts/elite20_packager.py"
OUT="${TMPDIR:-/tmp}/elite20_packager_demo"

PKG="${1:-}"
if [ -z "$PKG" ]; then
  for cand in "$HOME/Desktop"/*_提交包; do
    [ -d "$cand" ] && PKG="$cand" && break
  done
fi

if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
  echo "没找到提交包目录。用法：bash examples/run_demo.sh <PACKAGE_DIR>"
  echo
  echo "--- 演示 A：空包必须报缺失（不需要任何真实包）---"
  EMPTY="${TMPDIR:-/tmp}/elite20_packager_empty_demo_提交包"
  rm -rf "$EMPTY"; mkdir -p "$EMPTY"
  python3 "$CHECKER" "$EMPTY" --challenge C4 --no-xlsx -o "$OUT/empty" || true
  echo
  echo "--- 演示 B：--scaffold 生成待填骨架 ---"
  python3 "$CHECKER" "$EMPTY" --challenge C4 --student 演示 --scaffold --no-xlsx -o "$OUT/scaffold" | tail -30
  echo
  echo "--- 生成的文件（前 10 行示例骨架）---"
  head -10 "$EMPTY/演示_C4_AI日志.md"
  rm -rf "$EMPTY"
  exit 0
fi

echo "=== 对真实包跑自检：$PKG ==="
python3 "$CHECKER" "$PKG" -o "$OUT/real"
echo
echo "退出码: $?   （0=无缺失项 / 1=有缺失项 / 2=用法错误）"
echo "报告目录: $OUT/real"
