"""
Application styling with theme support.
"""

from PySide6.QtWidgets import QApplication, QSpinBox, QDoubleSpinBox, QAbstractSpinBox
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt, QObject, QEvent


# Light Theme Colors
LIGHT_COLORS = {
    'bg_primary': '#ffffff',
    'bg_secondary': '#f5f5f5',
    'bg_tertiary': '#eeeeee',
    'bg_header': '#fafafa',
    'bg_widget': '#ffffff',
    
    'text_primary': '#212121',
    'text_secondary': '#757575',
    'text_disabled': '#bdbdbd',
    'text_inverse': '#ffffff',
    
    'border': '#e0e0e0',
    'border_dark': '#bdbdbd',
    
    'accent': '#1976d2',
    'accent_hover': '#1565c0',
    'accent_light': '#e3f2fd',
    
    'success': '#2e7d32',
    'warning': '#f57c00',
    'error': '#c62828',
    'highlight': '#1976d2',
    
    'tooltip_bg': '#424242',
    'tooltip_text': '#ffffff',
    'selection_bg': '#e3f2fd',
    'selection_text': '#212121',
}

# Dark Theme Colors
DARK_COLORS = {
    'bg_primary': '#1e1e1e',
    'bg_secondary': '#252526',
    'bg_tertiary': '#2d2d2d',
    'bg_header': '#252526',
    'bg_widget': '#333333',
    
    'text_primary': '#d4d4d4',
    'text_secondary': '#a0a0a0',
    'text_disabled': '#606060',
    'text_inverse': '#1e1e1e',
    
    'border': '#3e3e42',
    'border_dark': '#505050',
    
    'accent': '#007acc',
    'accent_hover': '#0098ff',
    'accent_light': '#264f78',
    
    'success': '#4ec9b0',
    'warning': '#cca700',
    'error': '#f44747',
    'highlight': '#007acc',
    
    'tooltip_bg': '#252526',
    'tooltip_text': '#d4d4d4',
    'selection_bg': '#264f78',
    'selection_text': '#ffffff',
}

# Provide a default COLORS dict for imports that might use it directly (backward compat)
COLORS = LIGHT_COLORS.copy()


THEME_TEMPLATE = """
/* Main window */
QMainWindow, QDialog {
    background-color: %(bg_secondary)s;
    color: %(text_primary)s;
}

QWidget {
    color: %(text_primary)s;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}

/* Menu bar */
QMenuBar {
    background-color: %(bg_primary)s;
    color: %(text_primary)s;
    border-bottom: 1px solid %(border)s;
    padding: 2px 0;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
}

QMenuBar::item:selected {
    background-color: %(bg_tertiary)s;
}

QMenu {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    padding: 4px 0;
}

QMenu::item {
    padding: 6px 24px;
    color: %(text_primary)s;
}

QMenu::item:selected {
    background-color: %(accent)s;
    color: %(text_inverse)s;
}

QMenu::separator {
    height: 1px;
    background: %(border)s;
    margin: 4px 0;
}

/* Toolbar */
QToolBar {
    background-color: %(bg_primary)s;
    border: none;
    border-bottom: 1px solid %(border)s;
    padding: 4px 8px;
    spacing: 6px;
}

QToolBar::separator {
    width: 1px;
    background: %(border)s;
    margin: 4px 6px;
}

QToolButton {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 12px;
    color: %(text_primary)s;
    font-weight: 500;
}

QToolButton:hover {
    background-color: %(bg_secondary)s;
    border-color: %(border_dark)s;
}

QToolButton:pressed {
    background-color: %(bg_tertiary)s;
}

QToolButton:checked {
    background-color: %(accent)s;
    border-color: %(accent)s;
    color: %(text_inverse)s;
}

/* Status bar */
QStatusBar {
    background-color: %(bg_primary)s;
    color: %(text_secondary)s;
    border-top: 1px solid %(border)s;
    padding: 2px 8px;
    font-size: 11px;
}

QStatusBar::item {
    border: none;
}

/* Dock widgets */
QDockWidget {
    color: %(text_primary)s;
    font-weight: 500;
    font-size: 12px;
}

QDockWidget::title {
    background-color: %(bg_header)s;
    padding: 6px 8px;
    border: 1px solid %(border)s;
    text-align: left;
    color: %(text_primary)s;
}

QDockWidget::close-button, QDockWidget::float-button {
    border: none;
    background: transparent;
    padding: 2px;
}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {
    background-color: %(bg_tertiary)s;
    border-radius: 3px;
}

/* Group box */
QGroupBox {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
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
    color: %(accent)s;
    font-weight: 500;
    font-size: 11px;
    background-color: %(bg_primary)s; 
}

/* Buttons */
QPushButton {
    background-color: %(bg_primary)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 5px 12px;
    font-size: 11px;
    min-height: 14px;
    min-width: 40px;
}

QPushButton:hover {
    background-color: %(bg_secondary)s;
    border-color: %(border_dark)s;
}

QPushButton:pressed {
    background-color: %(bg_tertiary)s;
}

QPushButton:disabled {
    background-color: %(bg_header)s;
    color: %(text_disabled)s;
    border-color: %(border)s;
}

QPushButton#primary {
    background-color: %(accent)s;
    border-color: %(accent)s;
    color: %(text_inverse)s;
}

QPushButton#primary:hover {
    background-color: %(accent_hover)s;
    border-color: %(accent_hover)s;
}

/* Input fields */
QLineEdit {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 8px;
    color: %(text_primary)s;
    selection-background-color: %(accent)s;
    selection-color: %(text_inverse)s;
    font-size: 12px;
}

QLineEdit:focus {
    border-color: %(accent)s;
}

QLineEdit:disabled {
    background-color: %(bg_header)s;
    color: %(text_disabled)s;
}

/* Spinbox */
QSpinBox, QDoubleSpinBox {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 8px;
    padding-right: 20px;
    color: %(text_primary)s;
    font-size: 12px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: %(accent)s;
}

QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: %(bg_header)s;
    color: %(text_disabled)s;
}

/* Combo box */
QComboBox {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 8px;
    padding-right: 24px;
    color: %(text_primary)s;
    font-size: 12px;
    min-width: 80px;
}

QComboBox:hover {
    border-color: %(border_dark)s;
}

QComboBox:focus {
    border-color: %(accent)s;
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
    /* We rely on system arrow or specific image, usually handled by OS style, but let's leave it default for simplicity or add color adjustment if possible. 
       QComboBox uses standard OS primitives mostly. 
    */
}

QComboBox QAbstractItemView {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    selection-background-color: %(accent)s;
    selection-color: %(text_inverse)s;
    outline: none;
    padding: 4px 0;
    color: %(text_primary)s;
}

QComboBox QAbstractItemView::item {
    padding: 6px 8px;
    min-height: 20px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: %(bg_primary)s;
    alternate-background-color: %(bg_header)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    gridline-color: %(bg_tertiary)s;
    selection-background-color: %(selection_bg)s;
    selection-color: %(selection_text)s;
    font-size: 13px;
    color: %(text_primary)s;
}

QTableWidget::item, QTableView::item {
    padding: 4px 8px;
    border: none;
    min-height: 32px;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: %(selection_bg)s;
    color: %(selection_text)s;
}

QHeaderView::section {
    background-color: %(bg_header)s;
    color: %(text_secondary)s;
    padding: 8px;
    border: none;
    border-right: 1px solid %(bg_tertiary)s;
    border-bottom: 1px solid %(border)s;
    font-weight: 600;
    font-size: 11px;
}

QHeaderView::section:hover {
    background-color: %(bg_secondary)s;
}

/* Widgets inside table cells */
QTableWidget QLineEdit {
    background-color: %(bg_primary)s;
    border: 1px solid %(accent)s;
    border-radius: 0px;
    padding: 0px 4px;
    color: %(text_primary)s;
    margin: 0px;
    font-size: 13px;
    min-height: 32px;
}

QTableWidget QLineEdit:focus {
    border-color: %(accent)s;
}

QTableWidget QSpinBox, QTableWidget QDoubleSpinBox {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 2px;
    padding: 3px 6px;
    padding-right: 16px;
    color: %(text_primary)s;
    margin: 2px;
    font-size: 12px;
}

QTableWidget QComboBox {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 2px;
    padding: 3px 6px;
    padding-right: 18px;
    color: %(text_primary)s;
    margin: 2px;
    font-size: 12px;
    min-width: 50px;
}

QTableWidget QComboBox QAbstractItemView {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    selection-background-color: %(accent)s;
    selection-color: %(text_inverse)s;
    color: %(text_primary)s;
}

/* Scroll bars */
QScrollBar:vertical {
    background-color: %(bg_secondary)s;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: %(text_disabled)s;
    border-radius: 5px;
    min-height: 20px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: %(text_secondary)s;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: %(bg_secondary)s;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: %(text_disabled)s;
    border-radius: 5px;
    min-width: 20px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: %(text_secondary)s;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Slider */
QSlider::groove:horizontal {
    height: 4px;
    background-color: %(border)s;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: %(accent)s;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: %(accent_hover)s;
}

/* Check box */
QCheckBox {
    spacing: 6px;
    font-size: 12px;
    color: %(text_primary)s;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid %(border_dark)s;
    border-radius: 3px;
    background-color: %(bg_primary)s;
}

QCheckBox::indicator:checked {
    background-color: %(accent)s;
    border-color: %(accent)s;
}

QCheckBox::indicator:hover {
    border-color: %(text_secondary)s;
}

/* Labels */
QLabel, QGroupBox QLabel, QFormLayout QLabel, QWidget QLabel {
    color: %(text_primary)s;
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
    color: %(accent)s;
}

QLabel#subheading {
    color: %(text_secondary)s;
    font-size: 11px;
}

/* Splitter */
QSplitter::handle {
    background-color: %(border)s;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* Tooltip */
QToolTip {
    background-color: %(tooltip_bg)s;
    color: %(tooltip_text)s;
    border: none;
    padding: 4px 8px;
    font-size: 11px;
}

/* Frame */
QFrame[frameShape="4"], QFrame[frameShape="5"], QFrame[frameShape="6"] {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
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

/* Tab Widget */
QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar::tab {
    background-color: transparent;
    color: %(text_secondary)s;
    padding: 8px 16px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}

QTabBar::tab:selected {
    color: %(accent)s;
    border-bottom: 2px solid %(accent)s;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    color: %(text_primary)s;
    background-color: %(bg_secondary)s;
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


def apply_theme(app: QApplication, theme='light') -> None:
    """Apply the specified theme to the application."""
    colors = DARK_COLORS if theme == 'dark' else LIGHT_COLORS
    
    # Update global colors reference for other modules
    global COLORS
    COLORS.clear()
    COLORS.update(colors)
    
    # Apply stylesheet
    app.setStyleSheet(THEME_TEMPLATE % colors)
    
    # Install global event filter to remove spinbox buttons
    global _spinbox_filter
    if _spinbox_filter is None:
        _spinbox_filter = SpinBoxNoButtonsFilter()
    app.installEventFilter(_spinbox_filter)
    
    # Also set palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors['bg_secondary']))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors['text_primary']))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors['bg_primary']))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors['bg_secondary']))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors['tooltip_bg']))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors['tooltip_text']))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors['text_primary']))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors['bg_primary']))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors['text_primary']))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors['accent']))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors['highlight']))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors['accent']))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors['text_inverse']))
    
    app.setPalette(palette)


def apply_light_theme(app: QApplication) -> None:
    """Apply light theme."""
    apply_theme(app, 'light')


def apply_dark_theme(app: QApplication) -> None:
    """Apply dark theme."""
    apply_theme(app, 'dark')
