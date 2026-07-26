DARK_STYLESHEET = """
QWidget {
    background: #15171c;
    color: #eef1f5;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QStackedWidget { background: #15171c; }
QFrame#Sidebar {
    background: #0f1115;
    border-right: 1px solid #292d35;
}
QLabel#Brand {
    font-size: 20pt;
    font-weight: 700;
    color: #ffffff;
}
QLabel#PageTitle {
    font-size: 27pt;
    font-weight: 700;
    color: #ffffff;
}
QLabel#PageSubtitle {
    color: #aeb5c0;
    font-size: 11pt;
}
QLabel#Eyebrow {
    color: #6ea8ff;
    font-size: 9pt;
    font-weight: 700;
}
QLabel#SectionTitle {
    color: #ffffff;
    font-size: 15pt;
    font-weight: 700;
}
QLabel#Muted { color: #9fa7b3; }
QLabel#CardValue {
    color: #f6f8fb;
    font-size: 11pt;
    font-weight: 600;
}
QFrame#HeroCard {
    background: #1d2129;
    border: 1px solid #323845;
    border-radius: 12px;
}
QFrame#InfoCard {
    background: #1a1e25;
    border: 1px solid #303642;
    border-radius: 11px;
}
QPushButton {
    background: #242933;
    border: 1px solid #353c49;
    border-radius: 9px;
    padding: 10px 13px;
    text-align: left;
}
QPushButton:hover {
    background: #2d3440;
    border-color: #465062;
}
QPushButton:pressed { background: #20252d; }
QPushButton:checked {
    background: #245ea8;
    border-color: #4a86d4;
    color: #ffffff;
}
QPushButton#Primary {
    background: #2f6fca;
    border-color: #4a86d4;
    color: #ffffff;
    text-align: center;
    font-weight: 700;
    padding: 11px 17px;
}
QPushButton#Primary:hover { background: #387bd9; }
QPushButton#Secondary {
    text-align: center;
    font-weight: 600;
    padding: 11px 17px;
}
QPushButton#RecentProject {
    background: #1b1f26;
    padding: 12px 14px;
}
QLineEdit, QComboBox {
    background: #1d2128;
    border: 1px solid #353c48;
    border-radius: 8px;
    padding: 9px;
}
QLineEdit:focus, QComboBox:focus { border-color: #4a86d4; }
QGroupBox {
    background: #1a1e25;
    border: 1px solid #303642;
    border-radius: 11px;
    margin-top: 13px;
    padding: 14px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QStatusBar {
    background: #101217;
    color: #aeb5c0;
    border-top: 1px solid #292d35;
}
"""

LIGHT_STYLESHEET = """
QWidget {
    background: #f4f6f9;
    color: #20242b;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QStackedWidget { background: #f4f6f9; }
QFrame#Sidebar {
    background: #ffffff;
    border-right: 1px solid #dce1e8;
}
QLabel#Brand {
    font-size: 20pt;
    font-weight: 700;
    color: #171b22;
}
QLabel#PageTitle {
    font-size: 27pt;
    font-weight: 700;
    color: #171b22;
}
QLabel#PageSubtitle {
    color: #66707d;
    font-size: 11pt;
}
QLabel#Eyebrow {
    color: #2867b2;
    font-size: 9pt;
    font-weight: 700;
}
QLabel#SectionTitle {
    color: #171b22;
    font-size: 15pt;
    font-weight: 700;
}
QLabel#Muted { color: #66707d; }
QLabel#CardValue {
    color: #242a33;
    font-size: 11pt;
    font-weight: 600;
}
QFrame#HeroCard {
    background: #ffffff;
    border: 1px solid #d9dfe7;
    border-radius: 12px;
}
QFrame#InfoCard {
    background: #ffffff;
    border: 1px solid #d9dfe7;
    border-radius: 11px;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d4dae3;
    border-radius: 9px;
    padding: 10px 13px;
    text-align: left;
}
QPushButton:hover {
    background: #edf2f8;
    border-color: #bcc8d7;
}
QPushButton:pressed { background: #e4eaf2; }
QPushButton:checked {
    background: #dceafb;
    border-color: #78a6dc;
    color: #174f91;
}
QPushButton#Primary {
    background: #2f6fca;
    border-color: #2f6fca;
    color: #ffffff;
    text-align: center;
    font-weight: 700;
    padding: 11px 17px;
}
QPushButton#Primary:hover { background: #2864b8; }
QPushButton#Secondary {
    text-align: center;
    font-weight: 600;
    padding: 11px 17px;
}
QPushButton#RecentProject {
    background: #f9fafc;
    padding: 12px 14px;
}
QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #d4dae3;
    border-radius: 8px;
    padding: 9px;
}
QLineEdit:focus, QComboBox:focus { border-color: #78a6dc; }
QGroupBox {
    background: #ffffff;
    border: 1px solid #d9dfe7;
    border-radius: 11px;
    margin-top: 13px;
    padding: 14px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QStatusBar {
    background: #ffffff;
    color: #66707d;
    border-top: 1px solid #dce1e8;
}
"""
