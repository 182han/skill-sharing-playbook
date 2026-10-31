# 赵怡涵_C4_提交包 · elite20-packager

> **Elite20 提交包自检器** — 输入一个提交包文件夹路径，输出该包相对《提交总则》六件套 + §5.1 仓库结构 + 挑战 rubric 的**缺失项清单与修复建议**（Markdown + Excel），并可一键生成缺失文件的「待填」骨架。
>
> 挑战：**C4 技能分享与传播** ｜ 作者：赵怡涵 ｜ 日期：2026-10-03

---

## 是什么

一个**可安装的 Agent Skill**（`elite20-packager`）+ 一个**可直接运行的 Python 脚本**。它把散落在四份官方文件里的交付要求变成一条命令：

| 要求在哪 | 内容 |
|---|---|
| `_交付规范_执行者必读.md` §3 | 六件套 7 个文件（`姓名_CX_*.md`） |
| `_交付规范_执行者必读.md` §5.1 | 仓库结构（README / CHANGELOG / LICENSE / requirements.txt / scripts / tests / docs） |
| 各挑战 `CHALLENGE.md`「提交内容」表 | 挑战专属交付物（C4 是 5 项） |
| 各挑战 `rubric.json` 的 `red_flags` | 三条红线（各自封顶 5 分） |

**支持 C1–C10H 全部 20 个挑战**，检查规则从官方 `challenge.json` 自动生成，不是手写清单。

---

## 解决什么问题

Elite20 里**每个人做每个挑战都要交同一套证据账本**，而"缺文件"是最高频的扣分原因。官方把它单独列成了一条红线：

```json
// 07_C4 技能分享与传播/rubric.json
{ "id": "missing_artifacts", "description": "核心交付物缺失",
  "affectedDimension": "artifactCompleteness", "maxScore": 5 }
```

`maxScore: 5` 意味着：一旦缺核心交付物，**满分 15 分的「产物完整性」维度直接封顶 5 分**——一次丢 10 分。

但要求分散在四个地方，命名规范又严（`姓名_CX_*.md`），赶 deadline 时没人记得全。这个工具就是把这四份清单变成一条命令。

---

## 快速开始

```bash
# 1) 解包（.skill 就是一个 tar.gz）
tar -xzf 赵怡涵_C4_elite20-packager.skill

# 2) 对一个提交包跑自检
python3 elite20-packager/scripts/elite20_packager.py ~/Desktop/张三_C5_提交包 --challenge C5

# 3) 看报告
open ~/Desktop/张三_C5_提交包/reports/packager_report.md
```

**环境要求**：Python 3.8+；`openpyxl`（Excel 报告，缺了自动降级为只出 Markdown）；`PyYAML`（读注册表）。**不需要网络、不需要 GPU、不需要 API Key。**

```bash
python3 -V && python3 -c "import openpyxl, yaml; print('依赖 OK')"
```

### 常用参数

```bash
# 指定挑战（目录名不含 CX 时必需）
... --challenge C4 --student 赵怡涵

# 一键生成缺失文件的「待填」骨架（先预览再落盘）
... --challenge C5 --scaffold --dry-run
... --challenge C5 --scaffold

# 只出 Markdown / 输出 JSON / 换输出目录
... --no-xlsx
... --json
... -o /tmp/检查结果
```

---

## 示例

### 对一个真实的、已完成的自检（退出码 0）

```bash
$ python3 elite20-packager/scripts/elite20_packager.py ~/Desktop/赵怡涵_C2_提交包 --challenge C2

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

那条 `⚠️` 是**真问题**：`README 六段必备 — 未检出小节：是什么、解决什么问题`。

### 对一个空包（**反向测试**：证明它真的会报缺）

```bash
$ mkdir -p /tmp/演示_空包_C4_提交包
$ python3 elite20-packager/scripts/elite20_packager.py /tmp/演示_空包_C4_提交包 --challenge C4 --no-xlsx

L1 六件套                       通过  0 /  7
   ❌ 方案草案 — 未找到匹配 *方案草案*.md/*proposal*.md/*草案*.md 的文件
   ...
红线自检                         通过  0 /  4
   ❌ 红线 1：AI 日志与迭代痕迹 — 包内没有 AI 日志文件 → 触发 rubric `no_ai_log`（封顶 5 分）
   ❌ 红线 2：拿来说明标明 License — 包内没有 `拿来说明.md`
   ❌ 红线 3：可复现脚本 — 没有 `scripts/reproduce.sh`
   ❌ 红线 3：冒烟测试 — 没有 tests/ 下的冒烟测试
----------------------------------------------------------------
合计：✅ 0  ⚠️ 1  ❌ 28   |  必须先修 28 项
$ echo $?
1
```

### 一键起一个新包

```bash
$ python3 elite20-packager/scripts/elite20_packager.py /tmp/测试_C4_提交包 \
      --challenge C4 --student 张三 --scaffold --no-xlsx

骨架生成 : 新建 23 个
   + 张三_C4_方案草案.md
   + 张三_C4_方案设计.md
   ...
   + skill_src/你的技能名/SKILL.md
```

生成的骨架里**只有「待填」占位**：

```html
<!-- ⚠️ 本文件由 elite20-packager --scaffold 生成，全部字段为「待填」占位。
     禁止直接提交本骨架。请本人用真实内容替换每一处「待填」。 -->
```

更多真实运行记录见 `skill_src/elite20-packager/examples/README.md` 和 `赵怡涵_C4_demo/`。

---

## 项目结构

```
赵怡涵_C4_提交包/
├── 赵怡涵_C4_elite20-packager.skill   ← ★ 可安装技能包（37.7 KB tar.gz，17 项结构校验全 PASS）
├── 赵怡涵_C4_skill说明.md             ← 技能说明（问题/场景/IO/步骤/真实案例）
├── 赵怡涵_C4_教学说明.md              ← 教学说明（安装/上手/8 个坑/7 个技巧）
├── 赵怡涵_C4_AI日志.md                ← 10 个真实决策节点
├── 赵怡涵_C4_传播计划.md              ← C4 核心：发布话术/邀请清单/反馈表/v2 触发条件
├── 赵怡涵_C4_拿来说明.md              ← 复用来源 + License + 改了什么
├── 赵怡涵_C4_方案草案.md / _方案设计.md / _G1背书.md / _Portfolio条目.md / _AAR.md
├── 赵怡涵_C4_demo/                    ← 三个真实包的原始终端输出 + 报告
│   ├── run_demo.sh  run1_C1/  run2_C2/  run3_C4/
│   ├── 录屏脚本.md  截图位置说明.md     （视频/截图【待赵怡涵执行】）
├── skill_src/elite20-packager/         ← ★ 技能源码（.skill 由此打包）
│   ├── SKILL.md                        （270 行，正文 245 行 < 500）
│   ├── scripts/elite20_packager.py     （核心检查引擎，1268 行）
│   ├── scripts/build_challenge_index.py（注册表生成器，含"不发明官方要求"硬断言）
│   ├── references/challenges_index.yaml（20 个挑战，自动生成）
│   ├── references/checklist.yaml       （规则的人类可读镜像）
│   └── examples/                       （真实运行记录 + 复现脚本）
├── scripts/
│   ├── reproduce.sh                    ← 一条命令跑完全部自检
│   ├── build_skill.sh                  ← 打包 .skill（含 AppleDouble 防护）
│   └── verify_skill_package.py         ← .skill 结构校验（17 项）
├── tests/test_smoke.py                 ← 10 组冒烟断言（78 个检查点）
├── docs/                               ← 文件对照表 / 红线自测 / 群消息留痕 / demo
├── reports/                            ← 自检器对本包自己的输出
├── G2验证报告_生成说明.md              00_先读我_待办清单.md
└── README.md CHANGELOG.md LICENSE LICENSE-CONTENT.md requirements.txt .gitignore
```

---

## 技术栈

| 层 | 用了什么 |
|---|---|
| 语言 | Python 3（实测 3.9.6，要求 ≥3.8） |
| 依赖 | `openpyxl`（Excel 报告，可降级）、`PyYAML`（读注册表） |
| 标准库 | `argparse` `fnmatch` `tarfile` `re` `pathlib` `json` `os` `sys` `tempfile` `py_compile` `datetime` |
| 打包 | `tarfile` / `bsdtar`（`.skill` = tar.gz） |
| 测试 | 自带测试框架（不依赖 pytest，`python3 tests/test_smoke.py` 直接跑） |
| 数据 | YAML 注册表（从官方 `challenge.json` 机器生成） |
| 平台 | macOS arm64 / Linux（Windows 未实测） |

**为什么几乎没有依赖**：本机没有 pip 联网权限；更重要的是——**依赖越少，别人装得越顺，传播阻力越小**。缺 `openpyxl` 时自动降级为只出 Markdown，不崩。

---

## 验证

### `bash scripts/reproduce.sh` — 真实终端输出

（2026-10-03 于 macOS arm64 / Python 3.9.6 实测，**原样粘贴，未做任何修饰**）

```text
== 0/6 环境自检 ==
Python 3.9.6
  openpyxl 可用
  pyyaml   可用
  [ ok ] Python 3.9 + 依赖检查通过

== 1/6 重建 .skill 并校验结构 ==
已生成 赵怡涵_C4_elite20-packager.skill（38578 字节）
--- 结构校验 ---
======================================================================
verify_skill_package.py — .skill 结构校验
目标：/Users/zhanghao/Desktop/赵怡涵_C4_提交包/赵怡涵_C4_elite20-packager.skill
======================================================================
体积：38578 字节（37.7 KB）
PASS  S1 合法 gzip tar 归档                              成员 11 个
PASS  S9 路径安全                                        无绝对路径、无 ..
PASS  S9b 无归档垃圾                                      无 .DS_Store/__pycache__/.pyc
PASS  S2 顶层单目录                                       elite20-packager
PASS  S2b 可解压                                        解压成功
PASS  S4a frontmatter.name 非空                        elite20-packager
PASS  S4b frontmatter.description 非空                 长度 1358 字符
PASS  S5 name 是 kebab-case                           elite20-packager
PASS  S6 description 足够具体                            1358 字符
PASS  S6b description 含触发短语                          1 处触发语线索
PASS  S7 正文 < 500 行                                  245 行
PASS  S11 scripts/ 非空                                2 个文件
PASS  S11 references/ 非空                             2 个文件
PASS  S11 examples/ 非空                               2 个文件
PASS  S10 脚本可编译                                      2 个 .py 全部通过 py_compile
PASS  S2c 顶层目录名 == frontmatter.name                  elite20-packager
PASS  S8 体积合理                                        37.7 KB
----------------------------------------------------------------------
结果：PASS 17 / FAIL 0 / WARN 0
----------------------------------------------------------------------
  [ ok ] verify_skill_package.py 全 PASS（17 项）

== 2/6 冒烟测试 ==
======================================================================
赵怡涵_C4_提交包 · 冒烟测试
包根目录：/Users/zhanghao/Desktop/赵怡涵_C4_提交包
======================================================================
PASS  T1 六件套 方案草案 — 赵怡涵_C4_方案草案.md
PASS  T1 六件套 方案设计 — 赵怡涵_C4_方案设计.md
PASS  T1 六件套 G1背书 — 赵怡涵_C4_G1背书.md
PASS  T1 六件套 AI日志 — 赵怡涵_C4_AI日志.md
PASS  T1 六件套 拿来说明 — 赵怡涵_C4_拿来说明.md
PASS  T1 六件套 Portfolio条目 — 赵怡涵_C4_Portfolio条目.md
PASS  T1 六件套 AAR — 赵怡涵_C4_AAR.md
PASS  T1 文件 README.md — 23210 字节
PASS  T1 文件 CHANGELOG.md — 8857 字节
PASS  T1 文件 LICENSE — 1445 字节
PASS  T1 文件 requirements.txt — 757 字节
PASS  T1 文件 scripts/reproduce.sh — 4943 字节
PASS  T1 文件 tests/test_smoke.py — 21229 字节
PASS  T1 文件 docs/文件对照表.md — 7399 字节
PASS  T1 文件 docs/红线自测.md — 7752 字节
PASS  T1 文件 docs/群消息留痕.md — 3972 字节
PASS  T1 文件 docs/demo.md — 7988 字节
PASS  T1 文件 G2验证报告_生成说明.md — 3367 字节
PASS  T1 文件 00_先读我_待办清单.md — 6572 字节
PASS  T1 文件 赵怡涵_C4_skill说明.md — 14266 字节
PASS  T1 文件 赵怡涵_C4_教学说明.md — 11612 字节
PASS  T2 AI 日志存在 
PASS  T2 决策节点 >= 3（红线 R1） — 识别到 10 个
PASS  T2 未把正文交叉引用算成节点（应与真实节点数一致） — 识别到 10 个；若远超真实节点数说明计数被交叉引用污染
PASS  T2 AI 使用统计段存在 
PASS  T3 拿来说明存在 
PASS  T3 含 License 声明（红线 R2） 
PASS  T3 引用了 materials 里的两个 .skill 
PASS  T3 LICENSE 文件存在 
PASS  T4 reproduce.sh 存在（红线 R3） 
PASS  T4 reproduce.sh 可执行位 — 711
PASS  T4 用 set -euo pipefail 
PASS  T4 会跑冒烟测试 
PASS  T4 有失败退出路径（exit 1） 
PASS  T4 成功/失败退出码分离 
PASS  T5 .skill 存在 — 赵怡涵_C4_elite20-packager.skill
PASS  T5 是合法 tar.gz — 37.7 KB
PASS  T5 顶层单目录 — ['elite20-packager']
PASS  T5 无 AppleDouble 垃圾 
PASS  T5 含 SKILL.md 
PASS  T5 含 scripts/ 
PASS  T5 含 references/ 
PASS  T5 含 examples/ 
PASS  T6 SKILL.md 存在 
PASS  T6 有 YAML frontmatter 
PASS  T6 frontmatter 有 name 
PASS  T6 frontmatter 有 description 
PASS  T6 name 是 kebab-case 
PASS  T6 正文 < 500 行 — 245 行
PASS  T6 含 Purpose 小节 
PASS  T6 含 Workflow 小节 
PASS  T6 含 Edge Cases 小节 
PASS  T6 含 Examples 小节 
PASS  T7 注册表存在 
PASS  T7 覆盖 >= 20 个挑战 — 实际 20 个
PASS  T7 C4 检查项数 == 官方 token 数 — 5 vs 5
PASS  T7 每个检查项都能追溯到官方 token — ['*skill说明*', '*.skill', '*教学说明*', '*demo*', '*AI日志*']
PASS  T7 未发明官方要求（C1 不含翻译方法） 
PASS  T7 未发明官方要求（C2 不含论文 PDF 必填） 
PASS  T8 自检器脚本存在 
PASS  T8a 空包退出码为 1 — exit=1
PASS  T8a JSON 可解析 — items=32
PASS  T8a 空包缺失项 >= 20 — {'OK': 0, 'WARN': 2, 'MISSING': 28, 'INFO': 2}
PASS  T8a 报告文件已生成 
PASS  T8b 齐全包退出码为 0 — exit=0 缺失=[]
PASS  T10a Excel 报告已生成 
PASS  T10a Excel 4 个 sheet — ['总览', '缺失矩阵', '修复建议', '挑战交付物清单']
PASS  T8d README 未被覆盖 
PASS  T8d 生成了骨架文件 — 22 个
PASS  T8d 骨架含真实姓名前缀 — ['赵六_C4_AAR.md', '赵六_C4_AI日志.md', '赵六_C4_G1背书.md']
PASS  T8d 骨架标了「待填」占位 
PASS  T8d 骨架标了禁止直接提交 
PASS  T8d 骨架没被算成已完成（再跑一次仍报缺失） 
PASS  T9 传播计划存在 
PASS  T9 传播动作标了【待赵怡涵执行】 
PASS  T9 待办清单标了【待赵怡涵执行】 
PASS  T9 未伪造使用次数/发布记录 — []
PASS  T10b .skill 与 skill_src 同步（不是发旧包） 
----------------------------------------------------------------------
通过 78 / 失败 0
----------------------------------------------------------------------
  [ ok ] tests/test_smoke.py 全绿

== 3/6 用自检器检查本包自己（C4） ==
elite20-packager v1.0 · 包自检
包路径   : /Users/zhanghao/Desktop/赵怡涵_C4_提交包
学生/挑战: 赵怡涵 / C4   （扫描到 49 个文件）
----------------------------------------------------------------
L1 六件套                       通过  7 /  7
L2 仓库结构                      通过 15 / 15
L3 挑战专属交付物                   通过  5 /  5
红线自检                         通过  4 /  4
----------------------------------------------------------------
合计：✅ 31  ⚠️ 0  ❌ 0   |  必须先修 0 项
Markdown : /Users/zhanghao/Desktop/赵怡涵_C4_提交包/reports/packager_report.md
Excel    : /Users/zhanghao/Desktop/赵怡涵_C4_提交包/reports/packager_report.xlsx

结构层全绿。注意：这只说明文件账本齐了，不说明内容是对的。
  [ ok ] 本包结构自检：无缺失项

== 4/6 对真实历史包 C1 / C2 跑检查 ==
  [ ok ] C1 包检查完成（退出码 0，记录见 赵怡涵_C4_demo/run1_C1/）
  [ ok ] C2 包检查完成（退出码 0，记录见 赵怡涵_C4_demo/run2_C2/）
  [note] 本包自查（run3_C4）由 赵怡涵_C4_demo/run_demo.sh 生成

== 5/6 汇总 ==
  .skill 体积      : 38578 字节
  结构校验         : 17 PASS / 0 FAIL / 0 WARN
  本包文件总数     : 49

全部自检通过 ✅
```

**一句话总结**：`全部自检通过 ✅`，退出码 **0**；结构校验 **17 PASS / 0 FAIL / 0 WARN**；冒烟测试 **通过 78 / 失败 0**。

> ⚠️ 上面 `.skill 体积` 与 `本包文件总数` 会随源码/文档的每次修改而变动，**以你自己跑出来的数字为准**。我没有把它们写死——写死一个"漂亮数字"比不写更糟。运行环境不同（Python 小版本、依赖版本）也会让这两个数字变化。

### 三个真实包的实测（`bash 赵怡涵_C4_demo/run_demo.sh`）

| 运行 | 对象 | 原始终端记录 |
|---|---|---|
| run1 | `~/Desktop/赵怡涵_C1_提交包`（192 文件） | `赵怡涵_C4_demo/run1_C1/terminal_output.txt` |
| run2 | `~/Desktop/赵怡涵_C2_提交包`（37 文件） | `赵怡涵_C4_demo/run2_C2/terminal_output.txt` |
| run3 | 本包自己 | `赵怡涵_C4_demo/run3_C4/terminal_output.txt` |

### 单独跑测试

```bash
python3 tests/test_smoke.py      # 10 组断言，打印 通过 N / 失败 M
python3 scripts/verify_skill_package.py 赵怡涵_C4_elite20-packager.skill
```

---

## 这个工具**不做**什么（很重要）

| 它不做 | 为什么 |
|---|---|
| ❌ **不打分** | 自检器算出的分数 ≠ 官方 rubric 分数。给人一个"78 分"会严重误导。唯一的"通过率"数字强制标注为「启发式，非官方评分」 |
| ❌ **不验证内容真假** | 它只看文件在不在、关键内容有没有。**`reproduce.sh` 全绿 ≠ 东西是对的** |
| ❌ **不发明官方要求** | 生成器有三道硬锁：refine 只能细化已有官方 token、检查项数必须等于官方 token 数、测试断言禁止出现官方没有的要求 |
| ❌ **不伪造证据** | `--scaffold` 只写「待填」；绝不生成"已完成"的假记录；绝不覆盖已有文件 |
| ❌ **不代做群内动作** | 发群、找试用、收反馈只能本人做，一律标 `【待赵怡涵执行】` |

**"不发明官方要求"这条是用代价换来的**：开发中 AI 曾凭空推出 `翻译方法.md`（C1）和 `paper.pdf`（C2）两条官方并不存在的要求，导致对一个**已合格的真实历史包**误报缺失。一个会发明要求的自检器比没有自检器更糟——它会让本来合格的人白做返工。完整经过见 `赵怡涵_C4_AI日志.md` 决策节点 4。

---

## AI 生成说明

本包由 **赵怡涵** 在 **DeepSeek Harness（deepseek-v4-flash）** 辅助下完成。分工如下：

| 部分 | 谁做的 | 说明 |
|---|---|---|
| 选题决策 | **人** | AI 建议做"AI 论文排版器"，我驳回，改选"提交包自检器"（按 C4 评分逻辑：被使用次数） |
| 架构设计（三层账本） | **人** | AI 建议做加权打分器，我驳回，改为三层账本 |
| 代码骨架 | AI 起草 + **人核验修改** | 约 1268 行核心脚本。AI 铺样板，我修了 5 个真实 bug（见 AI 日志） |
| 检查规则 | **人** | 逐条从官方 `challenge.json` / `_交付规范_执行者必读.md` 核对 |
| `.skill` 打包 | AI 起草 + 人修正 | AI 给的 tar 命令是对的，但漏了 `COPYFILE_DISABLE`（macOS AppleDouble 坑），由我的校验脚本抓出 |
| 全部 `.md` 文档 | 人主导，AI 辅助润色 | 事实、数字、失败记录全部来自真实过程 |
| 测试 | 人设计 + AI 起草 | 含**反向测试**（空包必须报缺失）与**诚实性测试**（拦伪造字样） |

**AI 的使用是可追溯的**：`赵怡涵_C4_AI日志.md` 记录了 **10 个决策节点**，每个都含"背景 / AI 建议 / 我的判断 / 人工核验（真实命令）/ 结果"，并含 **4 次驳回**、**5 个真实 bug**、**AI 最大误导 1 例**。

**关键事实：AI 提出的方案被驳回了 4 次，其中 3 次驳回被证明是正确的。** 完整记录见 AI 日志。

---

## 借鉴来源

| 来源 | 拿了什么 | 详见 |
|---|---|---|
| `07_C4 技能分享与传播/materials/skill-explainer.skill` | ① 报告必须"固定 section、每节不许省"；② "每个批评必须配一条具体建议"；③ 边界情况清单（空文件/无 frontmatter/损坏的 .skill 包…） | `赵怡涵_C4_拿来说明.md` §二 |
| `07_C4 技能分享与传播/materials/wechat-doc-mapper.skill` | ① **注册表驱动**（挑战知识放 YAML，加挑战不改代码）；② `references/xxx.yaml` + `scripts/xxx.py` 的目录约定；③ argparse + 结构化输出的 CLI 形态；④ 扫描时的忽略规则 | `赵怡涵_C4_拿来说明.md` §三 |
| `_交付规范_执行者必读.md` | 六件套清单、§5.1 仓库结构、§3 诚实性规则、§4 AI 日志格式、§6 验证要求 | 转成机器可读检查项 |
| 官方 20 个 `challenge.json` / `CHANGELOG.md` / `rubric.json` | `required_deliverables`、提交内容表、三条 `red_flags` | 自动抽取成注册表，**只读不改官方文件** |
| `赵怡涵_C1_提交包` / `赵怡涵_C2_提交包` | 包目录形态、文档风格；**并作为真实测试对象** | 暴露了 4 个 bug |

**本包不含**任何官方 `.skill` 文件的副本，**未复制**它们的代码或文本，只借鉴结构与设计思路。逐条对照见 `赵怡涵_C4_拿来说明.md` 与 `LICENSE-CONTENT.md`。

---

## 已知缺口（如实列出，不藏）

| # | 缺口 | 说明 | 补齐路径 |
|---|---|---|---|
| 1 | **真实被使用次数 = 0** | C4 最高权重项。群内发布、邀请试用、收集反馈**一次都没做** | `赵怡涵_C4_传播计划.md`（话术/清单/反馈表已备好）；全部标 `【待赵怡涵执行】` |
| 2 | **demo 视频 / 截图未录制** | 终端记录是真实的（3 个包），但不含录屏 | `赵怡涵_C4_demo/录屏脚本.md` + `截图位置说明.md` |
| 3 | **G1 / G3 群内动作未做** | 总则要求群内公开，只能本人执行 | `赵怡涵_C4_G1背书.md`（话术模板已备） |
| 4 | **G2 验证报告未生成** | §9 规定 G2 禁止手写，必须官方 skill 产出 | `G2验证报告_生成说明.md` |
| 5 | **文本判定是启发式的** | 字数统计、决策节点计数都可能误报 | 报告已注明；v2 计划给出具体行号而非判断 |
| 6 | **未做 Windows / Linux 验证** | 只在 macOS arm64 + Python 3.9.6 实测 | 用 `pathlib` 写的，理论跨平台 |
| 7 | **两个官方 `.skill` 的 License 未标明** | 包内无 License 文件；本包未复制它们 | 需向群内确认，标 `【待赵怡涵执行】` |

---

## 一句话

> **`--scaffold` 帮你建文件夹，报告帮你找缺口，但内容只能你自己写。绿了只代表账本齐了。**
>
> 而这个工具本身，**目前有 0 个人用过**——C4 按"被使用次数"评分，所以那才是真正待办的事。

---

## License

代码 **MIT** ｜ 文档 **CC BY 4.0** ｜ 详见 `LICENSE` 与 `LICENSE-CONTENT.md`。
