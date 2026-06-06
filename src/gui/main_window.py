from PySide6.QtWidgets import QMainWindow, QLabel
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Configuración básica de la ventana profesional
        self.setWindowTitle("OpenTP Simulator - UPIITA IPN")
        self.resize(600, 400)
        
        # Mensaje central de éxito
        texto = QLabel("¡OpenTP Inicializado!\n\nEl entorno 3D y el compilador TP se configurarán aquí.", self)
        texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        texto.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        
        self.setCentralWidget(texto)
