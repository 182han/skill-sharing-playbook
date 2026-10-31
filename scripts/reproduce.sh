#!/usr/bin/env bash
# reproduce.sh — 赵怡涵_C4_提交包 一条命令跑完全部自检
#
# 跑法：bash scripts/reproduce.sh
# 退出码：0 = 全部通过；非 0 = 有失败项
#
# 步骤：
#   0/6  环境自检
#   1/6  重建 .skill 并用 verify_skill_package.py 校验结构
#   2/6  跑冒烟测试 tests/test_smoke.py
#   3/6  用自检器检查【本包自己】（C4）
#   4/6  对真实历史包 C1 / C2 跑检查（不存在则跳过，不算失败）
#   5/6  汇总
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

FAILED=0
note() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; FAILED=$((FAILED + 1)); }
pass() { printf '  [ ok ] %s\n' "$1"; }

# ---------------------------------------------------------------------------
note "0/6 环境自检"
# ---------------------------------------------------------------------------
python3 -V
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 - <<'PY'
import sys
ok = True
try:
    import openpyxl  # noqa: F401
    print("  openpyxl 可用")
except ImportError:
    print("  [warn] 没装 openpyxl —— Excel 报告会被跳过，Markdown 照出")
try:
    import yaml  # noqa: F401
    print("  pyyaml   可用")
except ImportError:
    print("  [FAIL] 没装 pyyaml —— 自检器读不了挑战注册表")
    sys.exit(3)
PY
[ $? -eq 0 ] || fail "环境依赖不满足"
pass "Python ${PYV} + 依赖检查通过"

# ---------------------------------------------------------------------------
note "1/6 重建 .skill 并校验结构"
# ---------------------------------------------------------------------------
bash "$ROOT/scripts/build_skill.sh" --quiet
SKILL_FILE="$ROOT/赵怡涵_C4_elite20-packager.skill"
[ -f "$SKILL_FILE" ] || fail "没有生成 .skill"
python3 "$ROOT/scripts/verify_skill_package.py" "$SKILL_FILE" > /tmp/verify_skill_out.txt 2>&1 \
  && pass "verify_skill_package.py 全 PASS（$(grep -c '^PASS' /tmp/verify_skill_out.txt) 项）" \
  || { cat /tmp/verify_skill_out.txt; fail "verify_skill_package.py 有 FAIL"; }

# ---------------------------------------------------------------------------
note "2/6 冒烟测试"
# ---------------------------------------------------------------------------
if python3 "$ROOT/tests/test_smoke.py"; then
  pass "tests/test_smoke.py 全绿"
else
  fail "tests/test_smoke.py 有失败"
fi

# ---------------------------------------------------------------------------
note "3/6 用自检器检查本包自己（C4）"
# ---------------------------------------------------------------------------
CHECKER="$ROOT/skill_src/elite20-packager/scripts/elite20_packager.py"
if python3 "$CHECKER" "$ROOT" --challenge C4 --student 赵怡涵 -o "$ROOT/reports"; then
  pass "本包结构自检：无缺失项"
else
  printf '  [warn] 本包自检报了缺失项（见 reports/packager_report.md）\n'
  sed -n '1,40p' "$ROOT/reports/packager_report.md" | grep -E '^\- |必须先修' || true
  fail "本包结构自检有缺失项"
fi

# ---------------------------------------------------------------------------
note "4/6 对真实历史包 C1 / C2 跑检查"
# ---------------------------------------------------------------------------
DEMO="$ROOT/赵怡涵_C4_demo"
run_real() {   # $1=挑战编号  $2=包路径  $3=归档目录名
  local cx="$1" pkg="$2" sub="$3"
  if [ ! -d "$pkg" ]; then
    printf '  [skip] 本机没有 %s（不是失败）\n' "$pkg"
    return
  fi
  mkdir -p "$DEMO/$sub"
  { echo "# 真实包 $cx：$pkg"; echo "# 运行时间：$(date '+%Y-%m-%d %H:%M:%S')"; echo; } > "$DEMO/$sub/terminal_output.txt"
  python3 "$CHECKER" "$pkg" --challenge "$cx" -o "$DEMO/$sub" >> "$DEMO/$sub/terminal_output.txt" 2>&1
  printf '  [ ok ] %s 包检查完成（退出码 %d，记录见 赵怡涵_C4_demo/%s/）\n' "$cx" "$?" "$sub"
}
run_real C1 "$HOME/Desktop/赵怡涵_C1_提交包" run1_C1
run_real C2 "$HOME/Desktop/赵怡涵_C2_提交包" run2_C2
# 本包自己（run3_C4）由 bash 赵怡涵_C4_demo/run_demo.sh 生成，避免重复跑
printf '  [note] 本包自查（run3_C4）由 赵怡涵_C4_demo/run_demo.sh 生成\n' 

# ---------------------------------------------------------------------------
note "5/6 汇总"
# ---------------------------------------------------------------------------
printf '  .skill 体积      : %s 字节\n' "$(wc -c < "$SKILL_FILE" | tr -d ' ')"
printf '  结构校验         : %s PASS / %s FAIL / %s WARN\n' \
  "$(grep -c '^PASS' /tmp/verify_skill_out.txt || true)" \
  "$(grep -c '^FAIL' /tmp/verify_skill_out.txt || true)" \
  "$(grep -c '^WARN' /tmp/verify_skill_out.txt || true)"
printf '  本包文件总数     : %s\n' "$(find "$ROOT" -type f -not -path '*/.git/*' -not -name '.DS_Store' | wc -l | tr -d ' ')"

echo
if [ "$FAILED" -eq 0 ]; then
  printf '\033[1m全部自检通过 ✅\033[0m\n'
  exit 0
else
  printf '\033[1m有 %d 项失败 ❌\033[0m\n' "$FAILED"
  exit 1
fi
