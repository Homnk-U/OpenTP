import sys
import os

# Este bloque le ayuda a Python a encontrar las carpetas internas sin errores de importación
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from core.kinematics import probar_matematicas

def main():
    # 1. Probamos que el backend funcione en la terminal
    probar_matematicas()
    
    # 2. Arrancamos la aplicación gráfica
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
