import sys
import os

# Permitir que Python encuentre los módulos internos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow  # <-- Cambiamos la importación

def main():
    app = QApplication(sys.argv)
    window = MainWindow()               # <-- Arrancamos la ventana contenedora
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()