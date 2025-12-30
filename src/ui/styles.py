"""
Light theme styling for the application.
"""

from PySide6.QtWidgets import QApplication, QSpinBox, QDoubleSpinBox, QAbstractSpinBox
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt, QObject, QEvent


# Color palette - Clean light theme
COLORS = {
    'bg_primary': '#ffffff',
    'bg_secondary': '#f5f5f5',
    'bg_tertiary': '#eeeeee',
    'bg_widget': '#ffffff',
    'accent': '#1976d2',
    'accent_hover': '#1565c0',
    'accent_light': '#e3f2fd',
    'text_primary': '#212121',
    'text_secondary': '#757575',
    'text_disabled': '#bdbdbd',
    'border': '#e0e0e0',
    'border_dark': '#bdbdbd',
    'success': '#2e7d32',
    'warning': '#f57c00',
    'error': '#c62828',
    'highlight': '#1976d2',
}


STYLESHEET = """
/* Main window */
QMainWindow, QDialog {
    background-color: #f5f5f5;
    color: #212121;
}

QWidget {
    color: #212121;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}

/* Menu bar */
QMenuBar {
    background-color: #ffffff;
    color: #212121;
    border-bottom: 1px solid #e0e0e0;
    padding: 2px 0;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
}

QMenuBar::item:selected {
    background-color: #eeeeee;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    padding: 4px 0;
}

QMenu::item {
    padding: 6px 24px;
}

QMenu::item:selected {
    background-color: #1976d2;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background: #e0e0e0;
    margin: 4px 0;
}

/* Toolbar */
QToolBar {
    background-color: #ffffff;
    border: none;
    border-bottom: 1px solid #e0e0e0;
    padding: 4px 8px;
    spacing: 6px;
}

QToolBar::separator {
    width: 1px;
    background: #e0e0e0;
    margin: 4px 6px;
}

QToolButton {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px 12px;
    color: #212121;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #f5f5f5;
    border-color: #bdbdbd;
}

QToolButton:pressed {
    background-color: #eeeeee;
}

QToolButton:checked {
    background-color: #1976d2;
    border-color: #1976d2;
    color: #ffffff;
}

/* Status bar */
QStatusBar {
    background-color: #ffffff;
    color: #757575;
    border-top: 1px solid #e0e0e0;
    padding: 2px 8px;
    font-size: 11px;
}

QStatusBar::item {
    border: none;
}

/* Dock widgets */
QDockWidget {
    color: #212121;
    font-weight: 500;
    font-size: 12px;
}

QDockWidget::title {
    background-color: #fafafa;
    padding: 6px 8px;
    border: 1px solid #e0e0e0;
    text-align: left;
}

QDockWidget::close-button, QDockWidget::float-button {
    border: none;
    background: transparent;
    padding: 2px;
}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {
    background-color: #eeeeee;
    border-radius: 3px;
}

/* Panel borders are set directly in Python code */

/* Group box */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    margin-top: 12px;
    padding: 12px;
    padding-top: 20px;
    font-weight: normal;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    color: #1976d2;
    font-weight: 500;
    font-size: 11px;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 5px 12px;
    font-size: 11px;
    min-height: 14px;
    min-width: 40px;
}

QPushButton:hover {
    background-color: #f5f5f5;
    border-color: #bdbdbd;
}

QPushButton:pressed {
    background-color: #eeeeee;
}

QPushButton:disabled {
    background-color: #fafafa;
    color: #bdbdbd;
    border-color: #eeeeee;
}

QPushButton#primary {
    background-color: #1976d2;
    border-color: #1976d2;
    color: #ffffff;
}

QPushButton#primary:hover {
    background-color: #1565c0;
    border-color: #1565c0;
}

/* Input fields */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px 8px;
    color: #212121;
    selection-background-color: #1976d2;
    selection-color: #ffffff;
    font-size: 12px;
}

QLineEdit:focus {
    border-color: #1976d2;
}

QLineEdit:disabled {
    background-color: #fafafa;
    color: #bdbdbd;
}

/* Spinbox */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px 8px;
    padding-right: 20px;
    color: #212121;
    font-size: 12px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #1976d2;
}

QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #fafafa;
    color: #bdbdbd;
}

/* Spinbox buttons removed - users can type values directly */

/* Combo box */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px 8px;
    padding-right: 24px;
    color: #212121;
    font-size: 12px;
    min-width: 80px;
}

QComboBox:hover {
    border-color: #bdbdbd;
}

QComboBox:focus {
    border-color: #1976d2;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border: none;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    selection-background-color: #1976d2;
    selection-color: #ffffff;
    outline: none;
    padding: 4px 0;
}

QComboBox QAbstractItemView::item {
    padding: 6px 8px;
    min-height: 20px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #ffffff;
    alternate-background-color: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    gridline-color: #eeeeee;
    selection-background-color: #e3f2fd;
    selection-color: #212121;
    font-size: 13px;
}

QTableWidget::item, QTableView::item {
    padding: 4px 8px;
    border: none;
    min-height: 32px;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #e3f2fd;
    color: #212121;
}

QHeaderView::section {
    background-color: #fafafa;
    color: #757575;
    padding: 8px;
    border: none;
    border-right: 1px solid #eeeeee;
    border-bottom: 1px solid #e0e0e0;
    font-weight: 600;
    font-size: 11px;
}

QHeaderView::section:hover {
    background-color: #f5f5f5;
}

/* Widgets inside table cells */
QTableWidget QLineEdit {
    background-color: #ffffff;
    border: 1px solid #1976d2;
    border-radius: 0px;
    padding: 0px 4px;
    color: #212121;
    margin: 0px;
    font-size: 13px;
    min-height: 32px;
}

QTableWidget QLineEdit:focus {
    border-color: #1976d2;
}

QTableWidget QSpinBox, QTableWidget QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 2px;
    padding: 3px 6px;
    padding-right: 16px;
    color: #212121;
    margin: 2px;
    font-size: 12px;
}

/* Spinbox buttons removed - users can type values directly */

QTableWidget QComboBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 2px;
    padding: 3px 6px;
    padding-right: 18px;
    color: #212121;
    margin: 2px;
    font-size: 12px;
    min-width: 50px;
}

QTableWidget QComboBox::drop-down {
    width: 16px;
}

QTableWidget QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    selection-background-color: #1976d2;
    selection-color: #ffffff;
    color: #212121;
}

/* Scroll bars */
QScrollBar:vertical {
    background-color: #f5f5f5;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #bdbdbd;
    border-radius: 5px;
    min-height: 20px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9e9e9e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f5f5f5;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #bdbdbd;
    border-radius: 5px;
    min-width: 20px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #9e9e9e;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Slider */
QSlider::groove:horizontal {
    height: 4px;
    background-color: #e0e0e0;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: #1976d2;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #1565c0;
}

/* Check box */
QCheckBox {
    spacing: 6px;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #bdbdbd;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #1976d2;
    border-color: #1976d2;
}

QCheckBox::indicator:hover {
    border-color: #757575;
}

/* Labels - ensure no borders anywhere */
QLabel, QGroupBox QLabel, QFormLayout QLabel, QWidget QLabel {
    color: #212121;
    font-size: 12px;
    border: 0px none transparent;
    border-width: 0px;
    border-style: none;
    background-color: transparent;
    background: transparent;
    padding: 0px;
    margin: 0px;
}

QLabel#heading {
    font-size: 14px;
    font-weight: 600;
    color: #1976d2;
}

QLabel#subheading {
    color: #757575;
    font-size: 11px;
}

/* Splitter */
QSplitter::handle {
    background-color: #e0e0e0;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* Tooltip */
QToolTip {
    background-color: #424242;
    color: #ffffff;
    border: none;
    padding: 4px 8px;
    font-size: 11px;
}

/* Frame - only style actual frames, not labels */
QFrame[frameShape="4"], QFrame[frameShape="5"], QFrame[frameShape="6"] {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}

/* Scroll area */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Dialog buttons */
QDialogButtonBox QPushButton {
    min-width: 70px;
}
"""


class SpinBoxNoButtonsFilter(QObject):
    """Global event filter that removes buttons from all spinboxes."""
    
    def __init__(self):
        super().__init__()
        self._processed = set()
    
    def eventFilter(self, obj, event):
        try:
            if event.type() in (QEvent.Type.Show, QEvent.Type.Polish):
                if isinstance(obj, (QSpinBox, QDoubleSpinBox)):
                    if id(obj) not in self._processed:
                        self._processed.add(id(obj))
                        obj.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            pass
        
        return False


# Global instance of the filter
_spinbox_filter = None


def apply_theme(app: QApplication) -> None:
    """Apply the light theme to the application."""
    app.setStyleSheet(STYLESHEET)
    
    # Install global event filter to remove spinbox buttons
    global _spinbox_filter
    if _spinbox_filter is None:
        _spinbox_filter = SpinBoxNoButtonsFilter()
    app.installEventFilter(_spinbox_filter)
    
    # Also set palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_secondary']))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS['bg_primary']))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS['bg_secondary']))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor('#424242'))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor('#ffffff'))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS['bg_primary']))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(COLORS['accent']))
    palette.setColor(QPalette.ColorRole.Link, QColor(COLORS['highlight']))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS['accent']))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
    
    app.setPalette(palette)


# Keep backward compatibility
def apply_dark_theme(app: QApplication) -> None:
    """Backward compatible alias."""
    apply_theme(app)
