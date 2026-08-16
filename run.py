import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import threading
import time
import uvicorn

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.desktop.main_container import MainContainer

from database.city import init_city_table
from database.db import init_db

def start_api_server():

#Startimg the FastAPI server in a background thread.
    import api.app  
    uvicorn.run(api.app.app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    init_city_table()
    init_db()
    
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    time.sleep(2)
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    
    window = MainContainer()
    window.show()
    
    sys.exit(app.exec())