#!/usr/bin/env bash
# run_demo.sh — 对三个【真实存在】的提交包跑一遍自检，把原始输出存档
#
# 跑法：bash 赵怡涵_C4_demo/run_demo.sh
# 产物：赵怡涵_C4_demo/run1_C1/ run2_C2/ run3_C4/  （各含 terminal_output.txt + 报告 + Excel）
#
# 说明：C1/C2 是本机桌面上真实存在的、已交付的历史包；C4 是本包自己。
#      三个包都不存在时会跳过并如实标注，不伪造任何输出。
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
CHECKER="$ROOT/skill_src/elite20-packager/scripts/elite20_packager.py"
DEMO="$ROOT/赵怡涵_C4_demo"

run_one() {
  local cx="$1" pkg="$2" out="$3" title="$4"
  mkdir -p "$out"
  if [ ! -d "$pkg" ]; then
    printf '包不存在，跳过：%s\n' "$pkg" > "$out/terminal_output.txt"
    echo "  [skip] $cx — 本机没有 $pkg"
    return
  fi
  local log="$out/terminal_output.txt"
  {
    echo "# $title"
    echo "# 运行时间：$(date '+%Y-%m-%d %H:%M:%S')"
    echo "# 命令："
    echo "\$ python3 skill_src/elite20-packager/scripts/elite20_packager.py \"$pkg\" --challenge $cx -o 赵怡涵_C4_demo/$(basename "$out")"
    echo
  } > "$log"
  python3 "$CHECKER" "$pkg" --challenge "$cx" -o "$out" >> "$log" 2>&1
  local rc=$?
  {
    echo
    echo "退出码: $rc   （0=无缺失项 / 1=有缺失项 / 2=用法或路径错误）"
  } >> "$log"
  echo "  [ok]   $cx — 退出码 $rc，报告见 赵怡涵_C4_demo/$(basename "$out")/"
}

echo "== 对三个真实提交包跑 elite20-packager =="
run_one C1 "$HOME/Desktop/赵怡涵_C1_提交包" "$DEMO/run1_C1" "真实包 1：赵怡涵_C1_提交包（课程资料获取与翻译）"
run_one C2 "$HOME/Desktop/赵怡涵_C2_提交包" "$DEMO/run2_C2" "真实包 2：赵怡涵_C2_提交包（AI for Math 论文）"
run_one C4 "$ROOT"                        "$DEMO/run3_C4" "真实包 3：赵怡涵_C4_提交包（本包，自己检查自己）"
echo "== 完成 =="
