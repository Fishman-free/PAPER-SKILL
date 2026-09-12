# CUMCM Paper Skill

> 中国大学生数学建模竞赛（国赛）论文写作专精 —— 面向 Claude Code 的写作规范、摘要范式、章节骨架与合规检查工具。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D16-brightgreen.svg)](https://nodejs.org/)

---

## 这是什么

一个 Claude Code Skill，把国赛论文写作从「凭感觉写」变成「按规范做」。

**提炼自**：3 篇真实国赛获奖论文（逐页拆解）+ 官方格式规范（2026 修订稿）+ 官方评阅工作规范 + 高校教学材料。

**核心内容**：

| 模块 | 内容 |
|------|------|
| 评阅标准 | 官方**四条评奖标准**、四级评审流程、获奖比例 —— 并**辟谣**网传的假评分表 |
| 三条红线 | 查重门槛（任一库 ≥25%）、AI 工具使用规定（2025 起试行）、参赛规则 |
| 摘要范式 | 4 种**从获奖论文提取的段落签名**、三件套、官方五要素、7 步打磨流程 |
| 分章写法 | 逐章「要回答什么 / 必须含什么 / 绝不要写什么」+ 参考句式 + 反例对照 |
| 获奖实例 | 3 篇论文的**摘要全文**、章节骨架对照、隐形加分项、反模式 |
| 格式规范 | 2026 修订稿十三条原文、匿名自查清单、图表公式规范、提交清单 |
| 合规脚本 | 自动检查格式硬约束与匿名红线 |
| LaTeX 模板 | cumcmthesis 文档类 + 13 个分章节源码 |

---

## 安装

### 方式一：npx（推荐）

```bash
npx cumcm-paper-skill
```

安装到用户级 `~/.claude/skills/cumcm-paper/`。

```bash
# 安装到当前项目（团队共享）
npx cumcm-paper-skill --project

# 覆盖已存在的安装
npx cumcm-paper-skill --force

# 卸载
npx cumcm-paper-skill --uninstall
```

### 方式二：手动安装

```bash
git clone https://github.com/Fishman-free/PAPER-SKILL.git
cp -r PAPER-SKILL/skill/cumcm-paper ~/.claude/skills/
```

Windows PowerShell：

```powershell
git clone https://github.com/Fishman-free/PAPER-SKILL.git
Copy-Item -Recurse PAPER-SKILL\skill\cumcm-paper $env:USERPROFILE\.claude\skills\
```

### 验证安装

重启 Claude Code，然后输入：

```
/help
```

应能在 skill 列表中看到 `cumcm-paper`。或者直接提问「国赛论文的摘要该怎么写」触发它。

---

## 使用

安装后，用自然语言提问即可自动激活：

### 摘要相关

```
帮我写一篇国赛论文的摘要，题目是……
这个摘要有什么问题？[粘贴摘要]
国赛摘要的关键词该怎么选？
```

### 结构与章节

```
帮我搭一个国赛论文的骨架
模型假设这一章该怎么写？
问题分析要注意什么？
灵敏度分析只给了图没有结论，怎么改？
```

### 合规与红线

```
国赛论文查重率多少会被刷？
用了 AI 写代码，论文里怎么声明？
格式规范对页数有什么要求？
提交前需要检查什么？
```

### 检查已有论文

```
帮我检查这篇论文的格式合规性
```

Claude 会调用 `scripts/check_paper.py`：

```bash
# 检查 LaTeX 源码（推荐）
python scripts/check_paper.py --latex main.tex --chapters chapter/

# 检查纯文本
python scripts/check_paper.py --text paper.txt

# 检查 PDF
python scripts/check_paper.py --pdf paper.pdf
```

检查项包括：电子版首页设置、目录、摘要环境、AI 声明、附录与代码、参考文献与引用标注、图表 caption、**身份信息泄露**（含路径、邮箱、占位符）、模糊表述、PDF 元数据。

---

## LaTeX 模板

`assets/latex-template/` 提供国赛专用模板：

```
assets/latex-template/
├── main.tex                      # 主文件
├── cumcmthesis.cls               # 国赛专用文档类
├── chapter/
│   ├── 1_restatement.tex         # 问题重述
│   ├── 2_analysis.tex            # 问题分析
│   ├── 3_assumptions.tex         # 模型假设
│   ├── 4_notation.tex            # 符号说明
│   ├── 5_model_q1.tex            # 问题一模型的建立与求解
│   ├── 6_model_q2.tex            # 问题二……
│   ├── 7_model_q3.tex            # 问题三……
│   ├── 8_sensitivity.tex         # 灵敏度分析
│   ├── 9_evaluation.tex          # 模型评价与推广
│   ├── 10_ai_declaration.tex     # AI 使用声明
│   ├── 11_reference.tex          # 参考文献
│   └── A_appendix.tex            # 附录（文件列表 + 代码）
└── figures/
```

**编译**（必须 XeLaTeX）：

```bash
xelatex main.tex
xelatex main.tex   # 第二次生成正确的引用与页码
```

**电子版提交**：改用

```latex
\documentclass[withoutpreface,bwprint]{cumcmthesis}
```

否则第一页是承诺书，违反《论文格式规范》第十条（电子版第一页必须为摘要专用页）。

---

## 三条红线（务必记住）

### 1. 查重：任一库 ≥ 25% 原则上不能报送全国评阅

知网**全文库**或竞赛**自建库**任一 ≥ 25%。

⚠️ **自建库才是主要杀伤源**。官方通报实例中多篇作品的全文库相似度仅 0–5.6%，而**自建库 100%** —— 说明是**队间互抄**。

**所以**：不与其他队伍交换素材，不抄袭同校往届论文（自建库含历年参赛论文）。

### 2. AI 使用：声明 + 《AI工具使用详情.pdf》

自 2025-09-01 起试行。允许使用，但须：

1. 正文相应位置标注
2. 参考文献著录：`[编号] 工具名称，版本/型号，开发机构/公司，使用日期`
3. 支撑材料附《AI工具使用详情.pdf》

**核心建模与分析必须由参赛队独立完成。** 隐瞒或虚假声明 → 取消评奖资格。

### 3. 参赛规则：不与队外交流赛题

⚠️ **加入赛题讨论群但被动接收也算违纪。**

---

## 🔴 辟谣：这些流传甚广的说法是假的

| 说法 | 真相 |
|------|------|
| 「摘要 35 分」「建模创造性 25 分」 | ❌ 官方**从未**发布任何权重。多个版本互相矛盾 |
| 「国一 90–100 分等级线」 | ❌ 无官方依据 |
| 「2024 年起 AIGC 检测，需低于 40%」 | ❌ 唯一来源是第三方技术博客。官方 2025 年全部相似度通报**只提知网自建库与全文库检测，完全未提 AIGC** |
| 「30 秒看摘要定档」「60–70% 淘汰率」 | ❌ 来自经验帖，且与其他说法互相矛盾 |

**官方只有四条评奖标准，没有权重表。按那四条打磨论文，不要按假评分表分配精力。**

---

## 诚实边界

1. **不能预测当年评阅细则** —— 「评阅要点」是评阅组内部材料，赛前不公开
2. **不能替你做建模** —— 本 skill 管「怎么写」，不管「做什么模型」
3. **不能保证获奖** —— 2025 年本科组全国一等奖比例约 0.48%（61,463 队中 294 队）
4. **规则会变** —— 本文档基于截至 2026-09-12 的官方文件，**每年赛前必须核对当届原文**
5. **三篇论文是样本** —— 提炼自物理建模、生产决策两类题型，其他题型可能有差异

---

## 相关 Skill

如果你需要**完整的数学建模流水线**（选题 → 分析建模 → 编码出图 → 论文排版），那是另一个技能：

- [`math-modeling`](https://github.com/Fishman-free) —— 三阶段建模流程
- `5writing` —— 竞赛论文撰写（Typst/LaTeX 双引擎）

本 skill 的定位是**国赛论文写作的深度专精**：评阅视角、获奖范式、合规红线。自包含，不依赖上述技能。

---

## 贡献

欢迎提交 Issue 与 PR：

- 发现规则版本更新（官网原文变更）
- 补充其他题型的获奖论文范式
- 报告脚本误报/漏报

**注意**：本项目只收录**有官方依据**的规则。引用经验性说法必须标注可信度等级并说明来源。

---

## 致谢

- 论文格式规范、评阅工作规范、AI 工具使用规定：全国大学生数学建模竞赛组委会
- LaTeX 模板：`cumcmthesis` 文档类
- 获奖论文范例：B060、B195、B196（用于结构与写法分析）

---

## License

[MIT](LICENSE)
