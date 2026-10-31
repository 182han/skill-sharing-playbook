# docs/demo

> **别人照着这份文档，能在我这台机器之外跑出同样的结果。**
> 每一步都给了命令和期望输出。跑不出来就是我的问题，请告诉我。

---

## 一、前置条件

| 项 | 要求 | 检查命令 |
|---|---|---|
| 操作系统 | macOS / Linux（Windows 未实测） | `uname -a` |
| Python | **3.8+**（实测 3.9.6） | `python3 -V` |
| `openpyxl` | 可选，用于 Excel 报告 | `python3 -c "import openpyxl; print('ok')"` |
| `PyYAML` | 必需，用于读挑战注册表 | `python3 -c "import yaml; print('ok')"` |
| 网络 | **不需要** | — |

**一键检查**：

```bash
python3 -V && python3 -c "import openpyxl, yaml; print('依赖 OK')"
```

**期望输出**：

```
Python 3.9.6
依赖 OK
```

缺 `openpyxl` 时：

```bash
python3 -m pip install --user openpyxl pyyaml
# 装不上也没关系：加 --no-xlsx 就能跳过 Excel
```

---

## 二、Demo A：对一个提交包跑自检（最核心的用法，30 秒）

### Step 1：拿到包

```bash
cd ~/Desktop/赵怡涵_C4_提交包
ls -la
```

### Step 2：跑自检

```bash
python3 skill_src/elite20-packager/scripts/elite20_packager.py "$(pwd)" --challenge C4
```

### Step 3：期望输出

```
elite20-packager v1.0 · 包自检
包路径   : /Users/你的用户名/Desktop/赵怡涵_C4_提交包
学生/挑战: 赵怡涵 / C4   （扫描到 NN 个文件）
----------------------------------------------------------------
L1 六件套                       通过  7 /  7
L2 仓库结构                      通过 16 / 16
L3 挑战专属交付物                   通过  5 /  5
红线自检                         通过  4 /  4
----------------------------------------------------------------
合计：✅ NN  ⚠️ N  ❌ 0   |  必须先修 0 项
Markdown : /Users/你的用户名/Desktop/赵怡涵_C4_提交包/reports/packager_report.md
Excel    : /Users/你的用户名/Desktop/赵怡涵_C4_提交包/reports/packager_report.xlsx

结构层全绿。注意：这只说明文件账本齐了，不说明内容是对的。
```

**三个产物**：

| 文件 | 怎么看 |
|---|---|
| `reports/packager_report.md` | `open reports/packager_report.md` |
| `reports/packager_report.xlsx` | `open reports/packager_report.xlsx`（4 个 sheet） |
| 退出码 | `echo $?` → `0` = 无缺失项 |

---

## 三、Demo B：对有缺失项的包跑自检（看它**真的会报缺**）

> **这一步比 Demo A 更重要。** 一个"永远说 OK"的检查器是没用的。用空目录验证它会报缺。

```bash
# 造一个空包
mkdir -p /tmp/演示_空包_C4_提交包

python3 skill_src/elite20-packager/scripts/elite20_packager.py \
    /tmp/演示_空包_C4_提交包 --challenge C4 --no-xlsx -o /tmp/演示输出
```

**期望输出（节选）**：

```
L1 六件套                       通过  0 /  7
   ❌ 方案草案 — 未找到匹配 *方案草案*.md/*proposal*.md/*草案*.md 的文件
   ❌ 方案设计 — 未找到匹配 *方案设计*.md/*设计*.md/*design*.md 的文件
   ...
L3 挑战专属交付物                   通过  0 /  5
   ❌ 挑战交付物：Skill 说明文档 — C4 的专属交付物缺失（匹配 *skill说明*/*skill说明*.md）
   ...
合计：✅ 0  ⚠️ 1  ❌ 28   |  必须先修 28 项
```

**看反向结果**：

```bash
echo "退出码: $?"          # 期望 1
```

---

## 四、Demo C：`--scaffold` 一键生成待填骨架

```bash
# 先预览，不写盘
python3 skill_src/elite20-packager/scripts/elite20_packager.py \
    /tmp/演示_空包_C4_提交包 --challenge C4 --student 演示 --scaffold --dry-run --no-xlsx \
    -o /tmp/演示输出

# 确认后真的生成
python3 skill_src/elite20-packager/scripts/elite20_packager.py \
    /tmp/演示_空包_C4_提交包 --challenge C4 --student 演示 --scaffold --no-xlsx \
    -o /tmp/演示输出

# 看生成了什么
find /tmp/演示_空包_C4_提交包 -type f | sort
```

**期望**：生成约 23 个文件，命名带真实前缀 `演示_C4_*`。

**关键验证：骨架里只有「待填」，没有假内容**

```bash
head -20 /tmp/演示_空包_C4_提交包/演示_C4_AI日志.md
```

**期望输出（前几行）**：

```
<!-- ⚠️ 本文件由 elite20-packager --scaffold 生成，全部字段为「待填」占位。
     禁止直接提交本骨架。请本人用真实内容替换每一处「待填」。
     生成时间：2026-10-03 18:38 -->

# 演示_C4_AI 日志

> 要求：≥3 个决策节点（建议 6–10 个）；…

### 决策节点 1：待填（一句话标题）

- **背景**：待填
- **AI 建议**：待填（附关键 prompt 原文）
```

**再跑一次检查，必须仍然报缺失**（防止骨架冒充成品）：

```bash
python3 skill_src/elite20-packager/scripts/elite20_packager.py \
    /tmp/演示_空包_C4_提交包 --challenge C4 --no-xlsx -q -o /tmp/演示输出
echo "退出码: $?"    # 期望 1，说明骨架不算"已交"
```

**清理**：

```bash
rm -rf /tmp/演示_空包_C4_提交包 /tmp/演示输出
```

---

## 五、Demo D：处理别人的包（换挑战、换人）

```bash
# 检查 C2 包
python3 skill_src/elite20-packager/scripts/elite20_packager.py \
    ~/Desktop/赵怡涵_C2_提交包 --challenge C2

# 完全不存在的路径（期望退出码 2，不是崩溃）
python3 skill_src/elite20-packager/scripts/elite20_packager.py /tmp/不存在的目录
echo "退出码: $?"    # 期望 2
```

---

## 六、Demo E：验证 `.skill` 真的能装

**这是 C4 最容易翻车的地方**——`.skill` 看起来是个 tar 包，但顶层结构不对就装不上。

```bash
# 1) 打包（含 AppleDouble 防护）
bash scripts/build_skill.sh

# 2) 结构校验（16 项）
python3 scripts/verify_skill_package.py 赵怡涵_C4_elite20-packager.skill

# 3) 人工确认顶层结构
tar -tzf 赵怡涵_C4_elite20-packager.skill

# 4) 解包并直接运行（模拟"别人装了之后怎么用"）
mkdir -p /tmp/skill_test && tar -xzf 赵怡涵_C4_elite20-packager.skill -C /tmp/skill_test
python3 /tmp/skill_test/elite20-packager/scripts/elite20_packager.py "$(pwd)" --challenge C4 --no-xlsx -o /tmp/演示输出
```

**期望**：`verify_skill_package.py` 输出 `结果：PASS 16 / FAIL 0 / WARN 0`，退出码 0。

---

## 七、完整复现：一条命令

```bash
cd ~/Desktop/赵怡涵_C4_提交包
bash scripts/reproduce.sh
```

**期望**：最后一行是 `全部自检通过 ✅`，退出码 0。

真实输出见 `README.md` 的「验证」一节。

---

## 八、Demo F：三个真实包的实测记录

```bash
bash 赵怡涵_C4_demo/run_demo.sh
```

**产物**：

```
赵怡涵_C4_demo/
├── run1_C1/  terminal_output.txt  packager_report.md  packager_report.xlsx
├── run2_C2/  terminal_output.txt  packager_report.md  packager_report.xlsx
└── run3_C4/  terminal_output.txt  packager_report.md  packager_report.xlsx
```

| 运行 | 对象 | 结果 |
|---|---|---|
| run1 | `~/Desktop/赵怡涵_C1_提交包`（192 文件，真实历史包） | 见 `run1_C1/terminal_output.txt` |
| run2 | `~/Desktop/赵怡涵_C2_提交包`（37 文件，真实历史包） | 见 `run2_C2/terminal_output.txt` |
| run3 | 本包自己 | 见 `run3_C4/terminal_output.txt` |

> 如果本机没有 C1/C2 包，脚本会打印 `[skip]` 并如实标注——**不会伪造输出**。

---

## 九、常见问题速查

| 现象 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'yaml'` | 缺 PyYAML | `python3 -m pip install --user pyyaml` |
| `Excel : （未安装 openpyxl，跳过 Excel 输出）` | 缺 openpyxl | 装它，或加 `--no-xlsx` |
| 报了一堆缺失但其实文件都在 | 命名不规范（少了 `_` 或大小写不对） | 改成 `姓名_CX_描述.md` |
| 挑战编号认错 | 目录名没带 `CX` | 显式加 `--challenge CX --student 姓名` |
| 报告里的"通过率" | **是启发式，不是官方分数** | 见 README「已知缺口」 |

更多坑见 `赵怡涵_C4_教学说明.md` §3。
