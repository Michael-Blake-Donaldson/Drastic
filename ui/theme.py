from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    font_family: str = "Segoe UI Variable"
    base_font_size: int = 11
    # WCAG 1.4.11: input border must be ≥ 3:1 against the white field background.
    # #7390a2 achieves 3.37:1 against #ffffff.
    input_border_color: str = "#7390a2"
    # WCAG 2.4.7 / 1.4.11: focus ring uses the primary brand blue.
    # #1474a3 achieves 5.18:1 against #ffffff.
    focus_ring_color: str = "#1474a3"
    # WCAG 1.4.3: text-selection background must be ≥ 4.5:1 against the
    # selected (white) text.  #135f90 achieves 6.84:1 against #ffffff.
    input_selection_bg: str = "#135f90"


THEME_TOKENS = ThemeTokens()


APP_STYLESHEET = """
QMainWindow {
    background-color: #f2f5f8;
}
QDockWidget::title {
    background: #e8eef3;
    color: #163447;
    padding: 8px 10px;
    font-weight: 600;
    border-bottom: 1px solid #d3dde6;
}
QToolBar {
    background: #f8fafc;
    border: 1px solid #dbe5ed;
    spacing: 8px;
    padding: 6px;
}
QToolButton {
    background: #1474a3;
    color: #ffffff;
    border: 1px solid #0f628a;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 600;
}
QToolButton:hover {
    background: #0f678f;
}
QTabWidget::pane {
    border: 1px solid #d4dfe8;
    background: #ffffff;
}
QTabBar::tab {
    background: #edf2f7;
    color: #22323d;
    border: 1px solid #d4dfe8;
    border-bottom: none;
    padding: 8px 12px;
    margin-right: 4px;
    min-width: 110px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0e4f70;
    font-weight: 700;
}
QLabel {
    color: #1b2d3a;
    font-size: 12px;
}
QLabel#SectionHeader {
    font-size: 14px;
    font-weight: 700;
    color: #0f5679;
    margin-top: 10px;
    margin-bottom: 4px;
}
QLabel#SubtleHint {
    color: #4f6573;
    margin-bottom: 6px;
}
QLabel#ValidationBanner {
    background: #fff0f0;
    color: #8a1b1b;
    border: 1px solid #efc1c1;
    border-radius: 6px;
    padding: 8px;
    font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    border: 1px solid #7390a2;
    border-radius: 6px;
    background: #ffffff;
    color: #142836;
    padding: 6px;
    selection-background-color: #135f90;
    selection-color: #ffffff;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    min-height: 34px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #142836;
    border: 1px solid #c2d0da;
    selection-background-color: #d9edf9;
    selection-color: #0f3550;
    outline: 0;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QTextEdit {
    min-height: 120px;
}
QPushButton {
    background: #ffffff;
    color: #145d80;
    border: 1px solid #aac0cf;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background: #e8f2f8;
}
QTableWidget, QTreeWidget, QListWidget {
    background: #ffffff;
    border: 1px solid #d4dfe8;
    color: #142631;
    gridline-color: #e7edf2;
    alternate-background-color: #f4f9fc;
}
QHeaderView::section {
    background: #edf4f9;
    color: #1f2e38;
    border: 1px solid #d2dbe2;
    padding: 6px;
    font-weight: 700;
}
QScrollArea {
    border: none;
    background: #ffffff;
}
QScrollArea > QWidget > QWidget#ScenarioContent {
    background: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    /* WCAG 2.4.7 Focus Visible — 2 px primary-blue ring; padding reduced by
       1 px each side so the overall widget height is unchanged. */
    border: 2px solid #1474a3;
    padding: 5px;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QTextEdit:disabled {
    background: #f0f4f7;
    color: #6e8fa0;
    border-color: #b6cad4;
}
QPushButton:focus {
    /* WCAG 2.4.7 — same 2 px ring; padding compensated to avoid size jitter. */
    border: 2px solid #1474a3;
    padding: 6px 11px;
}
QPushButton:pressed {
    background: #d0e8f2;
    border-color: #7ab4cc;
}
QPushButton:disabled {
    background: #f0f4f7;
    color: #7a9aaa;
    border-color: #c0d4de;
}
QToolButton:pressed {
    background: #0c5a7c;
}
QToolButton:disabled {
    background: #8ab5c9;
    color: #ddedf5;
    border-color: #79a3b8;
}
QListWidget::item:selected, QTableWidget::item:selected, QTreeWidget::item:selected {
    /* WCAG 1.4.3 — #135f90 bg with white text = 6.84:1 ✅ */
    background: #135f90;
    color: #ffffff;
}
QLabel#MetricLabel {
    background: #eef5fb;
    border: 1px solid #c7d8e5;
    border-radius: 6px;
    color: #12384d;
    font-size: 12px;
    font-weight: 700;
    padding: 6px;
}
QLabel#CompareCard {
    background: #f4f9fd;
    border: 1px solid #c8d9e6;
    border-radius: 8px;
    color: #12384d;
    font-size: 12px;
    font-weight: 700;
    padding: 8px;
    min-height: 44px;
}
QStatusBar {
    background: #f5f8fb;
    color: #1a3c51;
}
"""
