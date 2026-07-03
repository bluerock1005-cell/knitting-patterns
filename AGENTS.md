# AGENTS.md

编织图纸管理系统 — 个人 PDF 编织图纸的元数据管理 + 静态网站生成 + GitHub Pages 发布。

## 项目概述

用户收集编织图纸 PDF，用 Ravelry 链接自动获取元数据（作者、线材、密度、针码、用量、尺码等），生成带搜索筛选的静态网页，发布到 GitHub Pages 分享。

## 技术栈

- Python 3.13 + PyQt6（GUI 桌面管理器）
- requests + BeautifulSoup4（Ravelry 抓取）
- pypdf（PDF 元数据读取）
- 纯静态 HTML/CSS/JS（生成的网站，零外部依赖）
- GitHub Pages `/docs` 模式发布

## 文件结构

```
knitting-patterns/
├── gui.py               # 双击启动管理器（自引导 venv）
├── manager.py           # PyQt6 桌面管理器（卡片式 UI，核心）
├── manager.bat          # Windows 备用启动脚本
├── generate_site.py     # 网页生成脚本
├── scan_patterns.py     # CLI 扫描未登记 PDF + Ravelry 交互
├── ravelry_scraper.py   # Ravelry 页面抓取 + CSV 字段映射
├── update.bat           # 命令行一键更新（生成+提交+推送）
├── patterns.csv         # 中央元数据清单
├── requirements.txt     # Python 依赖
├── .venv/               # 项目虚拟环境（gitignore）
├── docs/                # GitHub Pages 发布目录
│   ├── index.html       # 自动生成的网页
│   ├── patterns/        # PDF 图纸文件
│   └── images/          # 图案示例图片
├── 项目更新.md    # 项目更新日志
└── AGENTS.md
```

## 核心数据流

```
Ravelry URL
    ↓ ravelry_scraper.py
元数据 dict（title, designer, gauge, needle, yarn, yardage, sizes, rating, price, image_url）
    ↓ map_to_csv_fields()
CSV 字段（category, type, notes(中文标签), image(filename), url）
    ↓ generate_site.py
静态网页 docs/index.html（卡片网格 + 搜索 + 分类/类型筛选）
    ↓ git push
GitHub Pages 发布
```

## patterns.csv 字段

| 字段 | 说明 |
|------|------|
| filename | PDF 文件名 |
| title | 图纸名称 |
| category | 棒针 / 钩针 |
| type | Ravelry 官方分类（Tops / Other、Sweater / Cardigan...） |
| language | 语言（后台隐藏，GUI 和网站均不显示） |
| difficulty | 难度（后台隐藏，GUI 和网站均不显示） |
| notes | 备注（`|` 分隔：作者：xxx \| 结构标签 \| 针码：... \| 密度：... \| 建议线材：... \| 用量：... \| 尺码：... \| 评分：... \| 售价：...） |
| image | 图片文件名（存在 docs/images/） |
| url | Ravelry 原始链接 |

## GUI 对话框流程

1. ① 选择 PDF 文件 → 复制到 docs/patterns/
2. ② 粘贴 Ravelry 网址 → 自动从 URL 提取名称 + 自动抓取元数据
3. ③ 封面图片（可选）→ 手动上传或从 Ravelry 自动下载
4. ④ 确认/修改：名称、属性（分类+类型）、备注
5. 保存 → 写入 patterns.csv + 图片存入 docs/images/

## 桌面管理器功能

- **卡片瀑布流**：图纸以封面卡片展示，悬浮浮现编辑/删除按钮，双击打开编辑对话框
- **封面图片**：支持手动上传本地图片或从 Ravelry 自动获取
- **PDF 删除**：PDF 文件标签页支持删除文件，已收录的图纸会自动联动清除 CSV 记录
- **拖拽上传**：支持直接拖拽 PDF 文件到窗口批量添加
- **搜索筛选**：支持按标题、作者、线材、密度等关键字搜索
- **生成网页 + 推送 GitHub**：一键生成静态网页并推送到 GitHub Pages

## 网站设计决策

- 类型列直接使用 Ravelry 官方分类名（Tops / Other 等），不再映射为中文
- 语言和难度筛选项已移除，GUI 对话框中也隐藏
- 备注使用 ` | ` 分隔结构化信息，网页卡片解析为图标行
- 图片和 PDF 都在 docs/ 内（GitHub Pages `/docs` 模式只能访问此目录）
- 卡片显示：图片 → 名称 → 分类/类型标签 → 结构化信息行 → 下载+Ravelry链接
- 搜索栏支持搜索标题、作者、线材、密度、针码等关键字

## 常用命令

```bash
# 启动 GUI
python gui.py

# 扫描新 PDF（CLI 方式）
python scan_patterns.py

# 重新生成网页
python generate_site.py

# 一键更新（生成 + 提交 + 推送）
双击 update.bat

# 测试 Ravelry 抓取
python ravelry_scraper.py

# 安装/更新依赖
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

## 注意事项

- 所有路径现在指向 `docs/patterns/` 和 `docs/images/`（非项目根目录）
- Ravelry 抓取需要网络，失败时不影响手动填写
- 图片下载失败时网页显示 🧶 占位符
- `.venv` 和 `__pycache__` 已在 gitignore
- GitHub Pages 设置：Branch `main`，文件夹 `/docs`
