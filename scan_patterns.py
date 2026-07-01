#!/usr/bin/env python3
"""
编织图纸扫描脚本
扫描 patterns/ 文件夹，自动发现未登记的 PDF，
解析文件名提取分类/类型/语言，读取 PDF 元数据提取标题，
支持从 Ravelry 链接自动获取元数据填充备注，
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

# 尝试导入 Ravelry 抓取模块
try:
    from ravelry_scraper import fetch_ravelry_pattern, map_to_csv_fields
    HAS_RAVELRY = True
except ImportError:
    HAS_RAVELRY = False

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


def fetch_ravelry_info():
    """交互式获取 Ravelry 元数据，返回 CSV 字段建议"""
    url = input("  请输入 Ravelry 链接（直接回车跳过）: ").strip()
    if not url:
        return None

    if not HAS_RAVELRY:
        print("   ⚠️  缺少 ravelry_scraper 模块，跳过 Ravelry 抓取")
        return None

    print("   🔍 正在从 Ravelry 获取信息...")
    try:
        scraped = fetch_ravelry_pattern(url)
    except Exception as e:
        print(f"   ❌ Ravelry 抓取失败: {e}")
        return None

    if scraped.get("_error") and not scraped.get("title"):
        print(f"   ❌ Ravelry 抓取失败: {scraped['_error']}")
        return None

    csv_fields = map_to_csv_fields(scraped)
    csv_fields["url"] = url

    # 展示预览
    print()
    print(f"   📋 从 Ravelry 获取到以下信息：")
    print(f"      标题:    {scraped.get('title', '')}")
    print(f"      设计师:  {scraped.get('designer', '')}")
    print(f"      分类:    {csv_fields.get('category', '')}")
    print(f"      类型:    {csv_fields.get('type', '')}")
    print(f"      语言:    {csv_fields.get('language', '')}")
    print(f"      难度:    {csv_fields.get('difficulty', '')}")
    notes = csv_fields.get('notes', '')
    if len(notes) > 80:
        notes = notes[:80] + "…"
    print(f"      备注:    {notes}")
    print()

    while True:
        choice = input("  是否采用？(y=采用 / n=跳过 / e=编辑备注后采用): ").strip().lower()
        if choice in ("y", "yes", "是"):
            return csv_fields
        elif choice in ("n", "no", "否", ""):
            return None
        elif choice in ("e", "edit", "编辑"):
            print(f"   当前备注: {csv_fields['notes']}")
            new_notes = input("   请输入新备注（直接回车保留原备注）: ").strip()
            if new_notes:
                csv_fields["notes"] = new_notes
            return csv_fields
        else:
            print("   无效输入，请输入 y / n / e")


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

        # 尝试从 Ravelry 获取元数据
        ravelry_fields = fetch_ravelry_info()

        new_entry = {
            "filename": filename,
            "title": parsed["title"],
            "category": parsed["category"],
            "type": parsed["type"],
            "language": parsed["language"],
            "difficulty": "",
            "notes": "",
            "image": "",
            "url": "",
        }

        # 如果从 Ravelry 获取到了信息，合并到条目中
        if ravelry_fields:
            if ravelry_fields.get("url"):
                new_entry["url"] = ravelry_fields["url"]
            if ravelry_fields.get("title"):
                new_entry["title"] = ravelry_fields["title"]
            if ravelry_fields.get("category"):
                new_entry["category"] = ravelry_fields["category"]
            if ravelry_fields.get("type"):
                new_entry["type"] = ravelry_fields["type"]
            if ravelry_fields.get("language"):
                new_entry["language"] = ravelry_fields["language"]
            if ravelry_fields.get("difficulty"):
                new_entry["difficulty"] = ravelry_fields["difficulty"]
            if ravelry_fields.get("notes"):
                new_entry["notes"] = ravelry_fields["notes"]
            if ravelry_fields.get("image"):
                new_entry["image"] = ravelry_fields["image"]

        new_pdfs.append(new_entry)
        print()

    return new_pdfs


def append_to_csv(new_patterns):
    """将新图纸追加到 CSV"""
    fieldnames = ["filename", "title", "category", "type", "language", "difficulty", "notes", "image", "url"]

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
