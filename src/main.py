import sys
import os
import time

# --- ANCLAJE DE RUTAS CRÍTICO ---
if hasattr(sys, '_MEIPASS'):
    ruta_raiz = sys._MEIPASS
else:
    ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

ruta_src = os.path.join(ruta_raiz, "src")
if os.path.exists(ruta_src) and ruta_src not in sys.path:
    sys.path.insert(0, ruta_src)

# Forzamos de forma global y absoluta el directorio de trabajo del sistema operativo
os.chdir(ruta_raiz)
# --------------------------------

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QCoreApplication
from PySide6.QtGui import QPixmap, QIcon

def resolver_ruta(ruta_relativa):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(ruta_raiz, ruta_relativa)

# =========================================================================
# 1. HILO SECUNDARIO (Puro y seguro para fluidos de Qt)
# =========================================================================
class HiloCargadorIndustrial(QThread):
    progreso_signal = Signal(int)
    estatus_signal = Signal(str)
    carga_completa_signal = Signal() 

    def run(self):
        self.estatus_signal.emit("Inicializando subsistemas de telemetría...")
        self.progreso_signal.emit(25)
        time.sleep(0.4) 

        self.estatus_signal.emit("Cargando entorno físico de motores...")
        self.progreso_signal.emit(60)
        time.sleep(0.4)
        
        self.estatus_signal.emit("Preparando mallas dinámicas del FANUC M-900iA...")
        self.progreso_signal.emit(85)
        time.sleep(0.2)
        
        self.carga_completa_signal.emit()

# =========================================================================
# 2. INTERFAZ GRÁFICA: Pantalla de carga
# =========================================================================
class PantallaDeCarga(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(460, 340)
        
        layout_externo = QVBoxLayout(self)
        layout_externo.setContentsMargins(0, 0, 0, 0)
        
        self.contenedor_visual = QWidget()
        self.contenedor_visual.setStyleSheet("QWidget { background-color: #21252b; border: 1px solid #181a1f; border-radius: 12px; }")
        layout_interno = QVBoxLayout(self.contenedor_visual)
        layout_interno.setContentsMargins(30, 30, 30, 30)
        
        self.lbl_logo = QLabel()
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Resolución de ruta y parche para Qt
        ruta_logo = resolver_ruta(os.path.join("src", "assets", "icons", "OpenTPOrnf.png"))
        ruta_logo_qt = ruta_logo.replace("\\", "/")
        
        if os.path.exists(ruta_logo):
            pixmap = QPixmap(ruta_logo_qt)
            if pixmap.isNull():
                self._mostrar_texto_alternativo("ERROR: Archivo encontrado, pero QPixmap no puede leerlo.\n¿Es realmente un PNG válido?")
            else:
                pixmap = pixmap.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.lbl_logo.setPixmap(pixmap)
        else:
            self._mostrar_texto_alternativo(f"ERROR: Archivo no encontrado en:\n{ruta_logo_qt}")
            
        self.efecto_opacidad = QGraphicsOpacityEffect(self.lbl_logo)
        self.lbl_logo.setGraphicsEffect(self.efecto_opacidad)
        
        self.animacion_parpadeo = QPropertyAnimation(self.efecto_opacidad, b"opacity")
        self.animacion_parpadeo.setDuration(1400)        
        self.animacion_parpadeo.setStartValue(1.0)        
        self.animacion_parpadeo.setKeyValueAt(0.5, 0.25)   
        self.animacion_parpadeo.setEndValue(1.0)          
        self.animacion_parpadeo.setEasingCurve(QEasingCurve.Type.InOutSine) 
        self.animacion_parpadeo.setLoopCount(-1)          
        self.animacion_parpadeo.start()
        
        self.lbl_estatus = QLabel("Inicializando sistema...")
        self.lbl_estatus.setStyleSheet("color: #9da5b4; font-size: 11px; font-family: 'Segoe UI'; font-weight: bold; margin-top: 15px;")
        
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setFixedHeight(4)
        self.barra_progreso.setTextVisible(False)          
        self.barra_progreso.setStyleSheet("""
            QProgressBar { background-color: #1e2227; border: none; border-radius: 2px; }
            QProgressBar::chunk { background-color: #ff6b00; border-radius: 2px; }
        """)
        
        layout_interno.addWidget(self.lbl_logo, stretch=1)
        layout_interno.addWidget(self.lbl_estatus)
        layout_interno.addWidget(self.barra_progreso)
        layout_externo.addWidget(self.contenedor_visual)
        
        self.centrar_en_pantalla()

    def _mostrar_texto_alternativo(self, mensaje_error=""):
        texto = "< OpenTP Simulator >"
        if mensaje_error:
            texto += f"\n\n[Debug] {mensaje_error}"
            self.lbl_logo.setStyleSheet("color: #ff6b00; font-size: 11px; font-weight: bold; font-family: 'Consolas';")
        else:
            self.lbl_logo.setStyleSheet("color: #ff6b00; font-size: 26px; font-weight: bold; font-family: 'Consolas';")
        self.lbl_logo.setText(texto)

    def centrar_en_pantalla(self):
        geo = self.frameGeometry()
        centro = self.screen().availableGeometry().center()
        geo.moveCenter(centro)
        self.move(geo.topLeft())

    def actualizar_progreso(self, valor):
        self.barra_progreso.setValue(valor)

    def actualizar_texto(self, texto):
        self.lbl_estatus.setText(texto)

# =========================================================================
# 3. ORQUESTADOR PRINCIPAL
# =========================================================================
def main():
    app = QApplication(sys.argv)
    
    # También aplicamos el parche de la ruta al icono de la ventana
    ruta_icono = resolver_ruta(os.path.join("src", "assets", "icons", "OpenTPOrnf.png"))
    ruta_icono_qt = ruta_icono.replace("\\", "/")
    if os.path.exists(ruta_icono):
        app.setWindowIcon(QIcon(ruta_icono_qt))
        
    splash = PantallaDeCarga()
    splash.show()
    
    hilo_cargador = HiloCargadorIndustrial()
    hilo_cargador.progreso_signal.connect(splash.actualizar_progreso)
    hilo_cargador.estatus_signal.connect(splash.actualizar_texto)
    
    def conmutar_a_interfaz_principal():
        # Aseguramos el CWD en la raíz del proceso principal antes de levantar nada
        os.chdir(ruta_raiz)
        
        splash.actualizar_texto("Sincronizando núcleo OpenTP...")
        splash.actualizar_progreso(95)
        
        # Procesamos los eventos para que el usuario vea el texto de arriba antes del bache
        QCoreApplication.processEvents()
        
        # Importación e instanciación segura en el Main Thread (mismo CWD de siempre)
        from gui.main_window import MainWindow
        
        global ventana_activa
        ventana_activa = MainWindow()
        
        splash.actualizar_progreso(100)
        QCoreApplication.processEvents()
        time.sleep(0.1)
        
        # Mostrar el robot e interactuar de inmediato
        ventana_activa.show()
        splash.animacion_parpadeo.stop()
        splash.close()

    hilo_cargador.carga_completa_signal.connect(conmutar_a_interfaz_principal)
    hilo_cargador.start()  
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()