#!/usr/bin/env python3
"""
编织图纸管理器 - PyQt6 桌面应用
功能：表格管理图纸、搜索、添加/编辑/删除、扫描未登记 PDF、
      一键生成网页、一键推送 GitHub。
"""

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

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

# ─── 配色（与网页一致）───
COLOR_BG = "#faf6f0"
COLOR_CARD = "#ffffff"
COLOR_PRIMARY = "#b85c5c"
COLOR_PRIMARY_DARK = "#8b3a3a"
COLOR_TEXT = "#3a3027"
COLOR_TEXT_LIGHT = "#8a7a6a"
COLOR_BORDER = "#e5ddd3"

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
        QDialog, QFormLayout, QComboBox, QTextEdit, QFileDialog, QMessageBox,
        QHeaderView, QAbstractItemView, QCheckBox, QFrame,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QIcon
except ImportError:
    print("缺少 PyQt6 依赖，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
        QDialog, QFormLayout, QComboBox, QTextEdit, QFileDialog, QMessageBox,
        QHeaderView, QAbstractItemView, QCheckBox, QFrame,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QIcon


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

    def __init__(self, parent=None, pattern=None, existing_files=None):
        super().__init__(parent)
        self.existing_files = existing_files or set()
        self.result_data = None
        self.selected_pdf_path = None

        is_edit = pattern is not None
        self.setWindowTitle("编辑图纸" if is_edit else "添加图纸")
        self.setMinimumWidth(520)
        self.downloaded_image = pattern.get("image", "") if is_edit and pattern else ""
        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # ═══════════════════════════════
        #  步骤 1：选择 PDF
        # ═══════════════════════════════
        step1_label = QLabel("① 选择 PDF 文件")
        step1_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY};")
        layout.addWidget(step1_label)

        file_row = QHBoxLayout()
        self.file_label = QLabel(pattern["filename"] if is_edit else "未选择文件")
        self.file_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT}; font-size: 13px; padding: 6px; border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD};")
        self.file_label.setMinimumWidth(280)
        btn_browse = QPushButton("📂 选择 PDF" if not is_edit else "📂 更换文件")
        btn_browse.setFixedWidth(120)
        btn_browse.setStyleSheet(self._btn_style(primary=True))
        btn_browse.clicked.connect(self._browse_pdf)
        file_row.addWidget(self.file_label)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # ═══════════════════════════════
        #  步骤 2：粘贴 Ravelry 网址
        # ═══════════════════════════════
        step2_label = QLabel("② 粘贴 Ravelry 网址（可选）")
        step2_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY}; margin-top: 6px;")
        layout.addWidget(step2_label)

        ravelry_row = QHBoxLayout()
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
        ravelry_row.addWidget(self.ravelry_url_input)

        self.btn_fetch_ravelry = QPushButton("🔍 读取")
        self.btn_fetch_ravelry.setFixedWidth(80)
        self.btn_fetch_ravelry.setStyleSheet(self._btn_style(primary=True))
        self.btn_fetch_ravelry.clicked.connect(self._fetch_ravelry)
        ravelry_row.addWidget(self.btn_fetch_ravelry)

        self.ravelry_status = QLabel("粘贴后自动读取")
        self.ravelry_status.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_LIGHT};")
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
        #  步骤 3：手动修改关键字信息
        # ═══════════════════════════════
        step3_label = QLabel("③ 确认/修改图纸信息")
        step3_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_PRIMARY};")
        layout.addWidget(step3_label)

        form = QFormLayout()
        form.setSpacing(10)

        # 标题
        self.title_input = QLineEdit(pattern["title"] if is_edit else "")
        self.title_input.setPlaceholderText("图纸名称…")
        form.addRow("名称:", self.title_input)

        # 分类 + 类型 同行
        cat_type_row = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItem("（分类）", "")
        for c in CATEGORIES:
            self.category_combo.addItem(c, c)
        if is_edit and pattern["category"]:
            idx = CATEGORIES.index(pattern["category"]) + 1 if pattern["category"] in CATEGORIES else 0
            self.category_combo.setCurrentIndex(idx)
        self.category_combo.setMinimumWidth(120)
        cat_type_row.addWidget(self.category_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItem("（类型）", "")
        for t in TYPES:
            self.type_combo.addItem(t, t)
        if is_edit and pattern["type"]:
            idx = TYPES.index(pattern["type"]) + 1 if pattern["type"] in TYPES else 0
            self.type_combo.setCurrentIndex(idx)
        self.type_combo.setMinimumWidth(120)
        cat_type_row.addWidget(self.type_combo)
        cat_type_row.addStretch()
        cat_type_widget = QWidget()
        cat_type_widget.setLayout(cat_type_row)
        form.addRow("属性:", cat_type_widget)

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

        # 备注
        self.notes_input = QTextEdit(pattern["notes"] if is_edit else "")
        self.notes_input.setPlaceholderText("作者、线材、密度、针码、用量、尺码…")
        self.notes_input.setFixedHeight(80)
        form.addRow("备注:", self.notes_input)

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
            self._fetch_ravelry()

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
        if cat and self.category_combo.currentData() == "":
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == cat:
                    self.category_combo.setCurrentIndex(i)
                    break

        ptype = csv_fields.get("type", "")
        if ptype and self.type_combo.currentData() == "":
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == ptype:
                    self.type_combo.setCurrentIndex(i)
                    break

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
            "category": self.category_combo.currentData(),
            "type": self.type_combo.currentData(),
            "language": self.language_combo.currentData(),
            "difficulty": self.difficulty_combo.currentData(),
            "notes": self.notes_input.toPlainText().strip(),
            "image": self.downloaded_image if hasattr(self, "downloaded_image") else "",
            "url": self.ravelry_url_input.text().strip() if hasattr(self, "ravelry_url_input") else "",
        }
        self.accept()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLOR_BG};
            }}
            QLabel {{
                color: {COLOR_TEXT};
                font-size: 14px;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                padding: 6px 10px;
                border: 2px solid {COLOR_BORDER};
                border-radius: 8px;
                background: {COLOR_CARD};
                color: {COLOR_TEXT};
                font-size: 14px;
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
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
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
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    border-color: {COLOR_PRIMARY};
                    color: {COLOR_PRIMARY};
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
#  主窗口
# ═══════════════════════════════════════════

class PatternManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧶 编织图纸管理器")
        self.setMinimumSize(900, 600)
        self.resize(1000, 650)
        self.patterns = []
        self.cmd_thread = None

        self._apply_style()
        self._build_ui()
        self._reload_table()

    # ─── UI 构建 ───

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # 顶部标题
        header = QLabel("🧶 编织图纸管理器")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLOR_PRIMARY};")
        main_layout.addWidget(header)

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

        # 搜索栏
        search_row = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_LIGHT};")
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
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.search_input.textChanged.connect(self._filter_table)
        search_row.addWidget(self.search_input)
        main_layout.addLayout(search_row)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        # 隐藏语言和难度列（与网站保持一致）
        self.table.setColumnHidden(FIELDNAMES.index("language"), True)
        self.table.setColumnHidden(FIELDNAMES.index("difficulty"), True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._edit_pattern)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {COLOR_CARD};
                border: 2px solid {COLOR_BORDER};
                border-radius: 10px;
                gridline-color: {COLOR_BORDER};
                font-size: 14px;
                color: {COLOR_TEXT};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
            }}
            QTableWidget::item:alternate {{
                background: {COLOR_BG};
            }}
            QHeaderView::section {{
                background: {COLOR_PRIMARY};
                color: white;
                padding: 8px 10px;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 8px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 8px;
            }}
        """)

        # 列宽
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 文件名
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 标题
        for i in range(2, len(HEADERS)):
            header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        main_layout.addWidget(self.table)

        # 状态栏
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_LIGHT};")
        main_layout.addWidget(self.status_label)

    # ─── 数据操作 ───

    def _reload_table(self):
        """重新加载 CSV 数据到表格"""
        self.patterns = load_patterns()
        self._populate_table(self.patterns)

    def _populate_table(self, data):
        """填充表格数据"""
        self.table.setRowCount(len(data))
        for i, p in enumerate(data):
            values = [p.get(k, "") for k in FIELDNAMES]
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                # 分类和难度用颜色标记
                if j == 2 and val:  # 分类
                    if val == "棒针":
                        item.setForeground(QColor("#a04545"))
                    elif val == "钩针":
                        item.setForeground(QColor("#4565a0"))
                elif j == 5 and val:  # 难度
                    if val == "初级":
                        item.setForeground(QColor("#2e7d32"))
                    elif val == "中级":
                        item.setForeground(QColor("#e65100"))
                    elif val == "高级":
                        item.setForeground(QColor("#c62828"))
                self.table.setItem(i, j, item)

        self.status_label.setText(f"共 {len(data)} 张图纸")

    def _filter_table(self):
        """搜索过滤"""
        q = self.search_input.text().strip().lower()
        if not q:
            self._populate_table(self.patterns)
            return
        filtered = [
            p for p in self.patterns
            if q in p.get("title", "").lower()
            or q in p.get("filename", "").lower()
            or q in p.get("notes", "").lower()
        ]
        self._populate_table(filtered)

    def _get_selected_index(self):
        """获取当前选中的行索引，返回 None 如果没选"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先在表格中选择一行")
            return None
        return row

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

            self.patterns.append(data)
            save_patterns(self.patterns)
            self._reload_table()
            self.status_label.setText(f"✅ 已添加: {data['title']}")

    def _edit_pattern(self):
        """编辑选中的图纸"""
        row = self._get_selected_index()
        if row is None:
            return

        # 获取当前过滤后的数据
        q = self.search_input.text().strip().lower()
        if q:
            display_list = [
                p for p in self.patterns
                if q in p.get("title", "").lower()
                or q in p.get("filename", "").lower()
                or q in p.get("notes", "").lower()
            ]
        else:
            display_list = self.patterns

        if row >= len(display_list):
            return
        pattern = display_list[row]

        existing_files = {p["filename"] for p in self.patterns if p["filename"] != pattern["filename"]}
        dialog = PatternDialog(self, pattern=pattern, existing_files=existing_files)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            data = dialog.result_data

            # 如果更换了文件
            if dialog.selected_pdf_path:
                src = dialog.selected_pdf_path
                dst = PDF_DIR / data["filename"]
                if src.resolve() != dst.resolve():
                    shutil.copy2(str(src), str(dst))

            # 更新数据
            for i, p in enumerate(self.patterns):
                if p["filename"] == pattern["filename"]:
                    self.patterns[i] = data
                    break

            save_patterns(self.patterns)
            self._reload_table()
            self.status_label.setText(f"✅ 已更新: {data['title']}")

    def _delete_pattern(self):
        """删除选中的图纸"""
        row = self._get_selected_index()
        if row is None:
            return

        # 获取当前显示的数据
        q = self.search_input.text().strip().lower()
        if q:
            display_list = [
                p for p in self.patterns
                if q in p.get("title", "").lower()
                or q in p.get("filename", "").lower()
                or q in p.get("notes", "").lower()
            ]
        else:
            display_list = self.patterns

        if row >= len(display_list):
            return
        pattern = display_list[row]

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
            save_patterns(self.patterns)
            self._reload_table()
            self.status_label.setText(f"✅ 已删除: {pattern['title']}")

    def _scan_folder(self):
        """扫描 patterns/ 文件夹，发现未登记的 PDF"""
        if not PDF_DIR.exists():
            QMessageBox.warning(self, "提示", "patterns/ 文件夹不存在")
            return

        existing = {p["filename"] for p in self.patterns}
        new_pdfs = []

        for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
            if pdf_path.name not in existing:
                # 尝试读取 PDF 标题
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
                })

        if not new_pdfs:
            QMessageBox.information(self, "扫描结果", "没有发现未登记的 PDF，所有文件已在清单中。")
            return

        # 列出新发现的文件，让用户确认
        names = "\n".join(f"  • {p['title']} ({p['filename']})" for p in new_pdfs)
        reply = QMessageBox.question(
            self, f"发现 {len(new_pdfs)} 张未登记的 PDF",
            f"以下 PDF 未在清单中：\n\n{names}\n\n是否全部添加到清单？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.patterns.extend(new_pdfs)
            save_patterns(self.patterns)
            self._reload_table()
            self.status_label.setText(f"✅ 已添加 {len(new_pdfs)} 张图纸，请补充分类和难度等信息")

    def _generate_site(self):
        """生成网页"""
        py_exe = sys.executable
        self.cmd_thread = CommandThread([py_exe, str(GENERATE_SCRIPT)])
        self.cmd_thread.output.connect(
            lambda text: self.status_label.setText(self.status_label.text() + text if not self.status_label.text().startswith("$") else text)
        )
        self.cmd_thread.finished_signal.connect(self._on_command_done)
        self.btn_generate.setEnabled(False)
        self.status_label.setText("正在生成网页…")
        self.cmd_thread.start()

    def _push_github(self):
        """推送到 GitHub"""
        # 先生成网页
        py_exe = sys.executable
        self.cmd_thread = CommandThread([py_exe, str(GENERATE_SCRIPT)])
        self.cmd_thread.finished_signal.connect(
            lambda ok, msg: self._do_git_commands() if ok else self._on_command_done(ok, msg)
        )
        self.btn_push.setEnabled(False)
        self.status_label.setText("正在生成网页并推送到 GitHub…")
        self.cmd_thread.start()

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
        commit_thread.finished_signal.connect(
            lambda ok, msg: self._git_push() if ok else self._on_command_done(ok, msg)
        )
        commit_thread.start()
        self.cmd_thread = commit_thread

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

    # ─── 样式 ───

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {COLOR_BG};
            }}
            QWidget {{
                color: {COLOR_TEXT};
                font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
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
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {COLOR_PRIMARY_DARK};
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
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    border-color: {COLOR_PRIMARY};
                    color: {COLOR_PRIMARY};
                }}
                QPushButton:disabled {{
                    background: #eee;
                    color: #aaa;
                }}
            """


# ═══════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════

def main():
    # 确保 patterns 文件夹存在
    PDF_DIR.mkdir(exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("编织图纸管理器")

    window = PatternManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
