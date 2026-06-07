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
        
        # Historial para almacenar los últimos ángulos seguros (evitar atravesar el suelo)
        self.ultimos_angulos_seguros = []
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- COLUMNA IZQUIERDA: El Visor 3D ---
        self.viewer_3d = RobotViewer3D()
        main_layout.addWidget(self.viewer_3d, stretch=2)
        
        # --- COLUMNA DERECHA: Panel de Control ---
        controles_widget = QWidget()
        controles_layout = QVBoxLayout(controles_widget)
        main_layout.addWidget(controles_widget, stretch=1)
        
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
        
        self.lbl_pos_x = QLabel("X: 0.00 mm")
        self.lbl_pos_y = QLabel("Y: 0.00 mm")
        self.lbl_pos_z = QLabel("Z: 0.00 mm")
        coord_layout.addWidget(self.lbl_pos_x)
        coord_layout.addWidget(self.lbl_pos_y)
        coord_layout.addWidget(self.lbl_pos_z)
        
        controles_layout.addWidget(panel_coordenadas)
        controles_layout.addSpacing(15)
        
        title_controles = QLabel("Control de Ejes (Jog)")
        title_controles.setStyleSheet("font-size: 16px; font-weight: bold;")
        controles_layout.addWidget(title_controles)
        
        btn_home_general = QPushButton("Resetear Todo a 0° (Home Animado)")
        btn_home_general.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold; padding: 5px; border-radius: 5px;")
        btn_home_general.clicked.connect(self.home_general_animado)
        controles_layout.addWidget(btn_home_general)
        
        self.sliders = []
        
        if self.viewer_3d.chain:
            contador_ejes = 1
            num_totales = len(self.viewer_3d.chain.links)
            self.ultimos_angulos_seguros = [0.0] * num_totales
            
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
                
                eje_header_layout = QHBoxLayout()
                label = QLabel(f"{nombre_eje}: 0°")
                eje_header_layout.addWidget(label)
                
                btn_reset_individual = QPushButton("0°")
                btn_reset_individual.setFixedWidth(35)
                btn_reset_individual.setStyleSheet("background-color: #44475a; color: white; border-radius: 3px; font-size: 11px;")
                
                controles_layout.addLayout(eje_header_layout)
                
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(limite_min_deg, limite_max_deg)
                slider.setValue(0)
                slider.setProperty("joint_index", i)
                slider.setProperty("nombre_limpio", nombre_eje)
                
                # Bloqueamos temporalmente señales durante el setup
                slider.blockSignals(True)
                slider.valueChanged.connect(self.slider_movido)
                slider.blockSignals(False)
                
                btn_reset_individual.clicked.connect(lambda checked=False, s=slider: self.animar_slider_a_cero(s))
                eje_header_layout.addWidget(btn_reset_individual)
                
                controles_layout.addWidget(slider)
                self.sliders.append((slider, label, i))
                contador_ejes += 1
            
        controles_layout.addStretch()
        self.calcular_coordenadas_rectangulares()

    def slider_movido(self):
        if not self.viewer_3d.chain:
            return
            
        num_totales = len(self.viewer_3d.chain.links)
        angulos_radianes = [0.0] * num_totales
        
        # 1. Almacenamos temporalmente los ángulos que el usuario quiere setear
        for slider, _, joint_index in self.sliders:
            angulos_radianes[joint_index] = np.radians(slider.value())
            
        # 2. SISTEMA ANTICOLISIÓN SUELO: Validamos mediante Cinemática Directa ANTES de dibujar
        matriz_homogena = self.viewer_3d.chain.forward_kinematics(angulos_radianes)
        z_futura_mm = matriz_homogena[2, 3] * 1000
        
        # Si la punta del robot baja de 15 mm respecto al piso, bloqueamos el movimiento
        if z_futura_mm < 15.0:
            # Revertimos los sliders a la última posición segura conocida sin disparar bucles de señales
            for slider, label, joint_index in self.sliders:
                slider.blockSignals(True)
                grado_seguro = int(np.degrees(self.ultimos_angulos_seguros[joint_index]))
                slider.setValue(grado_seguro)
                nombre_eje = slider.property("nombre_limpio")
                label.setText(f"{nombre_eje}: {grado_seguro}°")
                slider.blockSignals(False)
            return # Detenemos la ejecución. No se actualiza el entorno 3D.
            
        # 3. Si pasó la validación del suelo, guardamos esta configuración como segura
        self.ultimos_angulos_seguros = list(angulos_radianes)
        
        # 4. Actualizamos textos y entorno gráfico con total normalidad
        for slider, label, joint_index in self.sliders:
            grados = slider.value()
            nombre_eje = slider.property("nombre_limpio")
            label.setText(f"{nombre_eje}: {grados}°")
            
        self.viewer_3d.actualizar_posicion_visual(angulos_radianes)
        self.calcular_coordenadas_rectangulares()

    # --- SISTEMA DE ANIMACIÓN SUAVE PARA HOME ---
    def animar_slider_a_cero(self, slider):
        """Crea una interpolación de movimiento para llevar un slider individual a 0°."""
        anim = QVariantAnimation(self)
        anim.setDuration(500) # Duración de medio segundo
        anim.setStartValue(slider.value())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutCubic) # Aceleración y desaceleración orgánica
        
        # En cada paso de la animación, actualizamos el valor físico del slider
        anim.valueChanged.connect(slider.setValue)
        anim.start()
        # Mantenemos una referencia de la animación para evitar que recolectores de basura la destruyan
        slider.setProperty("animacion_activa", anim)

    def home_general_animado(self):
        """Lanza animaciones simultáneas en todos los ejes para regresar ordenadamente a Home."""
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
        x_mm = matriz_homogena[0, 3] * 1000
        y_mm = matriz_homogena[1, 3] * 1000
        z_mm = matriz_homogena[2, 3] * 1000
        
        self.lbl_pos_x.setText(f"X: {x_mm:.2f} mm")
        self.lbl_pos_y.setText(f"Y: {y_mm:.2f} mm")
        self.lbl_pos_z.setText(f"Z: {z_mm:.2f} mm")