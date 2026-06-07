from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel
from PySide6.QtCore import Qt
from gui.widgets_3d import RobotViewer3D
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenTP Simulator - FANUC M-900iA [UPIITA]")
        self.resize(1100, 700)
        
        # Widget y Layout principal (Horizontal: Izquierda 3D, Derecha Controles)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- COLUMNA IZQUIERDA: El Visor 3D ---
        self.viewer_3d = RobotViewer3D()
        main_layout.addWidget(self.viewer_3d, stretch=2) # Toma más espacio
        
        # --- COLUMNA DERECHA: Sliders de control (Jogging) ---
        controles_widget = QWidget()
        controles_layout = QVBoxLayout(controles_widget)
        main_layout.addWidget(controles_widget, stretch=1)
        
        title_controles = QLabel("Control de Ejes (Jog)")
        title_controles.setStyleSheet("font-size: 16px; font-weight: bold;")
        controles_layout.addWidget(title_controles)
        
        # Crear 6 sliders de prueba para mover las articulaciones
        self.sliders = []
        
        if self.viewer_3d.chain:
            for i, link in enumerate(self.viewer_3d.chain.links):
                # Convertimos el nombre a minúsculas para comparar fácil
                name_lower = link.name.lower()
                
                # FILTRO SEGURO POR NOMBRE: Saltamos los links fijos conocidos del URDF industrial
                if "base" in name_lower or "flange" in name_lower or "tool" in name_lower or "world" in name_lower:
                    continue
                
                # Nombre limpio en la interfaz: "joint_1" -> "Eje 1"
                nombre_limpio = link.name.replace("joint_", "Eje ")
                label = QLabel(f"{nombre_limpio}: 0°")
                controles_layout.addWidget(label)
                
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(-180, 180)
                slider.setValue(0)
                
                slider.setProperty("joint_index", i)
                slider.valueChanged.connect(self.slider_movido)
                
                controles_layout.addWidget(slider)
                self.sliders.append((slider, label, i))
            
        controles_layout.addStretch() # Empuja todo hacia arriba

    def slider_movido(self):
        if not self.viewer_3d.chain:
            return
            
        # Creamos una lista de ceros para todos los elementos del robot
        num_totales = len(self.viewer_3d.chain.links)
        angulos_radianes = [0.0] * num_totales
        
        # Solo llenamos los que corresponden a nuestros sliders activos
        for slider, label, joint_index in self.sliders:
            grados = slider.value()
            label.setText(f"Eje {self.viewer_3d.chain.links[joint_index].name}: {grados}°")
            angulos_radianes[joint_index] = np.radians(grados)
            
        # Refrescar el visualizador 3D
        self.viewer_3d.actualizar_posicion_visual(angulos_radianes)