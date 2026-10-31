# LICENSE-CONTENT.md — 内容来源与 License 分层说明

> 依据《Elite20 挑战提交总则》与《交付规范_执行者必读》§2：**若上游为 AGPL 等强传染协议，必须单列本文件说明。**

## 一、结论

**本包未复用任何 AGPL / GPL 等强传染协议的内容，因此不存在 License 冲突。**

本文件仍然单独列出，是为了把"哪些是原创、哪些引用了官方资料"说清楚，便于评审核对。

## 二、License 分层

| 内容 | 路径 | License | 说明 |
|---|---|---|---|
| 原创代码 | `skill_src/elite20-packager/scripts/*.py`、`scripts/*.py`、`tests/*.py` | **MIT** | 见根目录 `LICENSE` |
| 原创脚本 | `scripts/*.sh`、`赵怡涵_C4_demo/run_demo.sh` | **MIT** | 同上 |
| 原创文档 | 本包内全部 `*.md`（除下方引用项） | **CC BY 4.0** | 允许转载，需署名 |
| 官方规则数据 | `skill_src/elite20-packager/references/challenges_index.yaml` | **随上游，非本人版权** | 由 `build_challenge_index.py` 从官方 `challenge.json` 机器抽取；文件头已注明来源与生成命令 |
| 官方规则转写 | `skill_src/elite20-packager/references/checklist.yaml` | **随上游** | 从 `_交付规范_执行者必读.md` 转写成机器可读形式；文件头已注明 `source_docs` |
| 官方挑战文档 | 本包内**不含**任何官方文档副本 | — | 只以"引用路径"方式提及，未复制正文 |
| `skill-explainer.skill` | 本包内**不含** | ⚠️ 未标明 | 随官方资料包分发，包内无 License 文件。**仅借鉴结构与设计思路，未复制代码或文本** |
| `wechat-doc-mapper.skill` | 本包内**不含** | ⚠️ 未标明 | 同上 |

## 三、需要跟进的一项

⚠️ **【待赵怡涵执行】**：向群内确认 `07_C4 技能分享与传播/materials/` 下两个 `.skill` 文件（`skill-explainer.skill`、`wechat-doc-mapper.skill`）的 License 状态。

本包的处理方式是**保守的**：

1. **没有把它们复制进本包**（`find . -name "*.skill"` 只会命中本包自己的 `.skill`）；
2. 只借鉴了**结构与设计思路**（报告固定 section、注册表驱动的架构、CLI 形态），这些属于方法论层面；
3. 引用出处逐条写在 `赵怡涵_C4_拿来说明.md` 的"复用来源总表"里。

如果官方后续要求补充这两位作者的 License 声明，本文件会相应更新。

## 四、自检命令

```bash
# 确认包内不含两个官方 .skill 的副本
find . -name "*.skill"

# 确认没有复制官方技能里的代码/文本特征串
grep -rn "signal_keywords\|wechat_doc_mapper\|Skill Explainer\|D1 描述质量" \
     skill_src/ scripts/ tests/ || echo "未发现复制痕迹"
```
