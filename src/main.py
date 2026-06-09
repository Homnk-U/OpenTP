import sys
import time
from pathlib import Path

# Configuración del path del sistema
DIRECTORIO_ACTUAL = Path(__file__).resolve().parent
sys.path.append(str(DIRECTORIO_ACTUAL))

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen, QWidget

from core.kinematics import probar_matematicas
from gui.main_window import MainWindow

# --- CONSTANTES GLOBALES ---
ANCHO_APP = 1024
ALTO_APP = 768
DURACION_FADE_OUT_MS = 600
TIEMPO_CARGA_S = 2.5

def centrar_ventana(ventana: QWidget, ancho: int, alto: int, app: QApplication) -> None:
    """Calcula el centro de la pantalla actual y posiciona la ventana ahí."""
    pantalla = app.primaryScreen().geometry()
    x = (pantalla.width() - ancho) // 2
    y = (pantalla.height() - alto) // 2
    ventana.setGeometry(x, y, ancho, alto)

class CustomSplashScreen(QSplashScreen):
    """Clase especializada para el Splash Screen"""
    def __init__(self, ruta_logo: Path, app: QApplication):
        # Creamos el lienzo transparente del tamaño de la app
        lienzo = QPixmap(ANCHO_APP, ALTO_APP)
        lienzo.fill(Qt.transparent)
        
        super().__init__(lienzo)
        self.app = app
        
        # Configuración de ventana de la app
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        centrar_ventana(self, ANCHO_APP, ALTO_APP, self.app)
        
        # Contenedor para los bordes redondeados
        self.contenedor = QWidget(self)
        self.contenedor.setGeometry(0, 0, ANCHO_APP, ALTO_APP)
        self._aplicar_estilos(ruta_logo)

    def ejecutar_transicion_salida(self, ventana_principal: QWidget) -> None:
        """Maneja la animación de desvanecimiento y da paso a la ventana principal."""
        # Al usar 'self.animacion', aseguramos que el Garbage Collector no la destruya
        self.animacion = QPropertyAnimation(self, b"windowOpacity")
        self.animacion.setDuration(DURACION_FADE_OUT_MS)
        self.animacion.setStartValue(1.0)
        self.animacion.setEndValue(0.0)
        self.animacion.setEasingCurve(QEasingCurve.OutQuad)
        
        def al_terminar():
            ventana_principal.show()
            self.finish(ventana_principal)
            
        self.animacion.finished.connect(al_terminar)
        self.animacion.start()


def main() -> None:
    """Función principal que orquesta el ciclo de vida de la aplicación."""
    app = QApplication(sys.argv)
    
    # Definición de rutas usando pathlib (más limpio que os.path)
    ruta_logo = DIRECTORIO_ACTUAL / "assets" / "icons" / "robot_fanuc.png"
    
    # 1. Inicializar y mostrar Splash
    splash = CustomSplashScreen(ruta_logo, app)
    splash.show()
    app.processEvents()
    
    # 2. Carga del Backend
    probar_matematicas()
    time.sleep(TIEMPO_CARGA_S) 
    
    # 3. Preparar ventana principal
    window = MainWindow()
    window.resize(ANCHO_APP, ALTO_APP)
    centrar_ventana(window, ANCHO_APP, ALTO_APP, app)
    
    # 4. Transición animada
    splash.ejecutar_transicion_salida(window)
    
    # Ejecución del bucle de eventos (Estilo Qt6)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()