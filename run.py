# run.py
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.desktop.main_container import MainContainer

from database.city import init_city_table
from database.db import init_db

if __name__ == "__main__":
    init_city_table()
    init_db()
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    
    window = MainContainer()
    window.show()
    
    # This starts the event loop - app stays running until window closes
    sys.exit(app.exec())  # ← This line must be present