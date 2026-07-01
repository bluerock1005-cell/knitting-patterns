#!/usr/bin/env python3
"""
Ravelry 图案页面抓取模块
从 Ravelry 图案页面提取结构化元数据，并映射为 patterns.csv 字段。
"""

import re
import sys
from pathlib import Path

# Windows 控制台 UTF-8
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ─── 路径常量（供其他模块引用）───
SCRIPT_DIR = Path(__file__).parent.resolve()

# ─── 分类映射 ───
CATEGORY_MAP = {
    "棒针": "棒针",
    "钩针": "钩针",
}

# Ravelry craft → 中文分类
CRAFT_TO_CATEGORY = {
    "knitting": "棒针",
    "crochet": "钩针",
}

# Ravelry category keywords → 中文类型
CATEGORY_TO_TYPE = {
    # 上衣类
    "pullover": "毛衫",
    "sweater": "毛衫",
    "jumper": "毛衫",
    "cardigan": "开衫",
    "vest": "背心",
    "slipover": "背心",
    "top": "罩衫",
    "blouse": "罩衫",
    "tee": "罩衫",
    "tank": "罩衫",
    "bolero": "罩衫",
    "shrug": "罩衫",
    # 围巾披肩
    "scarf": "围巾",
    "cowl": "围巾",
    "shawl": "披肩",
    "wrap": "披肩",
    "stole": "披肩",
    "poncho": "披肩",
    # 帽子
    "hat": "帽子",
    "beanie": "帽子",
    "beret": "帽子",
    "hood": "帽子",
    "earflap": "帽子",
    "bonnet": "帽子",
    # 袜子
    "sock": "袜子",
    "stocking": "袜子",
    # 手套
    "glove": "手套",
    "mitten": "手套",
    "mitt": "手套",
    "fingerless": "手套",
    # 毯子
    "blanket": "毯子",
    "afghan": "毯子",
    "throw": "毯子",
    # 玩偶
    "doll": "玩偶",
    "toy": "玩偶",
    "animal": "玩偶",
    "amigurumi": "玩偶",
    # 其他
    "bag": "其他",
    "cushion": "其他",
    "pillow": "其他",
    "cozy": "其他",
    "coaster": "其他",
}

# 语言映射
LANG_TO_CN = {
    "chinese": "中",
    "english": "英",
    "japanese": "日",
    "french": "法",
    "german": "德",
    "spanish": "西",
    "korean": "韩",
    "russian": "俄",
    "italian": "意",
    "portuguese": "葡",
    "dutch": "荷",
    "norwegian": "挪",
    "swedish": "瑞",
    "danish": "丹",
    "finnish": "芬",
    "polish": "波",
    "czech": "捷",
    "turkish": "土",
}

# 难度映射
DIFFICULTY_MAP = {
    "beginner": "初级",
    "easy": "初级",
    "intermediate": "中级",
    "medium": "中级",
    "advanced": "高级",
    "expert": "高级",
}


def fetch_ravelry_pattern(url):
    """抓取 Ravelry 图案页面，返回结构化元数据字典。

    返回字段:
        title, designer, craft, category_text, published,
        languages_raw, price, difficulty_raw, yardage,
        gauge, needle_sizes, sizes, yarns,
        rating_overall, rating_clarity, clarity_votes,
        techniques, description, projects_count, queued_count,
        url, source_name
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {"_error": "缺少依赖，请运行: pip install requests beautifulsoup4"}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    result = {
        "title": "",
        "designer": "",
        "craft": "",
        "category_text": "",
        "published": "",
        "languages_raw": "",
        "price": "",
        "difficulty_raw": "",
        "yardage": "",
        "gauge": "",
        "needle_sizes": "",
        "sizes": "",
        "sizes_list": "",
        "yarns": [],
        "yarn_weight": "",
        "rating_overall": "",
        "rating_clarity": "",
        "clarity_votes": "",
        "techniques": [],
        "description": "",
        "projects_count": "",
        "queued_count": "",
        "url": url,
        "source_name": "",
        "image_url": "",
        "_error": "",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        result["_error"] = f"网络请求失败: {e}"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── 页面全文（用于正则提取）──
    page_text = soup.get_text(separator="\n", strip=False)

    # ══════════════════════════════════════
    #  标题 & 设计师（从 <title> 标签解析）
    # ══════════════════════════════════════
    title_tag = soup.select_one("title")
    raw_title = title_tag.get_text(strip=True) if title_tag else ""

    # 格式: "Ravelry: TwistVeil Blouse pattern by Natalja Ledvanova"
    title_match = re.search(
        r"Ravelry\s*:\s*(.+?)\s*pattern\s+by\s+(.+)",
        raw_title, re.IGNORECASE,
    )
    if title_match:
        result["title"] = title_match.group(1).strip()
        result["designer"] = title_match.group(2).strip()
    else:
        result["title"] = re.sub(r"\s*[-–|]\s*Ravelry\s*$", "", raw_title).strip()

    # ══════════════════════════════════════
    #  示例图片（从 og:image 或页面主图提取）
    # ══════════════════════════════════════
    og_image = soup.select_one('meta[property="og:image"]')
    if og_image:
        result["image_url"] = og_image.get("content", "")
    if not result["image_url"]:
        # 尝试从页面主图获取（medium2 或 small2 尺寸）
        for img in soup.select("img.lazy_srcset, img.height_lock"):
            src = img.get("src", "")
            if "ravelrycache.com/uploads" in src and "_medium" in src:
                result["image_url"] = src
                break
            elif "ravelrycache.com/uploads" in src and "_small" in src:
                result["image_url"] = src
                break
    if not result["image_url"]:
        # 尝试任意上传图片
        for img in soup.select("img"):
            src = img.get("src", "")
            if "ravelrycache.com/uploads/" in src and any(
                s in src for s in ("_medium", "_small2", "_square")
            ):
                result["image_url"] = src
                break
    # 如果只有 small2，尝试升级为 medium2（更大更清晰）
    if "_small2" in result["image_url"]:
        medium_url = result["image_url"].replace("_small2", "_medium2")
        result["image_url"] = medium_url  # medium2 存在则用，不存在会 fallback

    # ══════════════════════════════════════
    #  核心元数据（通过 .core_item_content__label 精确定位）
    # ══════════════════════════════════════
    label_map = {
        "Craft": "craft",
        "Category": "category_text",
        "Published": "published",
        "Yardage": "yardage",
        "Gauge": "gauge",
        "Needle size": "needle_sizes",
        "Sizes available": "sizes_list",
        "Languages": "languages_raw",
        "Suggested yarn": "yarn_suggested",
        "Yarn weight": "yarn_weight",
        "Published in": "source_name",
    }

    for label_el in soup.select(".core_item_content__label"):
        label_text = label_el.get_text(strip=True)
        parent = label_el.parent
        if not parent:
            continue

        # 父元素文本: "Label | value1 | value2 | ..."
        full_text = parent.get_text(separator=" | ", strip=True)

        for label_key, field_name in label_map.items():
            if label_text == label_key:
                # 去掉 label 前缀，取后续值
                value = full_text.replace(label_key + " | ", "", 1).strip()
                if value and value != label_key:
                    # 清理 category 中的面包屑 "Tops | → | Other" → "Tops / Other"
                    if field_name == "category_text":
                        value = re.sub(r"\s*\|\s*→\s*\|", " / ", value).replace("  ", " ")
                    if field_name == "sizes_list":
                        result["sizes_list"] = value
                    elif field_name == "yarn_suggested":
                        result["yarns"] = [
                            y.strip() for y in value.split(" | ")
                            if y.strip() and "both" not in y.lower()
                        ]
                    elif field_name == "yarn_weight":
                        result["yarn_weight"] = value
                    else:
                        result[field_name] = value
                break

    # ══════════════════════════════════════
    #  价格
    # ══════════════════════════════════════
    price_match = re.search(
        r"(?:€|USD|£|¥|EUR|GBP|\$)\s*[\d.]+\s*(?:EUR|USD|GBP)?",
        page_text,
    )
    if price_match:
        result["price"] = price_match.group(0).strip()

    # ══════════════════════════════════════
    #  难度（从页面文本搜索 Level）
    # ══════════════════════════════════════
    diff_match = re.search(
        r"(?:Level|Difficulty)\s*\n?\s*:?\s*\n?\s*([^\n]+)",
        page_text, re.IGNORECASE,
    )
    if diff_match:
        result["difficulty_raw"] = diff_match.group(1).strip()

    # ══════════════════════════════════════
    #  尺码详情（胸围尺寸表）
    # ══════════════════════════════════════
    # 搜索 "FINISHED MEASUREMENTS" 后面的尺码数据
    sizes_match = re.search(
        r"FINISHED\s+MEASUREMENTS[^\n]*\n((?:[^\n]+\n?){1,10})",
        page_text, re.IGNORECASE,
    )
    if sizes_match:
        sizes_lines = [l.strip() for l in sizes_match.group(1).split("\n") if l.strip()]
        # 过滤掉非尺码行（如 "Suggested yarn"）
        sizes_lines = [
            l for l in sizes_lines
            if re.search(r"(?:XS|S\b|M\b|L\b|XL|XXL|XXXL|\d+cm|\d+\")", l)
            and "Suggested" not in l
        ]
        if sizes_lines:
            result["sizes"] = " ".join(sizes_lines)

    # Fallback: 搜索 "Sizes: XS, S, M..." 后的尺码数据
    if not result["sizes"]:
        sizes_match2 = re.search(
            r"Sizes?\s*:\s*(XS,?\s*S,?\s*M,?\s*L,?\s*XL,?\s*XXL[^\n]*)",
            page_text, re.IGNORECASE,
        )
        if sizes_match2:
            # 继续读取后续的 Bust/Length 行
            pos = sizes_match2.end()
            subsequent = page_text[pos:pos + 500]
            bust_lines = re.findall(
                r"((?:XS|S|M|L|XL|XXL|XXXL)\s+\d+cm\s*\([^)]+\)[^\n]*)",
                subsequent,
            )
            if bust_lines:
                result["sizes"] = " ".join(bust_lines)

    # ══════════════════════════════════════
    #  评分
    # ══════════════════════════════════════
    overall_match = re.search(
        r"overall\s+rating\D*([\d.]+)\D*(\d+)\s*votes?",
        page_text, re.IGNORECASE,
    )
    if overall_match:
        result["rating_overall"] = f"{overall_match.group(1)}/5.0 (来自{overall_match.group(2)}票)"

    clarity_match = re.search(
        r"clarity\s+rating\D*([\d.]+)\D*(\d+)\s*votes?",
        page_text, re.IGNORECASE,
    )
    if clarity_match:
        result["rating_clarity"] = f"{clarity_match.group(1)}/5.0 (来自{clarity_match.group(2)}票)"

    # ══════════════════════════════════════
    #  技法/属性
    # ══════════════════════════════════════
    # 搜索标签/属性块。这些在页面中通常是以空格分隔的小写词列表
    # 位置通常在语言区块之后，以 "adult chart female..." 开头
    LANG_NAMES = {
        "english", "french", "german", "spanish", "japanese", "chinese",
        "korean", "russian", "italian", "portuguese", "dutch", "norwegian",
        "swedish", "danish", "finnish", "polish", "czech", "turkish",
    }
    # 找多个连续的小写单词（用双空格或逗号分隔），通常是属性标签
    attr_match = re.search(
        r"((?:adult|baby|child|teen|female|male|unisex)\s+[a-z][-a-z]*(?:\s{2,}[a-z][-a-z]*)+)",
        page_text, re.IGNORECASE,
    )
    if not attr_match:
        attr_match = re.search(
            r"((?:adult|baby|child|teen)\s+chart[^\n]*)",
            page_text, re.IGNORECASE,
        )
    if attr_match:
        techs_text = attr_match.group(1).strip()
        # 按双空格分割
        raw_techs = [t.strip() for t in re.split(r"\s{2,}", techs_text) if t.strip()]
        # 过滤掉语言名
        result["techniques"] = [
            t for t in raw_techs
            if t.lower() not in LANG_NAMES and len(t) > 2
        ]
        if not result["techniques"]:
            # Fallback: 按空格分割+过滤
            result["techniques"] = [
                w.strip(",")
                for w in techs_text.split()
                if len(w) > 2 and w.lower() not in LANG_NAMES
            ]

    # ══════════════════════════════════════
    #  描述
    # ══════════════════════════════════════
    desc_match = re.search(
        r"(?:Description|Notes?|简介)\s*\n\s*(.+?)(?:\n\s*\n|\n(?:Tags|Hashtags|Pattern|About|$))",
        page_text, re.DOTALL | re.IGNORECASE,
    )
    if desc_match:
        desc = desc_match.group(1).strip()
        if len(desc) > 500:
            desc = desc[:500] + "…"
        result["description"] = re.sub(r"\s+", " ", desc).strip()

    # ══════════════════════════════════════
    #  作品/排队数
    # ══════════════════════════════════════
    proj_match = re.search(r"(\d+[\d,]*)\s*projects?", page_text, re.IGNORECASE)
    if proj_match:
        result["projects_count"] = proj_match.group(1)

    queue_match = re.search(
        r"(\d+[\d,]*)\s*(?:queued?|in\s+queue)", page_text, re.IGNORECASE,
    )
    if queue_match:
        result["queued_count"] = queue_match.group(1)

    return result


def map_to_csv_fields(scraped):
    """将 Ravelry 元数据映射为 CSV 字段建议值。

    参数:
        scraped: fetch_ravelry_pattern() 返回的 dict

    返回:
        {category, type, language, difficulty, notes}
    """
    result = {
        "category": "",
        "type": "",
        "language": "",
        "difficulty": "",
        "notes": "",
    }

    if scraped.get("_error") and not scraped.get("title"):
        result["notes"] = f"[抓取失败: {scraped['_error']}]"
        return result

    # ── 分类（棒针/钩针）──
    craft = scraped.get("craft", "").lower()
    if "crochet" in craft:
        result["category"] = "钩针"
    elif "knit" in craft:
        result["category"] = "棒针"

    # ── 类型（直接使用 Ravelry 网站的 Category 分类）──
    cat_text = scraped.get("category_text", "").strip()
    if cat_text:
        result["type"] = cat_text

    # ── 语言 ──
    langs = scraped.get("languages_raw", "").lower()
    lang_codes = []
    for lang_en, lang_cn in LANG_TO_CN.items():
        if lang_en in langs:
            lang_codes.append(lang_cn)
    # 也尝试从原始文本直接匹配中文
    if not lang_codes:
        for lang_en, lang_cn in LANG_TO_CN.items():
            if lang_cn in langs:
                lang_codes.append(lang_cn)
    if lang_codes:
        result["language"] = "/".join(lang_codes)

    # ── 难度 ──
    diff = scraped.get("difficulty_raw", "").lower()
    diff_found = []
    for eng, cn in DIFFICULTY_MAP.items():
        if eng in diff:
            if cn not in diff_found:
                diff_found.append(cn)
    if len(diff_found) >= 2:
        # "中高级" or "初中级" — 取首尾
        result["difficulty"] = diff_found[0] + diff_found[-1].replace(
            diff_found[0], ""
        ) if diff_found[-1].startswith(diff_found[0]) else diff_found[0] + diff_found[-1]
        # 确保是 "中高级" 而不是 "中级高级"
        result["difficulty"] = result["difficulty"].replace("中中", "中").replace("级高", "高").replace("级初", "初")
    elif len(diff_found) == 1:
        result["difficulty"] = diff_found[0]

    # ── 备注（简体中文标签）──
    notes_parts = []

    # 作者
    designer = scraped.get("designer", "")
    if designer:
        notes_parts.append(f"作者：{designer}")

    # 结构描述
    techs = scraped.get("techniques", [])
    structure_keywords = {
        "top-down": "从上往下",
        "bottom-up": "从下往上",
        "seamless": "无缝",
        "in-the-round": "圈织",
        "worked-flat": "片织",
        "v-neck": "V领",
        "crew-neck": "圆领",
        "long-sleeve": "长袖",
        "short-sleeve": "短袖",
        "sleeveless": "无袖",
        "fitted": "合身版",
        "positive-ease": "宽松版",
        "negative-ease": "紧身版",
        "lace": "蕾丝",
        "cable": "绞花",
        "colorwork": "提花",
        "stripes": "条纹",
        "lace-edge": "蕾丝边",
        "button": "有扣",
    }
    structure = []
    for tech in techs:
        t = tech.lower().strip()
        if t in structure_keywords:
            structure.append(structure_keywords[t])
    if structure:
        notes_parts.append("、".join(structure))

    # 棒针针码
    needles = scraped.get("needle_sizes", "")
    if needles:
        # 提取 mm 数字
        mm_match = re.findall(r"([\d.]+)\s*mm", needles)
        if mm_match:
            notes_parts.append(f"针码：{'/'.join(mm_match)}mm")

    # 密度
    gauge = scraped.get("gauge", "")
    if gauge:
        # 简化密度信息
        gauge_simple = re.search(
            r"(\d+)\s*(?:stitches|针).*?(\d+)\s*(?:rows|行)", gauge, re.IGNORECASE
        )
        if gauge_simple:
            notes_parts.append(
                f"密度：{gauge_simple.group(1)}针×{gauge_simple.group(2)}行"
            )
        else:
            # 截取前 40 字
            notes_parts.append(f"密度：{gauge[:40]}")

    # 建议线材
    yarns = scraped.get("yarns", [])
    if yarns:
        # 每个 yarn 条目可能很长，只取前两个词（通常是品牌+线名）
        short_yarns = []
        for y in yarns:
            words = y.split()
            # 取前 3 个词作为简略名称
            short_name = " ".join(words[:3]) if len(words) > 3 else y
            if short_name not in short_yarns:
                short_yarns.append(short_name)
        yarn_text = " + ".join(short_yarns)
        if len(yarn_text) > 60:
            yarn_text = yarn_text[:60] + "…"
        notes_parts.append(f"建议线材：{yarn_text}")

    # 尺码（紧凑格式：XS-XXL 86-123cm胸围）
    sizes = scraped.get("sizes", "")
    if sizes:
        # 尝试提取尺码范围和胸围范围
        size_range_match = re.findall(
            r"((?:XS|S|M|L|XL|XXL|XXXL))\s+\d+cm\s*\([^)]+\)",
            sizes,
        )
        if size_range_match:
            # 找到第一个和最后一个尺码标签
            size_labels = re.findall(
                r"(XS|S\b|M\b|L\b|XL|XXL|XXXL)", sizes,
            )
            bust_cm = re.findall(r"(\d+)cm\s*\((\d+)[”\"']", sizes)
            if size_labels and bust_cm:
                size_range = f"{size_labels[0]}-{size_labels[-1]}"
                bust_range = f"{bust_cm[0][0]}-{bust_cm[-1][0]}cm"
                notes_parts.append(f"尺码：{size_range}（{bust_range}胸围）")
            else:
                notes_parts.append(f"尺码：{sizes[:80]}")
        else:
            notes_parts.append(f"尺码：{sizes[:80]}")


    # 线材用量（码数）
    yardage = scraped.get("yardage", "")
    if yardage:
        yd_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*yards?", yardage, re.IGNORECASE)
        if yd_match:
            notes_parts.append(f"用量：{yd_match.group(1)}-{yd_match.group(2)}码")
        else:
            m_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*m", yardage, re.IGNORECASE)
            if m_match:
                notes_parts.append(f"用量：{m_match.group(1)}-{m_match.group(2)}m")
            else:
                notes_parts.append(f"用量：{yardage[:40]}")
    # 评分
    rating = scraped.get("rating_overall", "")
    if rating:
        notes_parts.append(f"评分：{rating}")

    # 价格
    price = scraped.get("price", "")
    if price:
        notes_parts.append(f"售价：{price}")

    result["notes"] = " | ".join(notes_parts)

    return result


def download_image(image_url, save_dir, filename=None):
    """下载图案示例图片到本地。

    参数:
        image_url: 图片 URL
        save_dir: 保存目录（Path 对象或字符串）
        filename: 保存文件名（不含扩展名），默认从 URL 提取

    返回:
        保存的文件名（含扩展名），失败返回空字符串
    """
    import requests as req

    if not image_url:
        return ""

    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 从 URL 提取扩展名
    ext_match = re.search(r"\.(jpe?g|png|webp|gif)(?:\?|$)", image_url, re.IGNORECASE)
    ext = ext_match.group(1) if ext_match else "jpg"

    # 生成文件名
    if not filename:
        # 从 URL 中提取原始文件名
        url_filename = re.search(r"/([^/]+\.(?:jpe?g|png|webp|gif))(?:\?|$)", image_url, re.IGNORECASE)
        if url_filename:
            filename = Path(url_filename.group(1)).stem
        else:
            filename = "pattern_image"

    safe_name = re.sub(r"[^\w\-_]", "_", filename)
    save_path = save_dir / f"{safe_name}.{ext}"

    # 如果已存在则跳过
    if save_path.exists():
        return save_path.name

    try:
        resp = req.get(image_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }, timeout=20)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return save_path.name
    except Exception:
        return ""


# ─── 自测 ───
if __name__ == "__main__":
    test_url = "https://www.ravelry.com/patterns/library/twistveil-blouse"
    print(f"🔍 抓取: {test_url}")
    print("=" * 60)

    data = fetch_ravelry_pattern(test_url)

    if data.get("_error") and not data.get("title"):
        print(f"❌ 错误: {data['_error']}")
        sys.exit(1)

    print(f"📌 标题:       {data['title']}")
    print(f"👤 设计师:     {data['designer']}")
    print(f"🧵 Craft:      {data['craft']}")
    print(f"📂 分类:       {data['category_text']}")
    print(f"📅 发布日期:   {data['published']}")
    print(f"🌐 语言:       {data['languages_raw']}")
    print(f"💰 价格:       {data['price']}")
    print(f"📊 难度:       {data['difficulty_raw']}")
    print(f"📏 用线量:     {data['yardage']}")
    print(f"📐 密度:       {data['gauge']}")
    print(f"🪡 针号:       {data['needle_sizes']}")
    print(f"📏 尺码:       {data['sizes'][:120] if data['sizes'] else ''}...")
    print(f"⭐ 总评分:     {data['rating_overall']}")
    print(f"📝 清晰度:     {data['rating_clarity']}")
    print(f"🏷️  技法:      {', '.join(data['techniques'][:10])}...")
    print(f"📦 作品数:     {data['projects_count']}")
    print()

    print("── 映射为 CSV 字段 ──")
    csv_fields = map_to_csv_fields(data)
    for k, v in csv_fields.items():
        print(f"  {k}: {v}")
