#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CUMCM 论文合规性自检工具

把《全国大学生数学建模竞赛论文格式规范》的硬性条款和常见扣分点
变成可自动检测的检查项。

用法：
    # 检查 LaTeX 源码（推荐，最早发现问题）
    python check_paper.py --latex main.tex --chapters chapter/

    # 检查纯文本（从 PDF 复制或用 pdftotext 提取）
    python check_paper.py --text paper.txt

    # 检查 PDF（需要 pypdf 或 pymupdf）
    python check_paper.py --pdf paper.pdf

    # 同时检查 LaTeX 源码与生成的 PDF
    python check_paper.py --latex main.tex --chapters chapter/ --pdf paper.pdf

退出码：
    0 = 无 ERROR
    1 = 存在 ERROR
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Windows 控制台默认 GBK，强制切到 UTF-8 以便输出中文与符号
for _stream in ("stdout", "stderr"):
    _s = getattr(sys, _stream, None)
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# ---------------------------------------------------------------- 终端着色

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"

    @classmethod
    def disable(cls):
        for name in ("RESET", "BOLD", "DIM", "RED", "GREEN", "YELLOW", "CYAN"):
            setattr(cls, name, "")

if os.name == "nt" and not os.environ.get("WT_SESSION"):
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        C.disable()

# ---------------------------------------------------------------- 检查框架

class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []
        self.passed = []

    def error(self, code, msg, detail=None):
        self.errors.append((code, msg, detail))

    def warn(self, code, msg, detail=None):
        self.warnings.append((code, msg, detail))

    def info(self, code, msg, detail=None):
        self.infos.append((code, msg, detail))

    def ok(self, code, msg):
        self.passed.append((code, msg))

    def print(self):
        print()
        print(f"{C.BOLD}{'=' * 68}{C.RESET}")
        print(f"{C.BOLD}  CUMCM 论文合规性自检报告{C.RESET}")
        print(f"{C.BOLD}{'=' * 68}{C.RESET}")

        if self.errors:
            print(f"\n{C.RED}{C.BOLD}[ERROR] 必须修复（可能导致取消评奖资格）{C.RESET}")
            for code, msg, detail in self.errors:
                print(f"  {C.RED}✗{C.RESET} [{code}] {msg}")
                if detail:
                    for line in str(detail).splitlines():
                        print(f"      {C.DIM}{line}{C.RESET}")

        if self.warnings:
            print(f"\n{C.YELLOW}{C.BOLD}[WARN] 建议修复（影响印象分）{C.RESET}")
            for code, msg, detail in self.warnings:
                print(f"  {C.YELLOW}!{C.RESET} [{code}] {msg}")
                if detail:
                    for line in str(detail).splitlines():
                        print(f"      {C.DIM}{line}{C.RESET}")

        if self.infos:
            print(f"\n{C.CYAN}{C.BOLD}[INFO] 信息提示{C.RESET}")
            for code, msg, detail in self.infos:
                print(f"  {C.CYAN}i{C.RESET} [{code}] {msg}")
                if detail:
                    for line in str(detail).splitlines():
                        print(f"      {C.DIM}{line}{C.RESET}")

        if self.passed:
            print(f"\n{C.GREEN}{C.BOLD}[PASS] 通过{C.RESET}")
            for code, msg in self.passed:
                print(f"  {C.GREEN}✓{C.RESET} [{code}] {msg}")

        n_err, n_warn = len(self.errors), len(self.warnings)
        print()
        print(f"{C.BOLD}{'-' * 68}{C.RESET}")
        if n_err:
            print(f"{C.RED}{C.BOLD}结果：{n_err} 个 ERROR，{n_warn} 个 WARN{C.RESET}")
        elif n_warn:
            print(f"{C.YELLOW}{C.BOLD}结果：0 个 ERROR，{n_warn} 个 WARN{C.RESET}")
        else:
            print(f"{C.GREEN}{C.BOLD}结果：全部通过{C.RESET}")
        print(f"{C.BOLD}{'-' * 68}{C.RESET}")
        print()


# ---------------------------------------------------------------- 匿名检查

# 高置信度的身份泄露特征
ANON_PATTERNS = [
    # 学校名：匹配校名主体 + 前瞻抓取紧随的 0~3 个尾字符。
    #   字符类用 \w（Python3 中匹配 Unicode 单词字符，含中文与 ASCII），
    #   这样「XX大学」「xxxx大学」这类占位符写法也能被捕获。
    #   例：「我们以中国大学生名誉」→ group(1)='中国大学', group(2)='生名誉'
    #       「以江苏科技大学为例」  → group(1)='江苏科技大学', group(2)='为例'
    # ⚠️ 尾字符必须用前瞻 `((?=.{0,3}).{0,3})` 而非 `(.{0,3})`：
    #    后者在过滤失败时会被正则回溯缩短，把真实泄露的「XX大学张三同学」
    #    变成 group(2)='张三同'，从而绕过 SCHOOL_TAIL_OK 的「同学」判断。
    (r"(\w{2,8}?(?:大学|学院))((?=.{0,3}).{0,3})", "疑似出现学校名称"),
    (r"(学号|班号|队号)\s*[:：]\s*\w+", "疑似出现学号/班号/队号"),
    (r"(指导教师|指导老师|带队老师|教练)\s*[:：]", "疑似出现指导教师字段"),
    (r"(队长|队员|组员|我们组|本组|本队|本团队)\s*[:：]",
     "疑似出现队伍自指表述"),
    (r"(20\d{2})\s*级\s*\d+\s*班", "疑似出现年级班级"),
    (r"(通信地址|邮编|联系电话|手机号|联系邮箱)\s*[:：]", "疑似出现联系方式"),
    (r"[\w.\-]+@[\w\-]+\.(?:com|cn|edu|net|org)", "疑似出现邮箱地址"),
]

# 整行跳过：LaTeX 结构命令、规范/竞赛术语、参考文献条目
ANON_SKIP_LINE = re.compile(
    r"(\\bibitem|\\begin\{thebibliography\}|\\cite|\\ref|\\url|\\href"
    r"|参赛须知|竞赛章程|格式规范|数学建模竞赛|使用规定|AI使用详情"
    # 参考文献条目特征（PDF 提取后不再有 \bibitem）
    r"|\[[JMDCNR]\]|DOI:|doi:|\[EB/OL\]|\[Z\]|\[A\]"
    r"|高教学刊|学报|出版社|大学教育|教育学报"
    r"|,\s*\d{4}\s*[,，]\s*\d+\s*\(|0?[1-9]\d{3}[,，]\s*\d+)\s*[:(：]"
    # LaTeX 模板预置的身份字段（用户本就要填写/替换，且电子版会被 withoutpreface 去掉）
    r"|\\schoolname|\\baominghao|\\membera|\\memberb|\\memberc|\\supervisor|\\tihao"
)

# 正常语境白名单（出现在命中处附近则不算泄露）
ANON_ALLOWLIST = re.compile(
    r"(参考文献|引用|摘自|来源|发表于|作者|该大学|某大学|学报|期刊|杂志"
    r"|竞赛|比赛|章程|规程|规范|须知|声明|参赛队|评审|评阅|题目|赛题"
    r"|为例|本文|论文|建模|研究)"
)

# 学校名匹配的「尾字符白名单」：正文出现「…大学」后接这些【多字】学术/竞赛语素时，
# 属引用或规范语境，非身份泄露。
#   例：以江苏科技大学【为例】、佳木斯职业学院【学报】、大学【教育】
# ⚠️ 不要加入「的/由/和/在」等单字虚词——它们会掩盖「由XX大学张三同学完成」这类真实泄露。
SCHOOL_TAIL_OK = re.compile(
    r"^(为例|学报|团队|队伍|校园|生数学|数学|教育|出版社|的文章|的研究"
    # 「…大学生名誉/诚信」——承诺书固定表述
    r"|生名誉|生诚信"
    # PDF 提取可能把「…职业学院学报」拆行，尾字符退化为单个「学」
    r"|学)"
)

# 明确不是学校名的固定短语（正则可能误切其中的「XX大学」）
SCHOOL_NAME_WHITELIST = re.compile(
    r"(全国大学生数学建模竞赛|大学生数学建模|数学建模竞赛|大学生数学建模竞赛"
    r"|全国大学生|中国大学生|大学生在线|高职高专|本科组"
    # 承诺书/章程中的固定表述
    r"|中国大学生名誉|大学生名誉|大学生诚信)"
)

# LaTeX 注释中的路径泄露
PATH_PATTERNS = [
    (r"[A-Za-z]:\\Users\\[^\\\s]+", "Windows 用户目录路径（可能含姓名）"),
    (r"/home/[a-zA-Z0-9_\-]+", "Linux 家目录路径（可能含用户名）"),
    (r"/Users/[a-zA-Z0-9_\-]+", "macOS 用户目录路径"),
]


def _is_false_positive_school(full_match, tail_matched, ctx):
    """判定「疑似学校名」是不是误报。

    三种误报来源：
    1. 竞赛/学术固定短语（全国大学生数学建模竞赛）
    2. 引用他校的学术语境（以江苏科技大学为例、佳木斯职业学院学报）
    3. 匹配尾部接的是常用虚词（…大学的、…学院和）
    """
    if SCHOOL_NAME_WHITELIST.search(full_match):
        return True
    if SCHOOL_TAIL_OK.match(tail_matched or ""):
        return True
    if re.search(r"(为例|学报|学院学报|期刊|杂志|作者|发表)", ctx):
        return True
    return False


def check_anonymity(text, report, source_label):
    """检查身份信息泄露（规范第六条）

    误报控制原则：allowlist 只在【紧邻命中处】生效，不用宽上下文窗口——
    否则「…指导教师：李四…参考文献…」会因远处出现「参考文献」而被放过。
    """
    found_any = False

    for pattern, desc in ANON_PATTERNS:
        is_school = "学校名称" in desc
        for m in re.finditer(pattern, text):
            ctx_start = max(0, m.start() - 30)
            ctx_end = min(len(text), m.end() + 30)
            ctx = text[ctx_start:ctx_end].replace("\n", " ").strip()

            # allowlist 只看命中处紧邻的 8 个字符（前后各 8）
            near_start = max(0, m.start() - 8)
            near_end = min(len(text), m.end() + 8)
            near = text[near_start:near_end].replace("\n", " ")

            # 排除常见的非身份用法（命中处紧邻的语境）
            if re.search(r"(参考文献|引用|摘自|来源|发表于|学报|期刊|杂志)", near):
                continue
            if re.match(r"^[\)\）\]】]", ctx) or re.search(r"\[[JMDCNR]\]", near):
                continue

            if is_school:
                school_name = m.group(1)
                tail = m.group(2) or ""
                if _is_false_positive_school(school_name, tail, near):
                    continue

            report.error(
                "ANON",
                f"{desc}（{source_label}）",
                f"…{ctx}…",
            )
            found_any = True

    for pattern, desc in PATH_PATTERNS:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            ctx = text[start:end].replace("\n", " ").strip()
            report.error("ANON", f"{desc}（{source_label}）", f"…{ctx}…")
            found_any = True

    # 模板里常见的待填占位符
    placeholders = re.findall(r"(XX大学|某大学|xxxxx|XXXXX|XXXX|＿＿＿|_{4,})", text)
    if placeholders:
        report.warn(
            "ANON",
            f"发现 {len(placeholders)} 处可能未填写的占位符（{source_label}）",
            "占位符： " + ", ".join(sorted(set(placeholders))[:8]),
        )

    if not found_any:
        report.ok("ANON", f"未发现明显的身份信息泄露（{source_label}）")


def check_anonymity_lines(text, report, source_label):
    """逐行版本：跳过参考文献条目等正常语境行"""
    kept = []
    for line in text.splitlines():
        if ANON_SKIP_LINE.search(line):
            kept.append("[已跳过：文献/规范/竞赛术语行]")
        else:
            kept.append(line)
    check_anonymity("\n".join(kept), report, source_label)


# ---------------------------------------------------------------- LaTeX 检查

def collect_latex_text(main_path, chapters_dir=None):
    r"""收集 LaTeX 源码（主文件 + \input 的章节文件）"""
    parts = []
    main = Path(main_path)
    if not main.exists():
        return None

    main_src = main.read_text(encoding="utf-8", errors="ignore")
    parts.append((str(main), main_src))

    # 解析 \input{...} / \include{...}
    includes = re.findall(r"\\(?:input|include)\{([^}]+)\}", main_src)
    base = main.parent
    for inc in includes:
        for cand in (base / inc, base / (inc + ".tex"), Path(inc)):
            if cand.exists() and cand.is_file():
                parts.append((str(cand), cand.read_text(encoding="utf-8", errors="ignore")))
                break

    # 目录里其它 .tex
    if chapters_dir:
        cdir = Path(chapters_dir)
        if cdir.is_dir():
            known = {Path(p).resolve() for p, _ in parts}
            for f in sorted(cdir.glob("*.tex")):
                if f.resolve() not in known:
                    parts.append((str(f), f.read_text(encoding="utf-8", errors="ignore")))

    return parts


def strip_latex_comments(src):
    """去掉 LaTeX 注释行（注释里的身份信息不算泄露，但路径要查）"""
    lines = []
    for line in src.splitlines():
        # 保留注释内容用于路径检查，这里不删
        lines.append(line)
    return "\n".join(lines)


def check_latex(main_path, chapters_dir, report):
    parts = collect_latex_text(main_path, chapters_dir)
    if parts is None:
        report.error("FILE", f"找不到 LaTeX 主文件：{main_path}")
        return None

    combined = "\n".join(src for _, src in parts)
    report.info("FILE", f"读取 {len(parts)} 个 LaTeX 文件",
                "\n".join(os.path.basename(p) for p, _ in parts[:20]))

    # --- 检查 1：电子版是否用了 withoutpreface（规范第十条）
    if re.search(r"\\documentclass\s*\[[^\]]*withoutpreface", combined):
        report.ok("SPEC-10", "使用 withoutpreface 选项（电子版第一页为摘要页）")
    elif re.search(r"\\documentclass\{cumcmthesis\}", combined):
        report.warn(
            "SPEC-10",
            "主文件使用默认 documentclass，生成的 PDF 首页为承诺书",
            "电子版提交时需改为：\\documentclass[withoutpreface,bwprint]{cumcmthesis}\n"
            "（规范第十条：电子版论文的第一页必须为摘要专用页）",
        )

    # --- 检查 2：是否有目录（规范第四条：不要目录）
    if re.search(r"\\tableofcontents", combined):
        report.error("SPEC-4", "发现 \\tableofcontents —— 规范第四条明确要求「不要目录」")
    else:
        report.ok("SPEC-4", "未发现目录")

    # --- 检查 3：摘要页
    if re.search(r"\\begin\{abstract\}", combined):
        report.ok("SPEC-3", "发现摘要环境")
    else:
        report.warn("SPEC-3", "未发现 \\begin{abstract}，确认摘要页是否存在")

    # --- 检查 4：AI 使用声明
    if re.search(r"AI\s*使用声明|AI使用声明|ai_declaration", combined):
        report.ok("AI", "发现 AI 使用声明")
    else:
        report.warn(
            "AI",
            "未发现 AI 使用声明章节",
            "近年国赛要求声明 AI 使用情况，请核对当届《参赛须知》",
        )

    # --- 检查 5：附录与代码
    if re.search(r"\\appendix", combined):
        report.ok("SPEC-5", "发现 \\appendix 附录区")
    else:
        report.error("SPEC-5", "未发现 \\appendix —— 规范第五条要求附录含完整源代码")

    if re.search(r"\\begin\{lstlisting\}|\\begin\{minted\}|\\begin\{verbatim\}", combined):
        report.ok("SPEC-5", "附录中发现代码环境")
    else:
        report.warn("SPEC-5", "未发现代码排版环境（lstlisting/minted/verbatim）")

    # --- 检查 6：参考文献
    if re.search(r"\\bibliography\{|\\begin\{thebibliography\}", combined):
        report.ok("SPEC-7", "发现参考文献环境")
    else:
        report.error("SPEC-7", "未发现参考文献 —— 规范第七条要求列出参考文献")

    if re.search(r"\\cite\{", combined):
        report.ok("SPEC-7", "正文中发现 \\cite 引用标注")
    else:
        report.warn(
            "SPEC-7",
            "正文中未发现 \\cite —— 规范第七条要求在正文引用处予以标注",
        )

    # --- 检查 7：图表是否有 caption
    figs = re.findall(r"\\begin\{figure\}(.*?)\\end\{figure\}", combined, re.S)
    tabs = re.findall(r"\\begin\{table\}(.*?)\\end\{table\}", combined, re.S)
    fig_no_cap = [f for f in figs if "\\caption" not in f]
    tab_no_cap = [t for t in tabs if "\\caption" not in t]
    if fig_no_cap:
        report.warn("FIG", f"{len(fig_no_cap)} 个 figure 环境缺少 \\caption（图题）")
    if tab_no_cap:
        report.warn("TAB", f"{len(tab_no_cap)} 个 table 环境缺少 \\caption（表题）")
    if figs and not fig_no_cap:
        report.ok("FIG", f"全部 {len(figs)} 个图都有图题")
    if tabs and not tab_no_cap:
        report.ok("TAB", f"全部 {len(tabs)} 个表都有表题")

    # --- 检查 8：匿名（对 LaTeX 源码，跳过文献/规范术语行）
    check_anonymity_lines(combined, report, "LaTeX 源码")

    # --- 检查 9：单位是否误用斜体
    bad_units = re.findall(r"\$[^$]*?\b(?:cm|mm|km|kg|ms|μm|um)\b[^$]*?\$", combined)
    if bad_units:
        report.info(
            "MATH",
            f"发现 {len(bad_units)} 处单位出现在数学模式中，确认是否应用正体",
            "单位建议用 \\mathrm{} 或 \\text{}，不要用斜体",
        )

    # --- 检查 10：函数名是否用了正体
    bad_funcs = re.findall(r"\$(?![^$]*\\\w{2,})[^$]*\b(sin|cos|tan|log|ln|max|min|exp|lim)\b[^$]*\$", combined)
    if bad_funcs:
        report.warn(
            "MATH",
            "数学模式中疑似直接书写函数名（sin/cos/log/…）",
            "应使用 \\sin \\cos \\log \\max \\min \\exp \\lim（正体）",
        )

    return parts


# ---------------------------------------------------------------- 文本检查

def check_text(text, report, label):
    # 目录
    if re.search(r"^\s*目\s*录\s*$", text, re.M):
        report.error("SPEC-4", f"发现「目录」—— 规范第四条明确要求不要目录（{label}）")

    # 英文摘要
    if re.search(r"^\s*(Abstract|ABSTRACT)\s*$", text, re.M):
        report.error("SPEC-3", f"发现英文摘要 —— 规范第三条明确「无需翻译成英文」（{label}）")
    else:
        report.ok("SPEC-3", f"未发现英文摘要（{label}）")

    # 承诺书/编号页出现在电子版里
    if re.search(r"承诺书", text):
        report.warn(
            "SPEC-10",
            f"文本中发现「承诺书」—— 电子版不应包含承诺书页（{label}）",
        )

    # 匿名
    check_anonymity_lines(text, report, label)

    # 模糊表述（摘要/结果里最常见）
    vague = ["结果较好", "结果良好", "模型合理", "得到满意结果", "效果理想",
             "较为准确", "符合要求", "达到了预期"]
    hits = [v for v in vague if v in text]
    if hits:
        report.warn(
            "VAGUE",
            f"发现 {len(hits)} 类模糊表述，应替换为具体数值或机制描述（{label}）",
            "命中： " + "、".join(hits),
        )
    else:
        report.ok("VAGUE", f"未发现常见模糊表述（{label}）")


# ---------------------------------------------------------------- PDF 检查

def check_pdf(pdf_path, report):
    text = None
    page_count = None

    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        text = "\n".join(p.get_text() for p in doc)
        meta = doc.metadata or {}
    except ImportError:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            meta = dict(reader.metadata or {})
        except ImportError:
            report.warn("PDF", "未安装 pypdf/pymupdf，跳过 PDF 检查",
                        "安装： pip install pypdf  或  pip install pymupdf")
            return
        except Exception as e:
            report.error("PDF", f"读取 PDF 失败：{e}")
            return
    except Exception as e:
        report.error("PDF", f"读取 PDF 失败：{e}")
        return

    report.info("PDF", f"共 {page_count} 页")

    # 正文页数：无法从 PDF 精确区分正文与附录，做粗略提示
    if page_count > 30:
        report.info(
            "SPEC-4",
            f"PDF 共 {page_count} 页（> 30）",
            "规范第四条：正文不超过 30 页，附录页数不限。\n"
            "若正文确实 ≤ 30 页则无问题，请自行确认正文与附录的分界。",
        )
    else:
        report.ok("SPEC-4", f"总页数 {page_count} ≤ 30")

    # 元数据泄露
    for key in ("title", "author", "creator", "producer"):
        val = (meta or {}).get(key)
        if val and str(val).strip():
            if key in ("author", "title"):
                report.warn(
                    "META",
                    f"PDF 元数据 {key} = 「{val}」，确认不含身份信息",
                    "建议导出时清空元数据",
                )
            else:
                report.info("META", f"PDF 元数据 {key} = 「{val}」")

    # 文本层
    if text and len(text.strip()) > 100:
        check_text(text, report, "PDF 文本层")
    else:
        report.info(
            "PDF",
            "PDF 无文本层（扫描件），无法做全文检查",
            "如需检查，请提供 LaTeX 源码或纯文本",
        )


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(
        description="CUMCM 论文合规性自检",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--latex", metavar="MAIN.TEX", help="LaTeX 主文件路径")
    ap.add_argument("--chapters", metavar="DIR", help="LaTeX 章节目录（可选）")
    ap.add_argument("--text", metavar="FILE", help="纯文本文件路径")
    ap.add_argument("--pdf", metavar="FILE", help="PDF 文件路径")
    args = ap.parse_args()

    if not any([args.latex, args.text, args.pdf]):
        ap.print_help()
        print(f"\n{C.YELLOW}请至少指定 --latex、--text 或 --pdf 之一{C.RESET}\n")
        sys.exit(2)

    report = Report()

    if args.latex:
        check_latex(args.latex, args.chapters, report)

    if args.text:
        p = Path(args.text)
        if not p.exists():
            report.error("FILE", f"找不到文本文件：{args.text}")
        else:
            check_text(p.read_text(encoding="utf-8", errors="ignore"), report, "文本文件")

    if args.pdf:
        p = Path(args.pdf)
        if not p.exists():
            report.error("FILE", f"找不到 PDF：{args.pdf}")
        else:
            check_pdf(str(p), report)

    report.print()
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
