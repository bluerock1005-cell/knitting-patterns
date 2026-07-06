"""manager.py - 编织图纸管理器（双击直接运行）"""
import subprocess
import sys
from pathlib import Path

# ─── 虚拟环境自引导 ───
HERE = Path(__file__).parent.resolve()
VENV_DIR = HERE / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"
VENV_PYW = VENV_DIR / "Scripts" / "pythonw.exe"

if not VENV_PY.exists():
    print("正在创建虚拟环境，首次运行需要1-2分钟…")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    subprocess.run(
        [str(VENV_PY), "-m", "pip", "install",
         "PyQt6", "pypdf", "requests", "beautifulsoup4"],
        check=True,
    )
    print("初始化完成，正在启动…")

if str(sys.executable).lower() not in (str(VENV_PY).lower(), str(VENV_PYW).lower()):
    # 如果是从 pythonw.exe 启动的（无窗口），继续用 pythonw.exe 启动
    target = str(VENV_PYW) if sys.executable.lower().endswith('pythonw.exe') else str(VENV_PY)
    subprocess.Popen([target, __file__])
    sys.exit(0)

# ─── 主程序（下面已经是 venv 环境）───
"""
编织图纸管理器 - PyQt6 桌面应用
功能：表格管理图纸、搜索、添加/编辑/删除、扫描未登记 PDF、
      一键生成网页、一键推送 GitHub。
"""

import csv
import json
import os
import re
import shutil

  # ─── 路径常量 ───
SCRIPT_DIR = Path(__file__).parent.resolve()
CSV_PATH = SCRIPT_DIR / "patterns.csv"
PDF_DIR = SCRIPT_DIR / "docs" / "patterns"
GENERATE_SCRIPT = SCRIPT_DIR / "generate_site.py"
IMAGES_DIR = SCRIPT_DIR / "docs" / "images"

# 尝试导入 Ravelry 抓取模块
try:
    from ravelry_scraper import fetch_ravelry_pattern, map_to_csv_fields
    HAS_RAVELRY = True
except ImportError:
    HAS_RAVELRY = False

# ─── 分类体系 ───
CATEGORIES = ["棒针", "钩针"]
TYPES = ["毛衫", "开衫", "背心", "围巾", "帽子", "袜子", "手套", "披肩", "毯子", "玩偶", "其他"]
LANGUAGES = ["中", "日", "英"]
DIFFICULTIES = ["初级", "中级", "高级"]

FIELDNAMES = ["filename", "title", "category", "type", "language", "difficulty", "notes", "image", "url"]
HEADERS = ["文件", "名称", "分类", "类型", "语言", "难度", "备注", "图片", "网址"]
# 网站卡片上显示的列（与 generate_site.py 保持一致）
VISIBLE_COLUMNS = ["filename", "title", "category", "type", "notes", "image", "url"]
# 语言和难度在后台保留，表格中隐藏（网站也已移除这两个筛选项）
HIDDEN_COLUMNS = ["language", "difficulty"]

# ─── 配色（暖棕色系，细节更精致可爱）───
COLOR_BG = "#faf6f0"
COLOR_CARD = "#ffffff"
COLOR_PRIMARY = "#b85c5c"
COLOR_PRIMARY_DARK = "#8b3a3a"
COLOR_PRIMARY_LIGHT = "#f5e3e0"   # 浅粉棕，用于标签底色 / 选中态柔和背景
COLOR_TEXT = "#3a3027"
COLOR_TEXT_LIGHT = "#8a7a6a"
COLOR_BORDER = "#e5ddd3"
COLOR_KNIT = "#a04545"     # 棒针标签色
COLOR_KNIT_BG = "#f7e6e6"
COLOR_CROCHET = "#4f6fa0"  # 钩针标签色
COLOR_CROCHET_BG = "#e7edf6"
COLOR_SUCCESS = "#5a9c6e"  # 已生成网页 标记色
COLOR_SUCCESS_BG = "#e5f3e8"
FONT_FAMILY = '"Microsoft YaHei", "微软雅黑", "PingFang SC", "Segoe UI", sans-serif'

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
        QDialog, QFormLayout, QComboBox, QTextEdit, QFileDialog, QMessageBox,
        QHeaderView, QAbstractItemView, QCheckBox, QFrame, QTabWidget,
        QListWidget, QListWidgetItem, QSplitter, QScrollArea, QStyledItemDelegate,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
    from PyQt6.QtGui import QColor, QFont, QIcon, QFontDatabase
except ImportError:
    print("缺少 PyQt6 依赖，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
        QDialog, QFormLayout, QComboBox, QTextEdit, QFileDialog, QMessageBox,
        QHeaderView, QAbstractItemView, QCheckBox, QFrame, QTabWidget,
        QListWidget, QListWidgetItem, QSplitter, QScrollArea, QStyledItemDelegate,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
    from PyQt6.QtGui import QColor, QFont, QIcon, QFontDatabase


# ═══════════════════════════════════════════
#  数据读写
# ═══════════════════════════════════════════

def load_patterns():
    """读取 CSV，返回图纸列表"""
    patterns = []
    if not CSV_PATH.exists():
        return patterns
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("filename"):
                continue
            patterns.append({k: row.get(k, "").strip() for k in FIELDNAMES})
    return patterns


def save_patterns(patterns):
    """保存图纸列表到 CSV"""
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for p in patterns:
            writer.writerow({k: p.get(k, "") for k in FIELDNAMES})


def read_pdf_title(pdf_path):
    """从 PDF 元数据读取标题"""
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


# ═══════════════════════════════════════════
#  添加/编辑对话框
# ═══════════════════════════════════════════

class PatternDialog(QDialog):
    """添加 / 编辑图纸的对话框"""

    def __init__(self, parent=None, pattern=None, existing_files=None, pdf_path=None):
        super().__init__(parent)
        self.existing_files = existing_files or set()
        self.result_data = None
        self.selected_pdf_path = None

        is_edit = pattern is not None
        self.setWindowTitle("编辑图纸" if is_edit else "添加图纸")
        self.setMinimumWidth(540)
        self.downloaded_image = pattern.get("image", "") if is_edit and pattern else ""
        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 12, 24, 12)
        # 整体左对齐，保证内部行从左侧开始布局
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # ═══════════════════════════════
        #  步骤 1：选择 PDF
        # ═══════════════════════════════
        step1_label = QLabel("① 选择 PDF 文件")
        step1_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY}; margin-top: 6px;")
        layout.addWidget(step1_label)

        file_row = QHBoxLayout()
        file_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.file_label = QLabel(pattern["filename"] if is_edit else "未选择文件")
        self.file_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT}; font-size: 13px; padding: 6px; border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD};")
        # 固定显示宽度，避免随窗口伸缩
        self.file_label.setFixedWidth(420)
        # 左上对齐文本，基准于第一行
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        btn_browse = QPushButton("选择 PDF" if not is_edit else "更换文件")
        btn_browse.setFixedWidth(100)
        btn_browse.setStyleSheet(self._btn_style(primary=True))
        btn_browse.clicked.connect(self._browse_pdf)
        file_row.addWidget(self.file_label)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # 如果传入了 pdf_path（拖拽上传），预填文件信息
        if not is_edit and pdf_path:
            _pdf_path = Path(pdf_path)
            if _pdf_path.suffix.lower() == ".pdf":
                self.selected_pdf_path = _pdf_path
                self.file_label.setText(_pdf_path.name)
                self.file_label.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 13px; padding: 6px; border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD};")

        # ═══════════════════════════════
        #  步骤 2：粘贴 Ravelry 网址
        # ═══════════════════════════════
        step2_label = QLabel("② 粘贴 Ravelry 网址（可选）")
        step2_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY}; margin-top: 6px;")
        layout.addWidget(step2_label)

        ravelry_row = QHBoxLayout()
        ravelry_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.ravelry_url_input = QLineEdit()
        if is_edit and pattern:
            self.ravelry_url_input.setText(pattern.get("url", ""))
        self.ravelry_url_input.setPlaceholderText("https://www.ravelry.com/patterns/library/...")
        self.ravelry_url_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 2px solid {COLOR_BORDER};
                border-radius: 8px;
                background: {COLOR_CARD};
                color: {COLOR_TEXT};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLOR_PRIMARY}; }}
        """)
        # 固定网址输入宽度，避免拉宽对话框其他元素；文本左对齐
        self.ravelry_url_input.setFixedWidth(420)
        self.ravelry_url_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ravelry_row.addWidget(self.ravelry_url_input)

        self.btn_fetch_ravelry = QPushButton("读取")
        # 固定按钮宽度以显示完整文字且不随布局伸缩
        self.btn_fetch_ravelry.setFixedWidth(100)
        self.btn_fetch_ravelry.setStyleSheet(self._btn_style(primary=True))
        self.btn_fetch_ravelry.clicked.connect(self._fetch_ravelry)
        ravelry_row.addWidget(self.btn_fetch_ravelry)

        # 清除按钮（位于读取按钮右侧），确保文字不被截断
        self.btn_clear_url = QPushButton("清除")
        self.btn_clear_url.setFixedWidth(100)
        self.btn_clear_url.setStyleSheet(self._btn_style(primary=False))
        self.btn_clear_url.clicked.connect(self._clear_ravelry_url)
        ravelry_row.addWidget(self.btn_clear_url)

        self.ravelry_status = QLabel("自动读取")
        self.ravelry_status.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_LIGHT};")
        self.ravelry_status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        ravelry_row.addWidget(self.ravelry_status)
        layout.addLayout(ravelry_row)

        # 网址输入框失焦时自动触发读取
        self.ravelry_url_input.editingFinished.connect(self._auto_fetch_on_blur)
        # 回车也触发
        self.ravelry_url_input.returnPressed.connect(self._fetch_ravelry)
        # 记录上次的 URL，避免重复读取
        self._last_fetched_url = pattern.get("url", "") if is_edit and pattern else ""

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {COLOR_BORDER}; margin: 4px 0;")
        layout.addWidget(sep)

        # ═══════════════════════════════
        #  封面图片
        # ═══════════════════════════════
        image_label_title = QLabel("封面图片（可选）")
        image_label_title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY}; margin-top: 6px;")
        layout.addWidget(image_label_title)

        image_row = QHBoxLayout()
        image_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.image_label = QLabel("未选择图片")
        if is_edit and pattern.get("image"):
            self.image_label.setText(pattern["image"])
        self.image_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT}; font-size: 13px; padding: 6px; border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD};")
        # 固定图片标签宽度，左上对齐文本
        self.image_label.setFixedWidth(420)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        btn_browse_image = QPushButton("选择图片")
        btn_browse_image.setFixedWidth(100)
        btn_browse_image.setStyleSheet(self._btn_style(primary=True))
        btn_browse_image.clicked.connect(self._upload_image)
        self.btn_clear_image = QPushButton("清除")
        self.btn_clear_image.setFixedWidth(100)
        self.btn_clear_image.setStyleSheet(self._btn_style(primary=False))
        self.btn_clear_image.clicked.connect(self._clear_image)
        image_row.addWidget(self.image_label)
        image_row.addWidget(btn_browse_image)
        image_row.addWidget(self.btn_clear_image)
        layout.addLayout(image_row)

        # 小分隔线
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {COLOR_BORDER}; margin: 4px 0;")
        layout.addWidget(sep2)

        # ═══════════════════════════════
        #  步骤 3：手动修改关键字信息
        # ═══════════════════════════════
        step3_label = QLabel("③ 确认/修改图纸信息")
        step3_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY}; margin-top: 6px;")
        layout.addWidget(step3_label)

        form = QVBoxLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.title_input = QLineEdit(pattern["title"] if is_edit else "")
        self.title_input.setPlaceholderText("图纸名称…")
        self.title_input.setFixedWidth(420)
        self.title_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_row.addWidget(self.title_input)
        title_row.addStretch()
        form.addLayout(title_row)

        # 分类 + 类型 行
        category_row = QHBoxLayout()
        category_row.setContentsMargins(0, 0, 0, 0)
        category_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.category_input = QLineEdit(pattern["category"] if is_edit else "")
        self.category_input.setPlaceholderText("分类")
        self.category_input.setFixedWidth(205)
        self.category_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        category_row.addWidget(self.category_input)
        self.type_input = QLineEdit(pattern["type"] if is_edit else "")
        self.type_input.setPlaceholderText("类型")
        self.type_input.setFixedWidth(205)
        self.type_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        category_row.addWidget(self.type_input)
        category_row.addStretch()
        form.addLayout(category_row)

        # 语言 + 难度（后台保存，界面不显示，与网站一致）
        self.language_combo = QComboBox()
        self.language_combo.addItem("", "")
        for l in LANGUAGES:
            self.language_combo.addItem(l, l)
        if is_edit and pattern["language"]:
            idx = LANGUAGES.index(pattern["language"]) + 1 if pattern["language"] in LANGUAGES else 0
            self.language_combo.setCurrentIndex(idx)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItem("", "")
        for d in DIFFICULTIES:
            self.difficulty_combo.addItem(d, d)
        if is_edit and pattern["difficulty"]:
            idx = DIFFICULTIES.index(pattern["difficulty"]) + 1 if pattern["difficulty"] in DIFFICULTIES else 0
            self.difficulty_combo.setCurrentIndex(idx)

        # 备注行
        note_row = QHBoxLayout()
        note_row.setContentsMargins(0, 0, 0, 0)
        note_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.notes_input = QTextEdit(pattern["notes"] if is_edit else "")
        self.notes_input.setPlaceholderText("作者、线材、密度、针码、用量、尺码…")
        self.notes_input.setFixedHeight(160)
        self.notes_input.setFixedWidth(420)
        self.notes_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        try:
            self.notes_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        except Exception:
            pass
        note_row.addWidget(self.notes_input)
        note_row.addStretch()
        form.addLayout(note_row)

        layout.addLayout(form)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_ok = QPushButton("✓ 保存" if is_edit else "✓ 添加")
        btn_ok.setFixedWidth(100)
        btn_ok.setStyleSheet(self._btn_style(primary=True))
        btn_ok.clicked.connect(self._on_save)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.setStyleSheet(self._btn_style(primary=False))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _browse_pdf(self):
        """选择 PDF 文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", str(PDF_DIR), "PDF 文件 (*.pdf)"
        )
        if not path:
            return

        src = Path(path)
        self.selected_pdf_path = src
        self.file_label.setText(src.name)
        self.file_label.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 13px;")

        # 如果标题为空，尝试自动填充
        if not self.title_input.text().strip():
            pdf_title = read_pdf_title(src)
            if pdf_title:
                self.title_input.setText(pdf_title)
            else:
                # 用文件名（去扩展名）作为标题
                self.title_input.setText(src.stem.replace("_", " ").replace("-", " "))

    def _auto_fetch_on_blur(self):
        """网址输入框失焦时，如果有新网址则自动读取"""
        url = self.ravelry_url_input.text().strip()
        if url and url != self._last_fetched_url and "ravelry.com" in url:
            # 先从 URL 提取名称填入标题
            self._guess_title_from_url(url)
            self._fetch_ravelry()

    def _clear_ravelry_url(self):
        """清除 Ravelry URL 输入和状态提示"""
        self.ravelry_url_input.clear()
        self._last_fetched_url = ""
        self.ravelry_status.setText("粘贴后自动读取")
        self.ravelry_status.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_LIGHT};")

    def _guess_title_from_url(self, url):
        """从 Ravelry URL 的最后一段提取图纸名称"""
        import re
        # 匹配 /patterns/library/xxx 或 /patterns/xxx 格式
        m = re.search(r"/patterns(?:/library)?/([^/]+)/?$", url)
        if m:
            name = m.group(1)
            # 将连字符和下划线替换为空格，首字母大写
            name = re.sub(r"[-_]+", " ", name).strip()
            name = " ".join(w.capitalize() for w in name.split())
            if name and not self.title_input.text().strip():
                self.title_input.setText(name)

    def _fetch_ravelry(self):
        """异步抓取 Ravelry 数据"""
        self._last_fetched_url = self.ravelry_url_input.text().strip()
        url = self.ravelry_url_input.text().strip()
        if not url:
            self.ravelry_status.setText("请先粘贴 Ravelry 链接")
            return
        if "ravelry.com" not in url:
            self.ravelry_status.setText("⚠️ 不是有效的 Ravelry 链接")
            return

        self.btn_fetch_ravelry.setEnabled(False)
        self.ravelry_status.setText("正在获取…")
        self.ravelry_status.setStyleSheet("font-size: 12px; color: #b85c5c;")

        self.fetch_thread = RavelryFetchThread(url)
        self.fetch_thread.finished_signal.connect(self._apply_ravelry_data)
        self.fetch_thread.start()

    def _apply_ravelry_data(self, scraped):
        """Ravelry 数据获取完成，自动填充表单 + 下载图片"""
        self.btn_fetch_ravelry.setEnabled(True)

        if not scraped or (scraped.get("_error") and not scraped.get("title")):
            error = scraped.get("_error", "未知错误") if scraped else "无返回数据"
            self.ravelry_status.setText(f"❌ 获取失败: {error}")
            self.ravelry_status.setStyleSheet("font-size: 12px; color: #c0392b;")
            return

        # 下载示例图片
        self.downloaded_image = ""
        image_url = scraped.get("image_url", "")
        if image_url:
            from ravelry_scraper import download_image as dl_image
            image_name = scraped.get("title", "pattern").replace(" ", "_")
            self.downloaded_image = dl_image(image_url, IMAGES_DIR, image_name)
            if self.downloaded_image:
                self.ravelry_status.setText("✅ 图片已下载")
                self.ravelry_status.setStyleSheet("font-size: 12px; color: #27ae60;")

        csv_fields = map_to_csv_fields(scraped)
        if not csv_fields:
            self.ravelry_status.setText("❌ 无法解析数据")
            self.ravelry_status.setStyleSheet("font-size: 12px; color: #c0392b;")
            return

        # 自动填充（不覆盖用户已填的内容）
        if scraped.get("title") and not self.title_input.text().strip():
            self.title_input.setText(scraped["title"])

        cat = csv_fields.get("category", "")
        if cat and not self.category_input.text().strip():
            self.category_input.setText(cat)

        ptype = csv_fields.get("type", "")
        if ptype and not self.type_input.text().strip():
            self.type_input.setText(ptype)

        lang = csv_fields.get("language", "")
        if lang and self.language_combo.currentData() == "":
            found = False
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == lang:
                    self.language_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found and lang:
                self.language_combo.addItem(lang, lang)
                self.language_combo.setCurrentIndex(self.language_combo.count() - 1)

        diff = csv_fields.get("difficulty", "")
        if diff and self.difficulty_combo.currentData() == "":
            found = False
            for i in range(self.difficulty_combo.count()):
                if self.difficulty_combo.itemData(i) == diff:
                    self.difficulty_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found and diff:
                self.difficulty_combo.addItem(diff, diff)
                self.difficulty_combo.setCurrentIndex(self.difficulty_combo.count() - 1)

        notes = csv_fields.get("notes", "")
        if notes and not self.notes_input.toPlainText().strip():
            self.notes_input.setPlainText(notes)

        self.ravelry_status.setText("✅ 信息已填充" + (" + 图片已下载" if self.downloaded_image else ""))
        self.ravelry_status.setStyleSheet("font-size: 12px; color: #27ae60;")

    def _on_save(self):
        """保存按钮回调"""
        filename = self.file_label.text().strip()
        if filename == "未选择文件" or not filename:
            QMessageBox.warning(self, "提示", "请先选择 PDF 文件")
            return

        title = self.title_input.text().strip()
        if not title:
            title = Path(filename).stem

        # 检查文件名是否重复
        if filename in self.existing_files and self.selected_pdf_path:
            reply = QMessageBox.question(
                self, "文件名重复",
                f"文件名 '{filename}' 已存在，是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.result_data = {
            "filename": filename,
            "title": title,
            "category": self.category_input.text().strip(),
            "type": self.type_input.text().strip(),
            "language": self.language_combo.currentData(),
            "difficulty": self.difficulty_combo.currentData(),
            "notes": self.notes_input.toPlainText().strip(),
            "image": self.selected_image_filename if hasattr(self, "selected_image_filename") and self.selected_image_filename else (self.downloaded_image if hasattr(self, "downloaded_image") else ""),
            "url": self.ravelry_url_input.text().strip() if hasattr(self, "ravelry_url_input") else "",
        }
        self.accept()

    def _upload_image(self):
        """上传自定义封面图片"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择封面图片", str(IMAGES_DIR),
            "图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        )
        if not path:
            return
        src = Path(path)
        IMAGES_DIR.mkdir(exist_ok=True)
        dst = IMAGES_DIR / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(str(src), str(dst))
        self.selected_image_filename = src.name
        self.image_label.setText(src.name)
        self.image_label.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 13px; padding: 6px; border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD};")

    def _clear_image(self):
        """清除已选择的封面图片"""
        self.selected_image_filename = ""
        self.image_label.setText("未选择图片")
        self.image_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT}; font-size: 13px; padding: 6px; border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD};")

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLOR_BG};
                font-family: {FONT_FAMILY};
            }}
            QLabel {{
                color: {COLOR_TEXT};
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QLineEdit, QComboBox, QTextEdit {{
                padding: 6px 10px;
                border: 2px solid {COLOR_BORDER};
                border-radius: 8px;
                background: {COLOR_CARD};
                color: {COLOR_TEXT};
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QComboBox QLineEdit {{
                padding: 6px 10px;
                border: none;
                border-radius: 0;
                background: transparent;
                color: {COLOR_TEXT};
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

    @staticmethod
    def _btn_style(primary=True):
        if primary:
            return f"""
                QPushButton {{
                    background: {COLOR_PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 11px;
                    padding: 9px 18px;
                    font-size: 14px;
                    font-weight: bold;
                    font-family: {FONT_FAMILY};
                }}
                QPushButton:hover {{
                    background: {COLOR_PRIMARY_DARK};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background: {COLOR_CARD};
                    color: {COLOR_TEXT};
                    border: 2px solid {COLOR_BORDER};
                    border-radius: 11px;
                    padding: 9px 18px;
                    font-size: 14px;
                    font-family: {FONT_FAMILY};
                }}
                QPushButton:hover {{
                    border-color: {COLOR_PRIMARY};
                    color: {COLOR_PRIMARY};
                    background: {COLOR_PRIMARY_LIGHT};
                }}
            """


# ═══════════════════════════════════════════
#  后台任务线程
# ═══════════════════════════════════════════

class CommandThread(QThread):
    """在后台运行命令，避免界面卡死"""
    output = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, cmd, cwd=None):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd or str(SCRIPT_DIR)

    def run(self):
        try:
            self.output.emit(f"$ {' '.join(self.cmd)}\n")
            proc = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in proc.stdout:
                self.output.emit(line)
            proc.wait()
            if proc.returncode == 0:
                self.finished_signal.emit(True, "完成")
            else:
                self.finished_signal.emit(False, f"退出码: {proc.returncode}")
        except FileNotFoundError:
            self.finished_signal.emit(False, "命令未找到，请检查是否已安装")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


# ═══════════════════════════════════════════
#  Ravelry 异步抓取线程
# ═══════════════════════════════════════════

class RavelryFetchThread(QThread):
    """后台抓取 Ravelry 数据，避免界面卡死"""
    finished_signal = pyqtSignal(object)  # emits dict or None

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        if not HAS_RAVELRY:
            self.finished_signal.emit({"_error": "缺少 ravelry_scraper 模块"})
            return
        try:
            data = fetch_ravelry_pattern(self.url)
            self.finished_signal.emit(data)
        except Exception as e:
            self.finished_signal.emit({"_error": str(e)})




# ═══════════════════════════════════════════
#  瀑布流布局（FlowLayout）
# ═══════════════════════════════════════════

from PyQt6.QtWidgets import QLayout, QSizePolicy
from PyQt6.QtCore import QRect, QPoint


class FlowLayout(QLayout):
    """让子控件像瀑布流一样自动换行排列的布局"""

    def __init__(self, parent=None, margin=0, h_spacing=16, v_spacing=16):
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x, y = effective_rect.x(), effective_rect.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible():
                continue
            item_w = item.sizeHint().width()
            item_h = item.sizeHint().height()
            next_x = x + item_w + self._h_spacing
            if next_x - self._h_spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + self._v_spacing
                next_x = x + item_w + self._h_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item_h)

        return y + line_height - rect.y() + bottom


# ═══════════════════════════════════════════
#  图纸卡片（瀑布流网格中的单个卡片）
# ═══════════════════════════════════════════

from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QCursor

CARD_WIDTH = 220
COVER_HEIGHT = 160
CARD_HEIGHT = 330


def _rounded_pixmap(src_pixmap, target_size, radius):
    """把图片裁剪缩放为圆角矩形（顶部圆角），用于卡片封面"""
    w, h = target_size
    scaled = src_pixmap.scaled(
        w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    # 居中裁剪
    x_off = max(0, (scaled.width() - w) // 2)
    y_off = max(0, (scaled.height() - h) // 2)
    cropped = scaled.copy(x_off, y_off, w, h)

    result = QPixmap(w, h)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


class PatternCard(QFrame):
    """图纸卡片：封面图 + 标题 + 分类标签 + 备注预览，悬浮时浮现编辑/删除按钮"""

    def __init__(self, pattern, is_generated=False, parent=None):
        super().__init__(parent)
        self.pattern = pattern
        self.on_edit = None
        self.on_delete = None
        self.on_select = None
        self.setFixedWidth(CARD_WIDTH)
        # 统一卡片高度，确保网格中卡片尺寸一致并能显示全部信息
        self.setFixedHeight(CARD_HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._selected = False

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(14)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(QColor(184, 92, 92, 40))
        self.setGraphicsEffect(self._shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── 封面 ──
        self.cover = QLabel()
        self.cover.setFixedSize(CARD_WIDTH, COVER_HEIGHT)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_cover(pattern.get("image", ""))
        outer.addWidget(self.cover)

        # ── 信息区 ──
        info = QVBoxLayout()
        info.setContentsMargins(12, 10, 12, 12)
        info.setSpacing(6)

        title = pattern.get("title", "") or "（未命名）"
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        # 增加标题可用高度，避免长标题被截断
        self.title_label.setMaximumHeight(60)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.title_label.setToolTip(title)
        self.title_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLOR_TEXT}; "
            f"font-family: {FONT_FAMILY}; background: transparent;"
        )
        info.addWidget(self.title_label)

        # 分类 + 类型 标签行
        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        cat = pattern.get("category", "")
        ptype = pattern.get("type", "")
        if cat:
            tag_row.addWidget(self._make_tag(cat, is_knit=(cat == "棒针")))
        if ptype:
            tag_row.addWidget(self._make_tag(ptype, is_knit=None))
        tag_row.addStretch()
        info.addLayout(tag_row)

        notes = pattern.get("notes", "").strip()
        if notes:
            notes_label = QLabel(notes)
            notes_label.setWordWrap(True)
            # 允许备注显示多行，给出更大的最大高度以显示更多信息
            notes_label.setMaximumHeight(120)
            notes_label.setStyleSheet(
                f"font-size: 11px; color: {COLOR_TEXT_LIGHT}; "
                f"font-family: {FONT_FAMILY}; background: transparent;"
                f"padding-top: 4px;"
            )
            notes_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            info.addWidget(notes_label)

        # 在信息区底部加入弹性间隔，保证标签/标题等内容靠上显示
        info.addStretch()

        outer.addLayout(info)

        # ── 已生成 徽标 ──
        self._badge = None
        if is_generated:
            self._badge = QLabel("● 已上线", self)
            self._badge.setStyleSheet(
                f"background: {COLOR_SUCCESS_BG}; color: {COLOR_SUCCESS}; "
                f"font-size: 10px; font-weight: bold; padding: 3px 8px; "
                f"border-radius: 8px; font-family: {FONT_FAMILY};"
            )
            self._badge.adjustSize()
            self._badge.move(10, 10)
            self._badge.show()

        # ── 悬浮操作按钮（编辑/删除）──
        self.btn_edit = QPushButton("✏️", self)
        self.btn_delete = QPushButton("🗑️", self)
        for b in (self.btn_edit, self.btn_delete):
            b.setFixedSize(28, 28)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.92);
                    border: none;
                    border-radius: 14px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {COLOR_PRIMARY};
                }}
            """)
            b.hide()
        self.btn_edit.move(CARD_WIDTH - 66, 10)
        self.btn_delete.move(CARD_WIDTH - 34, 10)
        self.btn_edit.clicked.connect(lambda: self.on_edit and self.on_edit(self.pattern))
        self.btn_delete.clicked.connect(lambda: self.on_delete and self.on_delete(self.pattern))

        self._apply_frame_style()

    def set_generated(self, is_generated):
        """Update the generated badge without destroying the card"""
        if is_generated and self._badge is None:
            self._badge = QLabel("\u25cf \u5df2\u4e0a\u7ebf", self)
            self._badge.setStyleSheet(
                f"background: {COLOR_SUCCESS_BG}; color: {COLOR_SUCCESS}; "
                f"font-size: 10px; font-weight: bold; padding: 3px 8px; "
                f"border-radius: 8px; font-family: {FONT_FAMILY};"
            )
            self._badge.adjustSize()
            self._badge.move(10, 10)
            self._badge.show()
        elif not is_generated and self._badge is not None:
            self._badge.hide()
            self._badge.deleteLater()
            self._badge = None

    def set_generated(self, is_generated):
        """Update the generated badge without destroying the card"""
        if is_generated and self._badge is None:
            self._badge = QLabel("\u25cf \u5df2\u4e0a\u7ebf", self)
            self._badge.setStyleSheet(
                f"background: {COLOR_SUCCESS_BG}; color: {COLOR_SUCCESS}; "
                f"font-size: 10px; font-weight: bold; padding: 3px 8px; "
                f"border-radius: 8px; font-family: {FONT_FAMILY};"
            )
            self._badge.adjustSize()
            self._badge.move(10, 10)
            self._badge.show()
        elif not is_generated and self._badge is not None:
            self._badge.hide()
            self._badge.deleteLater()
            self._badge = None

    def _make_tag(self, text, is_knit):
        lbl = QLabel(text)
        if is_knit is True:
            bg, fg = COLOR_KNIT_BG, COLOR_KNIT
        elif is_knit is False:
            bg, fg = COLOR_CROCHET_BG, COLOR_CROCHET
        else:
            bg, fg = "#f1ece4", COLOR_TEXT_LIGHT
        lbl.setStyleSheet(f"""
            background: {bg}; color: {fg};
            font-size: 11px; font-weight: bold;
            padding: 2px 8px; border-radius: 8px;
            font-family: {FONT_FAMILY};
        """)
        # 固定标签高度，防止在固定卡片高度下纵向拉伸
        lbl.setFixedHeight(24)
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return lbl

    def _set_cover(self, image_rel_path):
        pixmap = None
        if image_rel_path:
            candidates = [SCRIPT_DIR / image_rel_path, IMAGES_DIR / Path(image_rel_path).name]
            for c in candidates:
                if c.exists():
                    pm = QPixmap(str(c))
                    if not pm.isNull():
                        pixmap = pm
                        break
        if pixmap is not None:
            rounded = _rounded_pixmap(pixmap, (CARD_WIDTH, COVER_HEIGHT), 14)
            self.cover.setPixmap(rounded)
            self.cover.setStyleSheet("background: transparent;")
        else:
            self.cover.setText("🧶")
            self.cover.setStyleSheet(f"""
                background: {COLOR_PRIMARY_LIGHT};
                color: {COLOR_PRIMARY};
                font-size: 40px;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            """)

    def _apply_frame_style(self, hover=False):
        border_color = COLOR_PRIMARY if (hover or self._selected) else COLOR_BORDER
        border_width = 2
        self.setStyleSheet(f"""
            PatternCard {{
                background: {COLOR_CARD};
                border: {border_width}px solid {border_color};
                border-radius: 14px;
            }}
        """)

    def set_selected(self, selected):
        self._selected = selected
        self._apply_frame_style()

    def enterEvent(self, event):
        self._apply_frame_style(hover=True)
        self._shadow.setBlurRadius(22)
        self._shadow.setColor(QColor(184, 92, 92, 90))
        self.btn_edit.show()
        self.btn_delete.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_frame_style(hover=False)
        self._shadow.setBlurRadius(14)
        self._shadow.setColor(QColor(184, 92, 92, 40))
        self.btn_edit.hide()
        self.btn_delete.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.on_select:
                self.on_select(self.pattern)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.on_edit:
            self.on_edit(self.pattern)
        super().mouseDoubleClickEvent(event)


# ═══════════════════════════════════════════
#  PDF 文件列表标签页
# ═══════════════════════════════════════════

class PdfFileTab(QWidget):
    """PDF 文件独立标签页 - 显示 docs/patterns/ 内所有 PDF"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部工具栏
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.btn_refresh = QPushButton("🔄 刷新列表")
        self.btn_refresh.setStyleSheet(_btn_style_static(primary=False))
        self.btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(self.btn_refresh)

        self.btn_open_folder = QPushButton("📂 打开文件夹")
        self.btn_open_folder.setStyleSheet(_btn_style_static(primary=False))
        self.btn_open_folder.clicked.connect(self._open_folder)
        top_row.addWidget(self.btn_open_folder)

        self.btn_delete_pdf = QPushButton("🗑️ 删除 PDF")
        self.btn_delete_pdf.setStyleSheet(_btn_style_static(primary=False))
        self.btn_delete_pdf.clicked.connect(self._delete_pdf)
        top_row.addWidget(self.btn_delete_pdf)

        top_row.addStretch()

        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT}; font-size: 13px;")
        top_row.addWidget(self.count_label)

        layout.addLayout(top_row)

        # PDF 列表
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {COLOR_CARD};
                border: 2px solid {COLOR_BORDER};
                border-radius: 10px;
                font-size: 14px;
                color: {COLOR_TEXT};
                font-family: {FONT_FAMILY};
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {COLOR_BORDER};
            }}
            QListWidget::item:selected {{
                background: {COLOR_PRIMARY};
                color: white;
                border-radius: 6px;
            }}
            QListWidget::item:alternate {{
                background: {COLOR_BG};
            }}
            QListWidget::item:hover {{
                background: #f5ece8;
                color: {COLOR_TEXT};
            }}
            QListWidget::item:selected:hover {{
                background: {COLOR_PRIMARY_DARK};
                color: white;
            }}
        """)
        layout.addWidget(self.list_widget)

        # 底部提示
        hint = QLabel("💡 双击可在系统默认程序中打开 PDF")
        hint.setStyleSheet(f"color: {COLOR_TEXT_LIGHT}; font-size: 12px; padding: 4px 0;")
        layout.addWidget(hint)

        self.list_widget.itemDoubleClicked.connect(self._open_pdf)
        self.refresh()

    def refresh(self):
        """刷新 PDF 文件列表"""
        self.list_widget.clear()
        if not PDF_DIR.exists():
            self.count_label.setText("文件夹不存在")
            return

        pdfs = sorted(PDF_DIR.glob("*.pdf"), key=lambda p: p.name.lower())
        for pdf in pdfs:
            size_kb = pdf.stat().st_size // 1024
            size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            item = QListWidgetItem(f"📄  {pdf.name}   （{size_str}）")
            item.setData(Qt.ItemDataRole.UserRole, str(pdf))
            self.list_widget.addItem(item)

        count = len(pdfs)
        self.count_label.setText(f"共 {count} 个 PDF 文件")

    def _open_folder(self):
        """在文件资源管理器中打开 patterns/ 文件夹"""
        PDF_DIR.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(str(PDF_DIR))
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(PDF_DIR)])

    def _open_pdf(self, item):
        """双击打开 PDF"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])

    def _delete_pdf(self):
        """删除选中的 PDF 文件（含联动删除图纸记录）"""
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.information(self, "提示", "请先在列表中选择一个 PDF 文件")
            return

        pdf_path = Path(item.data(Qt.ItemDataRole.UserRole))
        filename = pdf_path.name

        # 检查是否已录入 patterns.csv
        all_patterns = load_patterns()
        matched = [p for p in all_patterns if p.get("filename") == filename]
        has_csv_entry = len(matched) > 0

        # 构建确认信息
        msg = f"确定要删除 \"{filename}\" 吗？\n\n该操作会删除 PDF 文件本身。"
        if has_csv_entry:
            msg += f"\n\n此图纸已在 patterns.csv 中录入，将同步删除图纸记录。"

        reply = QMessageBox.question(
            self, "确认删除", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # 删除 PDF 文件
            if pdf_path.exists():
                pdf_path.unlink()

            # 联动删除 patterns.csv 中的记录
            if has_csv_entry:
                all_patterns = [p for p in all_patterns if p.get("filename") != filename]
                save_patterns(all_patterns)
                # 刷新主窗口的卡片列表
                if self.window() and hasattr(self.window(), "_reload_table"):
                    self.window()._reload_table()

            self.refresh()
            if self.window() and hasattr(self.window(), "status_label"):
                if has_csv_entry:
                    self.window().status_label.setText(f"✅ 已删除 PDF 及图纸记录: {filename}")
                else:
                    self.window().status_label.setText(f"✅ 已删除: {filename}")
        except Exception as e:
            QMessageBox.warning(self, "删除失败", f"无法删除文件:\n{e}")

def _btn_style_static(primary=True):
    if primary:
        return f"""
            QPushButton {{
                background: {COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: 11px;
                padding: 9px 18px;
                font-size: 14px;
                font-weight: bold;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: {COLOR_PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background: {COLOR_PRIMARY_DARK};
                padding-top: 10px;
            }}
            QPushButton:disabled {{
                background: #ccc;
                color: #999;
            }}
        """
    else:
        return f"""
            QPushButton {{
                background: {COLOR_CARD};
                color: {COLOR_TEXT};
                border: 2px solid {COLOR_BORDER};
                border-radius: 11px;
                padding: 9px 18px;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{
                border-color: {COLOR_PRIMARY};
                color: {COLOR_PRIMARY};
                background: {COLOR_PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                background: {COLOR_PRIMARY_LIGHT};
                padding-top: 10px;
            }}
            QPushButton:disabled {{
                background: #eee;
                color: #aaa;
            }}
        """


# ═══════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════

class PatternManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧶 编织图纸管理器")
        self.setMinimumSize(960, 640)
        self.resize(1100, 700)
        self.patterns = []
        self.cmd_thread = None

        self._apply_style()
        self._build_ui()
        self._reload_table()
        self.setAcceptDrops(True)

    # ─── UI 构建 ───

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # 顶部标题
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        header = QLabel("🧶 编织图纸管理器")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLOR_PRIMARY}; font-family: {FONT_FAMILY};")
        header_box.addWidget(header)
        subtitle = QLabel("把心爱的图纸都好好收藏起来吧 ✨")
        subtitle.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_LIGHT}; font-family: {FONT_FAMILY};")
        header_box.addWidget(subtitle)
        main_layout.addLayout(header_box)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_add = QPushButton("➕ 添加 PDF")
        self.btn_add.setStyleSheet(self._btn_style(primary=True))
        self.btn_add.clicked.connect(self._add_pattern)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ 编辑")
        self.btn_edit.setStyleSheet(self._btn_style(primary=False))
        self.btn_edit.clicked.connect(self._edit_pattern)
        toolbar.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("🗑️ 删除")
        self.btn_delete.setStyleSheet(self._btn_style(primary=False))
        self.btn_delete.clicked.connect(self._delete_pattern)
        toolbar.addWidget(self.btn_delete)

        toolbar.addSpacing(20)

        self.btn_scan = QPushButton("🔍 扫描文件夹")
        self.btn_scan.setStyleSheet(self._btn_style(primary=False))
        self.btn_scan.clicked.connect(self._scan_folder)
        toolbar.addWidget(self.btn_scan)

        toolbar.addStretch()

        self.btn_generate = QPushButton("🌐 生成网页")
        self.btn_generate.setStyleSheet(self._btn_style(primary=False))
        self.btn_generate.clicked.connect(self._generate_site)
        toolbar.addWidget(self.btn_generate)

        self.btn_push = QPushButton("🚀 推送 GitHub")
        self.btn_push.setStyleSheet(self._btn_style(primary=False))
        self.btn_push.clicked.connect(self._push_github)
        toolbar.addWidget(self.btn_push)

        main_layout.addLayout(toolbar)

        # ─── Tab 区域 ───
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {COLOR_BORDER};
                border-radius: 10px;
                background: {COLOR_BG};
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background: {COLOR_CARD};
                color: {COLOR_TEXT_LIGHT};
                border: 2px solid {COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 20px;
                margin-right: 4px;
                font-size: 14px;
                font-weight: bold;
                font-family: {FONT_FAMILY};
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background: {COLOR_PRIMARY};
                color: white;
                border-color: {COLOR_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background: #f0e8e8;
                color: {COLOR_PRIMARY};
            }}
        """)

        # ── Tab 1: 图纸管理（搜索 + 表格）──
        tab_manage = QWidget()
        tab_manage_layout = QVBoxLayout(tab_manage)
        tab_manage_layout.setContentsMargins(12, 12, 12, 12)
        tab_manage_layout.setSpacing(8)

        # 搜索栏
        search_row = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_LIGHT}; font-family: {FONT_FAMILY};")
        search_row.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入标题、文件名或备注关键词…")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 2px solid {COLOR_BORDER};
                border-radius: 10px;
                background: {COLOR_CARD};
                color: {COLOR_TEXT};
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.search_input.textChanged.connect(self._filter_cards)
        # 固定搜索框宽度，避免影响工具栏布局
        self.search_input.setFixedWidth(520)
        search_row.addWidget(self.search_input)

        self.count_hint_label = QLabel("")
        self.count_hint_label.setStyleSheet(
            f"font-size: 13px; color: {COLOR_TEXT_LIGHT}; font-family: {FONT_FAMILY}; padding-left: 4px;"
        )
        search_row.addWidget(self.count_hint_label)
        tab_manage_layout.addLayout(search_row)

        # 卡片瀑布流网格（用 QScrollArea 包裹一个使用 FlowLayout 的容器）
        self.selected_pattern = None
        self.pattern_cards = []  # 当前显示的 PatternCard 列表

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {COLOR_BG};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_flow_layout = FlowLayout(self.cards_container, margin=6, h_spacing=16, v_spacing=16)
        self.cards_scroll.setWidget(self.cards_container)

        tab_manage_layout.addWidget(self.cards_scroll)
        self.tab_widget.addTab(tab_manage, "📋  图纸管理")

        # ── Tab 2: PDF 文件 ──
        self.pdf_tab = PdfFileTab()
        self.tab_widget.addTab(self.pdf_tab, "📄  PDF 文件")

        # 切换 tab 时刷新 PDF 列表
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tab_widget)

        # 状态栏（放在 tab 外面，底部）
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLOR_TEXT_LIGHT};
            font-family: {FONT_FAMILY};
            background: transparent;
            padding: 4px 2px;
        """)
        main_layout.addWidget(self.status_label)

    def _on_tab_changed(self, index):
        """切换标签页时的回调"""
        if index == 1:  # PDF 文件 tab
            self.pdf_tab.refresh()

    # ─── 数据操作 ───

    def _reload_table(self):
        """重新加载 CSV 数据到卡片网格"""
        self.patterns = load_patterns()
        self.selected_pattern = None
        self._populate_cards(self.patterns)

    def _refresh_card_states(self):
        """Update card generated badges without rebuilding (fixes flash)"""
        generated_files = self._get_generated_filenames()
        for card in self.pattern_cards:
            is_gen = card.pattern.get("filename", "") in generated_files
            card.set_generated(is_gen)
        total = len(self.patterns)
        gen_count = len(generated_files)
        if gen_count > 0:
            self.status_label.setText(
                f"共 {total} 张图纸  |  🟢 已生成网页 {gen_count} 张  |  ⚪ 未生成 {total - gen_count} 张"
            )
        else:
            self.status_label.setText(f"共 {total} 张图纸  |  尚未生成网页")

    def _refresh_card_states(self):
        """Update card generated badges without rebuilding (fixes flash)"""
        generated_files = self._get_generated_filenames()
        for card in self.pattern_cards:
            is_gen = card.pattern.get("filename", "") in generated_files
            card.set_generated(is_gen)
        total = len(self.patterns)
        gen_count = len(generated_files)
        if gen_count > 0:
            self.status_label.setText(
                f"共 {total} 张图纸  |  🟢 已生成网页 {gen_count} 张  |  ⚪ 未生成 {total - gen_count} 张"
            )
        else:
            self.status_label.setText(f"共 {total} 张图纸  |  尚未生成网页")

    def _get_generated_filenames(self):
        """解析 docs/index.html，获取已生成网页中包含的图纸文件名集合"""
        index_path = SCRIPT_DIR / "docs" / "index.html"
        if not index_path.exists():
            return set()

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 提取嵌入的 PATTERNS JSON 数组
            m = re.search(r'const PATTERNS = (\[.*?\]);', content, re.DOTALL)
            if not m:
                return set()
            patterns_data = json.loads(m.group(1))
            return {p.get("filename", "") for p in patterns_data}
        except Exception:
            return set()

    def _clear_cards(self):
        """清空卡片网格中的所有卡片控件"""
        while self.cards_flow_layout.count():
            item = self.cards_flow_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.pattern_cards = []

    def _populate_cards(self, data):
        """用图纸数据重建卡片瀑布流网格"""
        self.cards_container.setUpdatesEnabled(False)
        self.cards_container.setUpdatesEnabled(False)
        generated_files = self._get_generated_filenames()
        self._clear_cards()

        if not data:
            empty_label = QLabel("🧶  还没有图纸，点击上方「添加 PDF」开始收藏吧～")
            empty_label.setStyleSheet(
                f"color: {COLOR_TEXT_LIGHT}; font-size: 14px; font-family: {FONT_FAMILY}; padding: 40px;"
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_flow_layout.addWidget(empty_label)
        else:
            for p in data:
                is_generated = p.get("filename", "") in generated_files
                card = PatternCard(p, is_generated=is_generated)
                card.on_edit = self._edit_pattern_data
                card.on_delete = self._delete_pattern_data
                card.on_select = self._select_card
                if self.selected_pattern and p.get("filename") == self.selected_pattern.get("filename"):
                    card.set_selected(True)
                self.cards_flow_layout.addWidget(card)
                self.pattern_cards.append(card)

        generated_count = len(generated_files)
        total_count = len(self.patterns)
        shown_count = len(data)
        self.count_hint_label.setText(f"（显示 {shown_count} / 共 {total_count} 张）" if shown_count != total_count else "")
        if generated_count > 0:
            self.status_label.setText(
                f"共 {total_count} 张图纸  |  🟢 已生成网页 {generated_count} 张  |  ⚪ 未生成 {total_count - generated_count} 张"
            )
        else:
            self.status_label.setText(f"共 {total_count} 张图纸  |  尚未生成网页")
        self.cards_container.setUpdatesEnabled(True)
        self.cards_container.update()
        self.cards_container.setUpdatesEnabled(True)
        self.cards_container.update()

    def _select_card(self, pattern):
        """点击卡片时选中它（更新高亮状态，供编辑/删除按钮使用）"""
        self.selected_pattern = pattern
        for card in self.pattern_cards:
            card.set_selected(card.pattern.get("filename") == pattern.get("filename"))

    def _filter_cards(self):
        """搜索过滤"""
        q = self.search_input.text().strip().lower()
        if not q:
            self._populate_cards(self.patterns)
            return
        filtered = [
            p for p in self.patterns
            if q in p.get("title", "").lower()
            or q in p.get("filename", "").lower()
            or q in p.get("notes", "").lower()
        ]
        self._populate_cards(filtered)

    def _get_selected_pattern(self):
        """获取当前选中的图纸，返回 None 如果没选"""
        if self.selected_pattern is None:
            QMessageBox.information(self, "提示", "请先点击一张图纸卡片进行选择")
            return None
        return self.selected_pattern

    def _add_pattern(self):
        """添加新图纸"""
        existing_files = {p["filename"] for p in self.patterns}
        dialog = PatternDialog(self, existing_files=existing_files)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            data = dialog.result_data

            # 如果选了新文件，复制到 patterns/
            if dialog.selected_pdf_path:
                src = dialog.selected_pdf_path
                dst = PDF_DIR / data["filename"]
                PDF_DIR.mkdir(exist_ok=True)
                if src.resolve() != dst.resolve():
                    shutil.copy2(str(src), str(dst))

            self.patterns.insert(0, data)
            save_patterns(self.patterns)
            self._reload_table()
            self.status_label.setText(f"✅ 已添加: {data['title']}")

    def _edit_pattern(self):
        """编辑选中的图纸（工具栏「✏️ 编辑」按钮）"""
        pattern = self._get_selected_pattern()
        if pattern is None:
            return
        self._edit_pattern_data(pattern)

    def _edit_pattern_data(self, pattern):
        """编辑指定图纸（卡片双击 / 卡片上的编辑按钮 均走这里）"""
        existing_files = {p["filename"] for p in self.patterns if p["filename"] != pattern["filename"]}
        dialog = PatternDialog(self, pattern=pattern, existing_files=existing_files)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            data = dialog.result_data

            if dialog.selected_pdf_path:
                src = dialog.selected_pdf_path
                dst = PDF_DIR / data["filename"]
                if src.resolve() != dst.resolve():
                    shutil.copy2(str(src), str(dst))

            for i, p in enumerate(self.patterns):
                if p["filename"] == pattern["filename"]:
                    self.patterns[i] = data
                    break

            save_patterns(self.patterns)
            self.selected_pattern = data
            self._populate_cards_from_search()
            self.status_label.setText(f"✅ 已更新: {data['title']}")

    def _delete_pattern(self):
        """删除选中的图纸（工具栏「🗑️ 删除」按钮）"""
        pattern = self._get_selected_pattern()
        if pattern is None:
            return
        self._delete_pattern_data(pattern)

    def _delete_pattern_data(self, pattern):
        """删除指定图纸（卡片上的删除按钮 也走这里）"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 '{pattern['title']}' 吗？\n\n"
            f"（PDF 文件不会被删除，只从清单中移除）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.patterns = [
                p for p in self.patterns
                if p["filename"] != pattern["filename"]
            ]
            if self.selected_pattern and self.selected_pattern.get("filename") == pattern["filename"]:
                self.selected_pattern = None
            save_patterns(self.patterns)
            self._populate_cards_from_search()
            self.status_label.setText(f"✅ 已删除: {pattern['title']}")

    def _populate_cards_from_search(self):
        """按当前搜索关键词重新渲染卡片网格（保留搜索状态，而不是清空搜索）"""
        q = self.search_input.text().strip().lower()
        if not q:
            self._populate_cards(self.patterns)
        else:
            filtered = [
                p for p in self.patterns
                if q in p.get("title", "").lower()
                or q in p.get("filename", "").lower()
                or q in p.get("notes", "").lower()
            ]
            self._populate_cards(filtered)

    def _scan_folder(self):
        """扫描 patterns/ 文件夹，发现未登记的 PDF"""
        if not PDF_DIR.exists():
            QMessageBox.warning(self, "提示", "patterns/ 文件夹不存在")
            return

        existing = {p["filename"] for p in self.patterns}
        new_pdfs = []

        for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
            if pdf_path.name not in existing:
                title = read_pdf_title(pdf_path)
                if not title:
                    title = pdf_path.stem.replace("_", " ").replace("-", " ")
                new_pdfs.append({
                    "filename": pdf_path.name,
                    "title": title,
                    "category": "",
                    "type": "",
                    "language": "",
                    "difficulty": "",
                    "notes": "",
                    "image": "",
                    "url": "",
                })

        if not new_pdfs:
            QMessageBox.information(self, "扫描结果", "没有发现未登记的 PDF，所有文件已在清单中。")
            return

        names = "\n".join(f"  • {p['title']} ({p['filename']})" for p in new_pdfs)
        reply = QMessageBox.question(
            self, f"发现 {len(new_pdfs)} 张未登记的 PDF",
            f"以下 PDF 未在清单中：\n\n{names}\n\n是否全部添加到清单？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.patterns = new_pdfs + self.patterns
            save_patterns(self.patterns)
            self._reload_table()
            self.status_label.setText(f"✅ 已添加 {len(new_pdfs)} 张图纸，请补充分类和类型等信息")

    def _generate_site(self):
        """生成网页"""
        py_exe = sys.executable
        self.cmd_thread = CommandThread([py_exe, str(GENERATE_SCRIPT)])
        self.cmd_thread.output.connect(
            lambda text: self.status_label.setText(text.strip() or self.status_label.text())
        )
        self.cmd_thread.finished_signal.connect(
            lambda ok, msg: self._on_generate_done(ok, msg)
        )
        self.btn_generate.setEnabled(False)
        self.status_label.setText("正在生成网页…")
        self.cmd_thread.start()

    def _push_github(self):
        """推送到 GitHub"""
        py_exe = sys.executable
        self.cmd_thread = CommandThread([py_exe, str(GENERATE_SCRIPT)])
        self.cmd_thread.finished_signal.connect(
            lambda ok, msg: self._do_git_commands() if ok else self._on_generate_done(ok, msg)
        )
        self.btn_push.setEnabled(False)
        self.status_label.setText("正在生成网页并推送到 GitHub…")
        self.cmd_thread.start()

    def _on_generate_done(self, ok, msg):
        """网页生成完成回调：刷新表格以更新生成状态标记"""
        self._refresh_card_states()  # 刷新表格，让已生成的行变绿
        self._on_command_done(ok, msg)

    def _do_git_commands(self):
        """执行 git add, commit, push"""
        git_thread = CommandThread(["git", "add", "-A"])
        git_thread.finished_signal.connect(
            lambda ok, msg: self._git_commit() if ok else self._on_command_done(ok, msg)
        )
        git_thread.output.connect(
            lambda text: self.status_label.setText(text.strip() or self.status_label.text())
        )
        git_thread.start()
        self.cmd_thread = git_thread

    def _git_commit(self):
        """git commit"""
        from datetime import datetime
        msg = f"更新图纸库 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        commit_thread = CommandThread(["git", "commit", "-m", msg])
        self._commit_output = []
        commit_thread.output.connect(
            lambda text: self._commit_output.append(text)
        )
        commit_thread.finished_signal.connect(self._on_commit_done)
        commit_thread.start()
        self.cmd_thread = commit_thread

    def _on_commit_done(self, ok, msg):
        """git commit 完成回调"""
        output_text = "".join(self._commit_output) if hasattr(self, "_commit_output") else ""
        if ok:
            self._git_push()
        elif "nothing to commit" in output_text or "没有要提交的更改" in output_text:
            self.status_label.setText("没有新变更，直接推送…")
            self._git_push()
        else:
            self._on_command_done(ok, msg)

    def _git_push(self):
        """git push"""
        push_thread = CommandThread(["git", "push"])
        push_thread.finished_signal.connect(self._on_command_done)
        push_thread.start()
        self.cmd_thread = push_thread

    def _on_command_done(self, ok, msg):
        """命令执行完成回调"""
        self.btn_generate.setEnabled(True)
        self.btn_push.setEnabled(True)
        if ok:
            self.status_label.setText(f"✅ {msg}")
        else:
            self.status_label.setText(f"❌ 失败: {msg}")
            QMessageBox.warning(self, "操作失败", f"命令执行失败:\n{msg}\n\n如果推送失败，请检查是否已配置 GitHub 远程仓库。")

    # ─── 拖拽上传 ───

    def dragEnterEvent(self, event):
        """拖拽进入事件：判断是否包含 PDF 文件"""
        mime = event.mimeData()
        if mime.hasUrls():
            pdf_urls = [u for u in mime.urls() if u.toLocalFile().lower().endswith(".pdf")]
            if pdf_urls:
                event.acceptProposedAction()
                self._drag_highlight_on()
                self._drag_pdf_count = len(pdf_urls)
                self.status_label.setText(f"📄 释放以添加 {len(pdf_urls)} 个 PDF")
            else:
                event.ignore()
                self.status_label.setText("⚠️ 只支持 PDF 文件")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件：取消高亮"""
        self._drag_highlight_off()
        self.status_label.setText(f"共 {len(self.patterns)} 张图纸")

    def dropEvent(self, event):
        """释放拖拽事件：处理 PDF 文件"""
        self._drag_highlight_off()
        mime = event.mimeData()
        pdf_paths = [Path(u.toLocalFile()) for u in mime.urls() if u.toLocalFile().lower().endswith(".pdf")]

        if not pdf_paths:
            self.status_label.setText("⚠️ 只支持 PDF 文件")
            return

        self.status_label.setText(f"📄 正在添加 {len(pdf_paths)} 个 PDF…")
        added = 0
        for pdf_path in pdf_paths:
            existing_files = {p["filename"] for p in self.patterns}
            dialog = PatternDialog(self, existing_files=existing_files, pdf_path=str(pdf_path))
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
                data = dialog.result_data
                if dialog.selected_pdf_path:
                    src = dialog.selected_pdf_path
                    dst = PDF_DIR / data["filename"]
                    PDF_DIR.mkdir(exist_ok=True)
                    if src.resolve() != dst.resolve():
                        shutil.copy2(str(src), str(dst))
                self.patterns.insert(0, data)
                added += 1

        save_patterns(self.patterns)
        self._reload_table()
        self.status_label.setText(f"✅ 已添加 {added} 张图纸（共 {len(self.patterns)} 张）")

    def _drag_highlight_on(self):
        """拖拽时给卡片网格区域加一个可爱的虚线高亮边框"""
        self.cards_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {COLOR_PRIMARY_LIGHT};
                border: 2px dashed {COLOR_PRIMARY};
                border-radius: 14px;
            }}
            QScrollBar:vertical {{
                background: {COLOR_BG};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    def _drag_highlight_off(self):
        """恢复卡片网格区域的原有样式"""
        self.cards_scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {COLOR_BG};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    # ─── 样式 ───

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {COLOR_BG};
            }}
            QMainWindow > QWidget {{
                background: {COLOR_BG};
            }}
            QWidget {{
                color: {COLOR_TEXT};
                font-family: {FONT_FAMILY};
            }}
            QMessageBox {{
                font-family: {FONT_FAMILY};
            }}
        """)

    @staticmethod
    def _btn_style(primary=True):
        return _btn_style_static(primary)


# ═══════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════

def main():
    # 确保 patterns 文件夹存在
    PDF_DIR.mkdir(exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("编织图纸管理器")

    # 全局设置微软雅黑字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = PatternManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


