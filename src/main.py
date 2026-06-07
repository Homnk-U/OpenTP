import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QSplashScreen, QWidget
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from gui.main_window import MainWindow
from core.kinematics import probar_matematicas

def centrar_ventana(ventana, ancho, alto, app):
    """Calcula el centro de la pantalla actual y posiciona la ventana ahí."""
    pantalla = app.primaryScreen().geometry()
    x = (pantalla.width() - ancho) // 2
    y = (pantalla.height() - alto) // 2
    ventana.setGeometry(x, y, ancho, alto)

def main():
    app = QApplication(sys.argv)
    
    # Dimensiones exactas para ambas ventanas
    ANCHO_APP = 1024
    ALTO_APP = 768
    
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_logo = os.path.join(ruta_base, "assets", "icons", "robot_fanuc.png")
    
    # --- 1. LIENZO TRANSPARENTE PARA EL SPLASH ---
    # Creamos un fondo invisible del tamaño de la app para que no se asomen esquinas cuadradas
    lienzo_transparente = QPixmap(ANCHO_APP, ALTO_APP)
    lienzeno_vacio = lienzo_transparente.fill(Qt.transparent)
    
    splash = QSplashScreen(lienzo_transparente)
    splash.setAttribute(Qt.WA_TranslucentBackground)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    
    # Centramos el splash en el monitor
    centrar_ventana(splash, ANCHO_APP, ALTO_APP, app)
    
    # --- 2. CONTENEDOR CON BORDES REDONDOS REALES ---
    contenedor = QWidget(splash)
    contenedor.setGeometry(0, 0, ANCHO_APP, ALTO_APP)
    
    # Si la imagen no existe, usamos un color plano oscuro
    if not os.path.exists(ruta_logo):
        contenedor.setStyleSheet(f"""
            QWidget {{
                background-color: #1e1e2e;
                border-radius: 30px;
            }}
        """)
    else:
        # Ajustamos la imagen con CSS para que se adapte perfectamente al redondeado
        contenedor.setStyleSheet(f"""
            QWidget {{
                background-image: url('{ruta_logo.replace('\\', "/")}');
                background-position: center;
                background-repeat: no-repeat;
                border-radius: 30px;
            }}
        """)
        
    splash.show()
    app.processEvents()
    
    # --- 3. CARGA DE BACKEND ---
    probar_matematicas()
    time.sleep(2.5) # Tiempo de visualización
    
    # --- 4. PREPARAR VENTANA PRINCIPAL ---
    window = MainWindow()
    window.resize(ANCHO_APP, ALTO_APP)
    # Forzamos a la ventana principal a estar EXACTAMENTE en las mismas coordenadas que el splash
    centrar_ventana(window, ANCHO_APP, ALTO_APP, app)
    
    # --- 5. ANIMACIÓN DE TRANSICIÓN (FADE OUT) ---
    animacion = QPropertyAnimation(splash, b"windowOpacity")
    animacion.setDuration(600) # 0.6 segundos de desvanecimiento suave
    animacion.setStartValue(1.0)
    animacion.setEndValue(0.0)
    animacion.setEasingCurve(QEasingCurve.OutQuad)
    
    def al_terminar_animacion():
        window.show()          # Aparece la ventana principal en el mismo lugar
        splash.finish(window) # Destruye el splash
        
    animacion.finished.connect(al_terminar_animacion)
    animacion.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()