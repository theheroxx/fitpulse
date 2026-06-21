# ui/desktop/main.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.city import init_city_table
from database.db import init_db
init_city_table()
init_db()

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.desktop.main_container import MainContainer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    
    style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
    if os.path.exists(style_path):
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except:
            pass
    
    window = MainContainer()
    window.show()
    sys.exit(app.exec())