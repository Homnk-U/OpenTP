from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from gui.widgets_3d import RobotViewer3D
import numpy as np
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenTP Simulator - FANUC M-900iA [UPIITA]")
        self.resize(1200, 800) # Ampliado un poco para que quepan bien las coordenadas
        
        # Widget y Layout principal (Horizontal)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- COLUMNA IZQUIERDA: El Visor 3D ---
        self.viewer_3d = RobotViewer3D()
        main_layout.addWidget(self.viewer_3d, stretch=2)
        
        # --- COLUMNA DERECHA: Panel de Control Completo ---
        controles_widget = QWidget()
        controles_layout = QVBoxLayout(controles_widget)
        main_layout.addWidget(controles_widget, stretch=1)
        
        # 1. Subpanel de Coordenadas Rectangulares (X, Y, Z)
        panel_coordenadas = QWidget()
        panel_coordenadas.setStyleSheet("""
            QWidget {
                background-color: #2a2a3a;
                border-radius: 10px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
        """)
        coord_layout = QVBoxLayout(panel_coordenadas)
        
        title_coords = QLabel("Posición Cartesiana (TCP)")
        title_coords.setStyleSheet("font-size: 14px; font-weight: bold; color: #50fa7b; background: transparent;")
        coord_layout.addWidget(title_coords)
        
        # Labels para mostrar las coordenadas rectangulares
        self.lbl_pos_x = QLabel("X: 0.00 mm")
        self.lbl_pos_y = QLabel("Y: 0.00 mm")
        self.lbl_pos_z = QLabel("Z: 0.00 mm")
        coord_layout.addWidget(self.lbl_pos_x)
        coord_layout.addWidget(self.lbl_pos_y)
        coord_layout.addWidget(self.lbl_pos_z)
        
        controles_layout.addWidget(panel_coordenadas)
        
        # Espaciador
        controles_layout.addSpacing(15)
        
        # 2. Título de Controles Jog
        title_controles = QLabel("Control de Ejes (Jog)")
        title_controles.setStyleSheet("font-size: 16px; font-weight: bold;")
        controles_layout.addWidget(title_controles)
        
        # Botón para resetear TODOS los ejes a la vez
        btn_home_general = QPushButton("Resetear Todo a 0° (Home)")
        btn_home_general.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold; padding: 5px; border-radius: 5px;")
        btn_home_general.clicked.connect(self.home_general)
        controles_layout.addWidget(btn_home_general)
        
        self.sliders = []
        
        if self.viewer_3d.chain:
            contador_ejes = 1
            
            for i, link in enumerate(self.viewer_3d.chain.links):
                name_lower = link.name.lower()
                
                if "base" in name_lower or "flange" in name_lower or "tool" in name_lower or "world" in name_lower:
                    continue
                
                if link.bounds is not None:
                    limite_min_deg = int(np.degrees(link.bounds[0]))
                    limite_max_deg = int(np.degrees(link.bounds[1]))
                else:
                    limite_min_deg = -180
                    limite_max_deg = 180
                
                nombre_eje = f"Eje joint_{contador_ejes}"
                
                # Layout horizontal para la etiqueta del eje y su botón Reset individual
                eje_header_layout = QHBoxLayout()
                label = QLabel(f"{nombre_eje}: 0°")
                eje_header_layout.addWidget(label)
                
                # Botón individual de reset a 0°
                btn_reset_individual = QPushButton("0°")
                btn_reset_individual.setFixedWidth(35)
                btn_reset_individual.setStyleSheet("background-color: #44475a; color: white; border-radius: 3px; font-size: 11px;")
                
                # Truco de Python: pasamos el slider actual como argumento por defecto al clickear
                controles_layout.addLayout(eje_header_layout)
                
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(limite_min_deg, limite_max_deg)
                slider.setValue(0)
                slider.setProperty("joint_index", i)
                slider.setProperty("nombre_limpio", nombre_eje)
                slider.valueChanged.connect(self.slider_movido)
                
                # Conectamos el botón para que ponga el slider en cero
                btn_reset_individual.clicked.connect(lambda checked=False, s=slider: s.setValue(0))
                eje_header_layout.addWidget(btn_reset_individual)
                
                controles_layout.addWidget(slider)
                self.sliders.append((slider, label, i))
                contador_ejes += 1
            
        controles_layout.addStretch()
        # Calcular coordenadas iniciales al abrir la app
        self.calcular_coordenadas_rectangulares()

    def slider_movido(self):
        if not self.viewer_3d.chain:
            return
            
        num_totales = len(self.viewer_3d.chain.links)
        angulos_radianes = [0.0] * num_totales
        
        for slider, label, joint_index in self.sliders:
            grados = slider.value()
            nombre_eje = slider.property("nombre_limpio")
            label.setText(f"{nombre_eje}: {grados}°")
            angulos_radianes[joint_index] = np.radians(grados)
            
        # Refrescar visualizador 3D
        self.viewer_3d.actualizar_posicion_visual(angulos_radianes)
        
        # REFRESCAR COORDENADAS RECTANGULARES (X, Y, Z)
        self.calcular_coordenadas_rectangulares()

    def home_general(self):
        """Pone absolutamente todos los sliders activos en 0 grados."""
        for slider, _, _ in self.sliders:
            slider.setValue(0)

    def calcular_coordenadas_rectangulares(self):
        """Utiliza la Cinemática Directa de IKPy para obtener la posición de la herramienta."""
        if not self.viewer_3d.chain:
            return
            
        # 1. Obtener los ángulos actuales en radianes directos de los sliders
        num_totales = len(self.viewer_3d.chain.links)
        angulos_actuales = [0.0] * num_totales
        for slider, _, joint_index in self.sliders:
            angulos_actuales[joint_index] = np.radians(slider.value())
            
        # 2. IKPy calcula la Matriz de Transformación Homogénea del último eslabón (TCP)
        # forward_kinematics() devuelve una matriz de 4x4
        matriz_homogena = self.viewer_3d.chain.forward_kinematics(angulos_actuales)
        
        # La posición X, Y, Z se encuentra siempre en la última columna de la matriz:
        # matriz[0,3] = X, matriz[1,3] = Y, matriz[2,3] = Z
        # Las unidades del URDF suelen estar en metros, multiplicamos por 1000 para mostrarlas en mm
        x_mm = matriz_homogena[0, 3] * 1000
        y_mm = matriz_homogena[1, 3] * 1000
        z_mm = matriz_homogena[2, 3] * 1000
        
        # 3. Actualizamos las etiquetas de la interfaz con dos decimales
        self.lbl_pos_x.setText(f"X: {x_mm:.2f} mm")
        self.lbl_pos_y.setText(f"Y: {y_mm:.2f} mm")
        self.lbl_pos_z.setText(f"Z: {z_mm:.2f} mm")