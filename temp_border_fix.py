import os
from PySide6.QtWidgets import (
    QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMenu, QCheckBox, QWidget, QAbstractItemView, QLabel,
    QDialog, QProgressBar, QPushButton, QLineEdit, QHBoxLayout,
    QSizePolicy, QFileDialog, QFontDialog, QColorDialog,
    QFontComboBox, QSpinBox, QComboBox, QToolButton
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QBrush, QPixmap, QAction
import pyqtgraph as pg
from src.ui.table_view import TableView
from src.ui.plot_view import PlotView
from src.ui.variables_panel import VariablesPanel
from src.ui.bits_panel import BitsPanel
from src.ui.scan_dialog import ScanWorker
from src.models.register import AccessMode
from src.ui.styles import COLORS

# Quick script to add borders to remaining panels
# ViewerTextPanel at line 992, ViewerImagePanel at line 1069

print("Lines to modify:")
print("Line 992: ViewerTextPanel._setup_ui")
print("Line 1069: ViewerImagePanel._setup_ui")
