#!/usr/bin/env python3
"""
编织图纸管理器 - 网页生成脚本
读取 patterns.csv，生成带搜索和筛选功能的静态网页 docs/index.html
"""

import csv
import json
import os
import sys
from pathlib import Path

# Windows 控制台 UTF-8 输出
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ─── 路径配置 ───
SCRIPT_DIR = Path(__file__).parent.resolve()
CSV_PATH = SCRIPT_DIR / "patterns.csv"
PDF_DIR = SCRIPT_DIR / "patterns"
OUTPUT_DIR = SCRIPT_DIR / "docs"
OUTPUT_FILE = OUTPUT_DIR / "index.html"

# ─── 分类中文映射（可选，留空则直接显示原始值）───
CATEGORY_LABELS = {
    "棒针": "棒针",
    "钩针": "钩针",
}
DIFFICULTY_LABELS = {
    "初级": "初级",
    "中级": "中级",
    "高级": "高级",
}


def load_patterns(csv_path):
    """读取 CSV，返回图纸列表"""
    patterns = []
    if not csv_path.exists():
        print(f"⚠️  找不到 {csv_path}")
        return patterns

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 跳过空行
            if not row.get("filename"):
                continue
            patterns.append(
                {
                    "filename": row["filename"].strip(),
                    "title": row.get("title", "").strip() or row["filename"].strip(),
                    "category": row.get("category", "").strip(),
                    "type": row.get("type", "").strip(),
                    "language": row.get("language", "").strip(),
                    "difficulty": row.get("difficulty", "").strip(),
                    "notes": row.get("notes", "").strip(),
                    "image": row.get("image", "").strip(),
                    "url": row.get("url", "").strip(),
                }
            )
    return patterns


def build_html(patterns):
    """生成完整的 HTML 页面"""

    # 把数据嵌入页面供 JS 使用
    patterns_json = json.dumps(patterns, ensure_ascii=False)

    # 收集筛选项
    categories = sorted(set(p["category"] for p in patterns if p["category"]))
    types = sorted(set(p["type"] for p in patterns if p["type"]))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧶 编织图纸库</title>
    <style>
        :root {{
            --bg: #faf6f0;
            --card-bg: #ffffff;
            --primary: #b85c5c;
            --primary-light: #e8b4b4;
            --primary-dark: #8b3a3a;
            --text: #3a3027;
            --text-light: #8a7a6a;
            --border: #e5ddd3;
            --shadow: 0 2px 12px rgba(0,0,0,0.06);
            --radius: 14px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                         "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
        }}

        /* ─── 顶部头部 ─── */
        header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: #fff;
            padding: 2.5rem 1.5rem 2rem;
            text-align: center;
        }}
        header h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }}
        header p {{
            opacity: 0.85;
            font-size: 0.95rem;
        }}

        /* ─── 工具栏 ─── */
        .toolbar {{
            max-width: 1100px;
            margin: -1.2rem auto 0;
            padding: 0 1.5rem;
            position: relative;
            z-index: 10;
        }}
        .toolbar-inner {{
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1.2rem 1.5rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
            align-items: center;
        }}
        .search-box {{
            flex: 1 1 220px;
            position: relative;
        }}
        .search-box input {{
            width: 100%;
            padding: 0.6rem 0.8rem 0.6rem 2.3rem;
            border: 2px solid var(--border);
            border-radius: 10px;
            font-size: 0.95rem;
            transition: border-color 0.2s;
            background: var(--bg);
            color: var(--text);
        }}
        .search-box input:focus {{
            outline: none;
            border-color: var(--primary);
        }}
        .search-box::before {{
            content: "🔍";
            position: absolute;
            left: 0.7rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.9rem;
        }}
        select {{
            padding: 0.55rem 0.8rem;
            border: 2px solid var(--border);
            border-radius: 10px;
            font-size: 0.9rem;
            background: var(--bg);
            color: var(--text);
            cursor: pointer;
            transition: border-color 0.2s;
        }}
        select:focus {{ outline: none; border-color: var(--primary); }}

        .stats {{
            font-size: 0.85rem;
            color: var(--text-light);
            white-space: nowrap;
        }}

        /* ─── 卡片网格 ─── */
        .grid {{
            max-width: 1100px;
            margin: 1.5rem auto 3rem;
            padding: 0 1.5rem;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.2rem;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.15s, box-shadow 0.15s;
        }}
        .card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }}
        .card-thumb {{
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--primary-light), #f3d9d9);
            overflow: hidden;
        }}
        .card-thumb img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .card-thumb .placeholder {{
            font-size: 3rem;
        }}
        .card-body {{
            padding: 1rem 1.2rem 1.2rem;
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.6rem;
            color: var(--text);
        }}
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-bottom: 0.7rem;
        }}
        .tag {{
            font-size: 0.75rem;
            padding: 0.15rem 0.55rem;
            border-radius: 6px;
            background: var(--bg);
            color: var(--text-light);
            border: 1px solid var(--border);
        }}
        .tag.cat-棒针 {{ background: #fce8e8; color: #a04545; border-color: #f0c8c8; }}
        .tag.cat-钩针 {{ background: #e8f0fc; color: #4565a0; border-color: #c8d8f0; }}
        .tag.diff-初级 {{ background: #e8f5e9; color: #2e7d32; border-color: #c8e6c9; }}
        .tag.diff-中级 {{ background: #fff3e0; color: #e65100; border-color: #ffe0b2; }}
        .tag.diff-高级 {{ background: #fce4ec; color: #c62828; border-color: #f8bbd0; }}

        .card-notes {{
            font-size: 0.82rem;
            color: var(--text-light);
            margin-bottom: 0.8rem;
            flex: 1;
        }}
        .card-info {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            margin-bottom: 0.8rem;
            flex: 1;
            font-size: 0.78rem;
            color: var(--text-light);
        }}
        .info-item {{
            display: block;
            padding: 0.15rem 0;
            border-bottom: 1px dotted var(--border);
        }}
        .info-item:last-child {{
            border-bottom: none;
        }}
        .download-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.5rem 1rem;
            background: var(--primary);
            color: #fff;
            text-decoration: none;
            border-radius: 10px;
            font-size: 0.88rem;
            font-weight: 500;
            text-align: center;
            transition: background 0.2s;
            align-self: flex-start;
        }}
        .download-btn:hover {{
            background: var(--primary-dark);
        }}
        .card-actions {{
            display: flex;
            gap: 0.5rem;
            align-items: center;
            flex-wrap: wrap;
        }}
        .ravelry-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.5rem 0.8rem;
            color: var(--primary);
            text-decoration: none;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 500;
            border: 1.5px solid var(--primary-light);
            transition: background 0.2s;
        }}
        .ravelry-link:hover {{
            background: var(--primary-light);
            color: var(--primary-dark);
        }}

        /* ─── 空状态 ─── */
        .empty {{
            text-align: center;
            padding: 3rem 1.5rem;
            color: var(--text-light);
        }}
        .empty .emoji {{
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }}

        /* ─── 页脚 ─── */
        footer {{
            text-align: center;
            padding: 1.5rem;
            font-size: 0.8rem;
            color: var(--text-light);
        }}

        @media (max-width: 600px) {{
            header h1 {{ font-size: 1.5rem; }}
            .toolbar-inner {{ flex-direction: column; align-items: stretch; }}
            .search-box {{ flex: 1 1 100%; }}
            select {{ width: 100%; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>🧶 编织图纸库</h1>
        <p>我的毛线图纸收藏 · 点击下载 PDF</p>
    </header>

    <div class="toolbar">
        <div class="toolbar-inner">
            <div class="search-box">
                <input type="text" id="search" placeholder="搜索标题、作者、线材、密度、针码…" />
            </div>
            <select id="filter-category">
                <option value="">全部分类</option>
                {''.join(f'<option value="{c}">{c}</option>' for c in categories)}
            </select>
            <select id="filter-type">
                <option value="">全部类型</option>
                {''.join(f'<option value="{t}">{t}</option>' for t in types)}
            </select>
            <span class="stats" id="stats"></span>
        </div>
    </div>

    <div class="grid" id="grid"></div>

    <footer>
        由 generate_site.py 自动生成 · 数据来源 patterns.csv
    </footer>

    <script>
        const PATTERNS = {patterns_json};

        const grid = document.getElementById('grid');
        const stats = document.getElementById('stats');
        const searchInput = document.getElementById('search');
        const filters = {{
            category: document.getElementById('filter-category'),
            type: document.getElementById('filter-type'),
        }};

        function render() {{
            const q = searchInput.value.trim().toLowerCase();
            const fc = filters.category.value;
            const ft = filters.type.value;

            const filtered = PATTERNS.filter(p => {{
                if (q && !(p.title.toLowerCase().includes(q) || p.notes.toLowerCase().includes(q) || p.filename.toLowerCase().includes(q)))
                    return false;
                if (fc && p.category !== fc) return false;
                if (ft && p.type !== ft) return false;
                return true;
            }});

            stats.textContent = `共 ${{filtered.length}} / ${{PATTERNS.length}} 张`;

            if (filtered.length === 0) {{
                grid.innerHTML = `
                    <div class="empty" style="grid-column: 1 / -1;">
                        <div class="emoji">🧶</div>
                        <p>没有找到匹配的图纸</p>
                    </div>`;
                return;
            }}

            grid.innerHTML = filtered.map(p => {{
                const tags = [];
                if (p.category) tags.push(`<span class="tag cat-${{p.category}}">${{p.category}}</span>`);
                if (p.type) tags.push(`<span class="tag">${{p.type}}</span>`);
                if (p.language) tags.push(`<span class="tag">${{p.language}}</span>`);
                if (p.difficulty) tags.push(`<span class="tag diff-${{p.difficulty}}">${{p.difficulty}}</span>`);

                const hasImage = p.image && p.image.trim() !== '';
                const thumbContent = hasImage
                    ? `<img src="../images/${{encodeURIComponent(p.image)}}" alt="${{escapeHtml(p.title)}}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">`
                    : '';
                const thumbFallback = hasImage
                    ? `<span class="placeholder" style="display:none">🧶</span>`
                    : `<span class="placeholder">🧶</span>`;

                // 解析备注为结构化信息行
                let notesHtml = '';
                if (p.notes) {{
                    const parts = p.notes.split('|').map(s => s.trim()).filter(Boolean);
                    const infoItems = parts.map(part => {{
                        // 给每段加图标和样式
                        let icon = '📌';
                        if (part.startsWith('类型')) icon = '📂';
                        else if (part.startsWith('作者')) icon = '✍️';
                        else if (part.startsWith('建议线材')) icon = '🧵';
                        else if (part.startsWith('密度')) icon = '📐';
                        else if (part.startsWith('针码')) icon = '🪡';
                        else if (part.startsWith('用量')) icon = '📏';
                        else if (part.startsWith('尺码')) icon = '📊';
                        else if (part.startsWith('评分')) icon = '⭐';
                        else if (part.startsWith('售价')) icon = '💰';
                        return `<span class="info-item">${{icon}} ${{escapeHtml(part)}}</span>`;
                    }});
                    notesHtml = `<div class="card-info">${{infoItems.join('')}}</div>`;
                }}

                const ravelryLink = p.url && p.url.trim() !== ''
                    ? `<a class="ravelry-link" href="${{escapeHtml(p.url)}}" target="_blank" rel="noopener">🔗 Ravelry 原址</a>`
                    : '';

                return `
                    <div class="card">
                        <div class="card-thumb">${{thumbContent}}${{thumbFallback}}</div>
                        <div class="card-body">
                            <div class="card-title">${{escapeHtml(p.title)}}</div>
                            <div class="tags">${{tags.join('')}}</div>
                            ${{notesHtml}}
                            <div class="card-actions">
                                <a class="download-btn" href="../patterns/${{encodeURIComponent(p.filename)}}" download>
                                    📄 下载 PDF
                                </a>
                                ${{ravelryLink}}
                            </div>
                        </div>
                    </div>`;
            }}).join('');
        }}

        function escapeHtml(str) {{
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }}

        searchInput.addEventListener('input', render);
        filters.category.addEventListener('change', render);
        filters.type.addEventListener('change', render);

        render();
    </script>
</body>
</html>"""
    return html


def main():
    # 读取数据
    patterns = load_patterns(CSV_PATH)
    print(f"📖 读取到 {len(patterns)} 张图纸")

    # 检查 PDF 文件是否存在
    for p in patterns:
        pdf_path = PDF_DIR / p["filename"]
        if not pdf_path.exists():
            print(f"  ⚠️  警告: patterns/{p['filename']} 文件不存在")

    # 生成 HTML
    html = build_html(patterns)

    # 写入文件
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 网页已生成: {OUTPUT_FILE}")
    print(f"   共 {len(patterns)} 张图纸")


if __name__ == "__main__":
    main()
