from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QPushButton
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QIcon
from gui.widgets_3d import RobotViewer3D
import numpy as np
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenTP Simulator - FANUC M-900iA [UPIITA]")
        self.resize(1200, 800)
        
        self.ultimos_angulos_seguros = []
        self.sliders = []
        
        # Layout principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- COLUMNA IZQUIERDA: Visor 3D ---
        self.viewer_3d = RobotViewer3D()
        main_layout.addWidget(self.viewer_3d, stretch=2)
        
        # --- COLUMNA DERECHA: Panel de Controles ---
        self.controles_widget = QWidget()
        self.controles_layout = QVBoxLayout(self.controles_widget)
        main_layout.addWidget(self.controles_widget, stretch=1)
        
        # Panel de Coordenadas Rectangulares
        panel_coordenadas = QWidget()
        panel_coordenadas.setStyleSheet("""
            QWidget { background-color: #2a2a3a; border-radius: 10px; }
            QLabel { color: #ffffff; font-family: 'Consolas', monospace; font-size: 13px; }
        """)
        coord_layout = QVBoxLayout(panel_coordenadas)
        
        title_coords = QLabel("Posición Cartesiana (TCP)")
        title_coords.setStyleSheet("font-size: 14px; font-weight: bold; color: #50fa7b; background: transparent;")
        coord_layout.addWidget(title_coords)
        
        self.lbl_pos_x = QLabel("X: --- mm")
        self.lbl_pos_y = QLabel("Y: --- mm")
        self.lbl_pos_z = QLabel("Z: --- mm")
        coord_layout.addWidget(self.lbl_pos_x)
        coord_layout.addWidget(self.lbl_pos_y)
        coord_layout.addWidget(self.lbl_pos_z)
        self.controles_layout.addWidget(panel_coordenadas)
        self.controles_layout.addSpacing(15)
        
        # Título de Jogging
        self.title_controles = QLabel("Control de Ejes (Jog)")
        self.title_controles.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.controles_layout.addWidget(self.title_controles)
        
        # Botón de Home General
        self.btn_home_general = QPushButton("Resetear Todo a 0° (Home Animado)")
        self.btn_home_general.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold; padding: 5px; border-radius: 5px;")
        self.btn_home_general.setEnabled(False) # Inactivo hasta que cargue el robot
        self.btn_home_general.clicked.connect(self.home_general_animado)
        self.controles_layout.addWidget(self.btn_home_general)
        
        # CONEXIÓN ASÍNCRONA VITAL: Cuando el visor 3D termine, creamos los sliders
        self.viewer_3d.robot_listo_interfaz.connect(self.construir_sliders_dinamicos)
        self.controles_layout.addStretch()

    def construir_sliders_dinamicos(self):
        """Construye las barras de jogging de forma asíncrona tras finalizar la carga en segundo plano."""
        if not self.viewer_3d.chain:
            return
            
        # Remover el stretch temporal inferior para insertar los controles ordenadamente
        self.controles_layout.takeAt(self.controles_layout.count() - 1)
        
        contador_ejes = 1
        num_totales = len(self.viewer_3d.chain.links)
        self.ultimos_angulos_seguros = [0.0] * num_totales
        
        for i, link in enumerate(self.viewer_3d.chain.links):
            name_lower = link.name.lower()
            if "base" in name_lower or "flange" in name_lower or "tool" in name_lower or "world" in name_lower:
                continue
                
            limite_min_deg, limite_max_deg = (-180, 180)
            if link.bounds is not None:
                limite_min_deg = int(np.degrees(link.bounds[0]))
                limite_max_deg = int(np.degrees(link.bounds[1]))
            
            nombre_eje = f"Eje joint_{contador_ejes}"
            eje_header_layout = QHBoxLayout()
            label = QLabel(f"{nombre_eje}: 0°")
            eje_header_layout.addWidget(label)
            
            btn_reset_individual = QPushButton("0°")
            btn_reset_individual.setFixedWidth(35)
            btn_reset_individual.setStyleSheet("background-color: #44475a; color: white; border-radius: 3px; font-size: 11px;")
            
            self.controles_layout.addLayout(eje_header_layout)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(limite_min_deg, limite_max_deg)
            slider.setValue(0)
            slider.setProperty("joint_index", i)
            slider.setProperty("nombre_limpio", nombre_eje)
            
            slider.valueChanged.connect(self.slider_movido)
            btn_reset_individual.clicked.connect(lambda checked=False, s=slider: self.animar_slider_a_cero(s))
            eje_header_layout.addWidget(btn_reset_individual)
            
            self.controles_layout.addWidget(slider)
            self.sliders.append((slider, label, i))
            contador_ejes += 1
            
        self.controles_layout.addStretch()
        self.btn_home_general.setEnabled(True)
        self.calcular_coordenadas_rectangulares()

    def slider_movido(self):
        if not self.viewer_3d.chain:
            return
        num_totales = len(self.viewer_3d.chain.links)
        angulos_radianes = [0.0] * num_totales
        for slider, _, joint_index in self.sliders:
            angulos_radianes[joint_index] = np.radians(slider.value())
            
        matriz_homogena = self.viewer_3d.chain.forward_kinematics(angulos_radianes)
        z_futura_mm = matriz_homogena[2, 3] * 1000
        
        if z_futura_mm < 15.0:
            for slider, label, joint_index in self.sliders:
                slider.blockSignals(True)
                grado_seguro = int(np.degrees(self.ultimos_angulos_seguros[joint_index]))
                slider.setValue(grado_seguro)
                label.setText(f"{slider.property('nombre_limpio')}: {grado_seguro}°")
                slider.blockSignals(False)
            return
            
        self.ultimos_angulos_seguros = list(angulos_radianes)
        for slider, label, joint_index in self.sliders:
            label.setText(f"{slider.property('nombre_limpio')}: {slider.value()}°")
            
        self.viewer_3d.actualizar_posicion_visual(angulos_radianes)
        self.calcular_coordenadas_rectangulares()

    def animar_slider_a_cero(self, slider):
        anim = QVariantAnimation(self)
        anim.setDuration(500)
        anim.setStartValue(slider.value())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.valueChanged.connect(slider.setValue)
        anim.start()
        slider.setProperty("animacion_activa", anim)

    def home_general_animado(self):
        for slider, _, _ in self.sliders:
            self.animar_slider_a_cero(slider)

    def calcular_coordenadas_rectangulares(self):
        if not self.viewer_3d.chain:
            return
        num_totales = len(self.viewer_3d.chain.links)
        angulos_actuales = [0.0] * num_totales
        for slider, _, joint_index in self.sliders:
            angulos_actuales[joint_index] = np.radians(slider.value())
            
        matriz_homogena = self.viewer_3d.chain.forward_kinematics(angulos_actuales)
        self.lbl_pos_x.setText(f"X: {matriz_homogena[0, 3] * 1000:.2f} mm")
        self.lbl_pos_y.setText(f"Y: {matriz_homogena[1, 3] * 1000:.2f} mm")
        self.lbl_pos_z.setText(f"Z: {matriz_homogena[2, 3] * 1000:.2f} mm")