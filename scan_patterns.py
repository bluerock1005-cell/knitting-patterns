#!/usr/bin/env python3
"""
编织图纸扫描脚本
扫描 patterns/ 文件夹，自动发现未登记的 PDF，
解析文件名提取分类/类型/语言，读取 PDF 元数据提取标题，
生成或更新 patterns.csv。
"""

import csv
import os
import re
import sys
from pathlib import Path

# Windows 控制台 UTF-8
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).parent.resolve()
CSV_PATH = SCRIPT_DIR / "patterns.csv"
PDF_DIR = SCRIPT_DIR / "patterns"

# ─── 分类体系 ───
CATEGORIES = {"棒针", "钩针"}
TYPES = {
    "毛衫", "开衫", "背心", "围巾", "帽子", "袜子",
    "手套", "披肩", "毯子", "玩偶", "其他",
}
LANG_MAP = {
    "中": "中", "中文": "中", "cn": "中", "zh": "中",
    "日": "日", "日文": "日", "日文版": "日", "jp": "日", "ja": "日",
    "英": "英", "英文": "英", "英文版": "英", "en": "英",
}


def read_pdf_title(pdf_path):
    """尝试从 PDF 元数据读取标题"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        if reader.metadata:
            title = reader.metadata.get("/Title", "")
            if title and len(title.strip()) > 1:
                return title.strip()
    except Exception:
        pass
    return ""


def parse_filename(filename):
    """
    解析文件名，尝试提取分类、类型、语言。
    支持的命名格式：
      棒针_毛衫_麻花开衫_日文.pdf
      钩针围巾_菠萝花_中.pdf
      TwistVeil_Blouse.pdf  (无法解析的，返回原始名)
    """
    stem = Path(filename).stem  # 去掉 .pdf
    parts = re.split(r"[_\-]", stem)

    category = ""
    pattern_type = ""
    language = ""
    title_parts = []

    for part in parts:
        part_stripped = part.strip()
        if not part_stripped:
            continue

        # 检查语言
        lower = part_stripped.lower()
        if not language and lower in LANG_MAP:
            language = LANG_MAP[lower]
            continue

        # 检查分类（棒针/钩针 可能和其他词连在一起）
        if not category:
            for cat in CATEGORIES:
                if cat in part_stripped:
                    category = cat
                    # 从 part 中移除分类词，剩余部分留作 title
                    remaining = part_stripped.replace(cat, "").strip("_-")
                    if remaining and remaining not in TYPES:
                        title_parts.append(remaining)
                    break
            else:
                # 检查类型
                if not pattern_type:
                    for t in TYPES:
                        if t in part_stripped:
                            pattern_type = t
                            remaining = part_stripped.replace(t, "").strip("_-")
                            if remaining:
                                title_parts.append(remaining)
                            break
                    else:
                        title_parts.append(part_stripped)
                else:
                    title_parts.append(part_stripped)
        else:
            # 已找到分类，继续找类型
            if not pattern_type:
                for t in TYPES:
                    if t in part_stripped:
                        pattern_type = t
                        remaining = part_stripped.replace(t, "").strip("_-")
                        if remaining:
                            title_parts.append(remaining)
                        break
                else:
                    title_parts.append(part_stripped)
            else:
                title_parts.append(part_stripped)

    title = " ".join(title_parts).strip() if title_parts else stem

    return {
        "category": category,
        "type": pattern_type,
        "language": language,
        "title": title,
    }


def load_existing_csv():
    """读取现有 CSV 中的文件名集合"""
    existing = set()
    if CSV_PATH.exists():
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("filename"):
                    existing.add(row["filename"].strip())
    return existing


def scan_pdfs():
    """扫描 PDF 文件夹，返回未登记的 PDF 列表"""
    existing = load_existing_csv()
    new_pdfs = []

    if not PDF_DIR.exists():
        print(f"⚠️  patterns/ 文件夹不存在")
        return new_pdfs

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        filename = pdf_path.name
        if filename in existing:
            continue

        print(f"  📄 发现新文件: {filename}")

        # 解析文件名
        parsed = parse_filename(filename)

        # 尝试读取 PDF 元数据标题
        pdf_title = read_pdf_title(pdf_path)
        if pdf_title:
            parsed["title"] = pdf_title

        new_pdfs.append({
            "filename": filename,
            "title": parsed["title"],
            "category": parsed["category"],
            "type": parsed["type"],
            "language": parsed["language"],
            "difficulty": "",
            "notes": "",
        })

    return new_pdfs


def append_to_csv(new_patterns):
    """将新图纸追加到 CSV"""
    fieldnames = ["filename", "title", "category", "type", "language", "difficulty", "notes"]

    # 如果 CSV 不存在，创建并写入表头
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for p in new_patterns:
            writer.writerow(p)


def main():
    print("=" * 50)
    print("  编织图纸扫描脚本")
    print("=" * 50)
    print()

    # 读取现有记录数
    existing = load_existing_csv()
    print(f"📋 已登记图纸: {len(existing)} 张")
    print(f"📁 扫描文件夹: {PDF_DIR}")
    print()

    # 扫描新 PDF
    new_pdfs = scan_pdfs()

    if not new_pdfs:
        print()
        print("✅ 没有发现未登记的 PDF，所有文件已在清单中。")
        return

    print()
    print(f"🆕 共发现 {len(new_pdfs)} 张未登记的 PDF：")
    print()
    for i, p in enumerate(new_pdfs, 1):
        info_parts = []
        if p["category"]:
            info_parts.append(p["category"])
        if p["type"]:
            info_parts.append(p["type"])
        if p["language"]:
            info_parts.append(p["language"])
        info = " / ".join(info_parts) if info_parts else "（待补充）"
        print(f"  {i}. {p['title']}")
        print(f"     文件: {p['filename']}")
        print(f"     信息: {info}")
        print()

    # 确认写入
    answer = input("是否将以上记录写入 patterns.csv？(y/n): ").strip().lower()
    if answer in ("y", "yes", "是"):
        append_to_csv(new_pdfs)
        print(f"\n✅ 已写入 {len(new_pdfs)} 条记录到 patterns.csv")
        print("💡 请手动检查并补充难度、备注等字段。")
    else:
        print("\n已取消，未写入任何数据。")


if __name__ == "__main__":
    main()
