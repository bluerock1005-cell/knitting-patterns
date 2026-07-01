# 🧶 编织图纸库

个人编织图纸（PDF）管理系统：用 CSV 记录图纸信息，一键生成带搜索和筛选功能的网页，通过 GitHub Pages 免费分享给朋友下载。

## 文件结构

```
knitting-patterns/
├── patterns/            # PDF 原文件
│   └── TwistVeil_Blouse.pdf
├── patterns.csv         # 图纸清单（标题、分类、难度等）
├── generate_site.py     # 网页生成脚本
├── scan_patterns.py     # 扫描文件夹 + Ravelry 自动获取
├── ravelry_scraper.py   # Ravelry 页面信息抓取模块
├── manager.py           # PyQt6 桌面管理器（推荐）
├── manager.bat          # 桌面管理器启动脚本
├── update.bat           # 命令行一键更新脚本
├── requirements.txt     # Python 依赖
├── docs/                # 网页输出目录（GitHub Pages 发布源）
│   └── index.html       # 自动生成的网页
└── README.md
```

## 两种使用方式

### 方式一：桌面管理器（推荐，点点鼠标就行）

双击 `manager.bat` 启动图形界面，可以：

- **添加 PDF** — 选择文件，自动读取 PDF 标题，填表保存
- **编辑/删除** — 双击表格中的行编辑，或选中后删除
- **扫描文件夹** — 一键发现 patterns/ 中未登记的 PDF，批量导入
- **生成网页** — 点击按钮重新生成 docs/index.html
- **推送 GitHub** — 自动生成网页 + git commit + git push

### 方式二：命令行（适合批量操作）

```bash
# 扫描 patterns/ 文件夹，自动生成 CSV 初稿
python scan_patterns.py

# 重新生成网页
python generate_site.py

# 提交并推送
git add -A && git commit -m "更新" && git push
```

或直接双击 `update.bat`。

## patterns.csv 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| filename | PDF 文件名（须与 patterns/ 中的文件一致） | TwistVeil_Blouse.pdf |
| title | 显示标题 | TwistVeil 罩衫 |
| category | 分类：棒针 / 钩针 | 棒针 |
| type | 类型：毛衫 / 围巾 / 帽子... | 毛衫 |
| language | 语言：中 / 日 / 英 | 英 |
| difficulty | 难度：初级 / 中级 / 高级 | 中级 |
| notes | 备注（可选） | 镂空绞花女士罩衫 |

## 分类体系

| 字段 | 可选值 |
|------|--------|
| 分类 (category) | 棒针、钩针 |
| 类型 (type) | 毛衫、开衫、背心、围巾、帽子、袜子、手套、披肩、毯子、玩偶、其他 |
| 语言 (language) | 中、日、英 |
| 难度 (difficulty) | 初级、中级、高级 |

## 文件命名规范（建议）

统一命名格式，方便扫描脚本自动解析：

```
分类_类型_名称_语言.pdf
```

示例：
```
棒针_毛衫_麻花开衫_日文.pdf
钩针_围巾_菠萝花_中.pdf
棒针_帽子_渔夫帽_英.pdf
```

不符合此格式的文件也能正常使用，只是需要手动填写分类信息。

## Ravelry 自动获取信息 🆕

添加新图纸时，只需粘贴 Ravelry 图案链接，系统会自动抓取并填充：

- **标题、设计师**
- **分类、类型、难度**
- **针号、密度**
- **用线、尺码范围**
- **评分、售价**

### 在桌面管理器中使用

1. 点击「添加 PDF」，选择文件
2. 在「Ravelry」输入框粘贴链接（如 `https://www.ravelry.com/patterns/library/twistveil-blouse`）
3. 点击「获取信息」，等 2-3 秒
4. 表单自动填充，检查确认后保存

### 在命令行中使用

```bash
python scan_patterns.py
```

扫描到新 PDF 后，会提示输入 Ravelry 链接，粘贴后自动获取信息并预览，确认后写入 CSV。

### 手动抓取

也可以单独使用抓取模块查看某图案的信息：

```bash
python ravelry_scraper.py
```

> **注意**：抓取依赖网络连接，需要能访问 ravelry.com。如果抓取失败，仍可正常手动填写信息。

## 备份建议

`patterns.csv` 是所有图纸的索引，丢了要重新整理。建议：

1. **GitHub 仓库** — 每次 push 自动备份到 GitHub
2. **本地副本** — 把 patterns.csv 复制一份到 OneDrive 或其他云盘
3. **定期导出** — 图纸多了以后，可以用管理器导出 CSV 副本

---

## 首次部署到 GitHub Pages（只需做一次）

### 1. 注册 GitHub 账号

前往 https://github.com/signup 免费注册。

### 2. 安装 Git（如果还没有）

下载安装：https://git-scm.com/download/win

安装后在终端验证：
```bash
git --version
```

### 3. 在 GitHub 新建仓库

- 点击右上角 **+** → **New repository**
- 仓库名填 `knitting-patterns`
- 选择 **Public**（公开，否则 Pages 无法免费使用）
- 勾选 **Add a README file**
- 点击 **Create repository**

### 4. 关联本地项目到 GitHub

在项目文件夹内打开终端（右键 → Git Bash Here），执行：

```bash
# 初始化 Git
git init

# 关联远程仓库（把 你的用户名 换成你的 GitHub 用户名）
git remote add origin https://github.com/你的用户名/knitting-patterns.git

# 首次提交
git add -A
git commit -m "初始化编织图纸库"
git branch -M main
git push -u origin main
```

### 5. 开启 GitHub Pages

1. 打开仓库页面 → **Settings** → 左侧 **Pages**
2. **Source** 选择 **Deploy from a branch**
3. **Branch** 选 `main`，文件夹选 `/docs`
4. 点击 **Save**

等 2-3 分钟，你的网页就上线了：

```
https://你的用户名.github.io/knitting-patterns/
```

把这个链接发给朋友就能访问了！

### 以后每次更新

只需双击 `update.bat`，脚本自动完成：生成网页 → 提交 → 推送。几分钟后网页自动更新。

## 常见问题

**Q: 推送时提示权限错误？**
A: 需要配置 Git 身份信息和认证。运行：
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```
首次推送时会弹出登录窗口，按提示登录 GitHub 即可。

**Q: 网页打开后 PDF 下载不了？**
A: 确保 PDF 文件确实在 `patterns/` 文件夹中，且文件名与 CSV 中记录的完全一致（区分大小写）。

**Q: 想修改网页样式？**
A: 编辑 `generate_site.py` 中的 HTML 模板和 CSS，然后重新运行脚本即可。
