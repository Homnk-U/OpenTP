import numpy as np
from functools import partial
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGroupBox, QLabel, QTextEdit, QCheckBox
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from gui.widgets_3d import RobotViewer3D
from core.tp_compiler import TPCompiler

class PanelControlIndustrial(QWidget):
    def __init__(self, viewer_3d, parent=None):
        super().__init__(parent)
        self.viewer_3d = viewer_3d 
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(4, 4, 4, 4)
        layout_principal.setSpacing(6)
        
        # VARIABLES DE ESTADO INDUSTRIAL
        self.override = 50          # Override por defecto al 50%
        self.mostrar_eje_world = True
        self.mostrar_eje_tcp = True
        
        self.current_angles_deg = [0.0] * 6 
        self.deadman_activo = False 
        self.ultimos_angulos_seguros = list(self.current_angles_deg)
        self.animacion_movimiento = None
        self.compilador = TPCompiler()
        self.siguiente_id_punto = 1 
        
        estilo_botones_industrial = """
            QPushButton { background-color: #333333; color: white; font-weight: bold; font-size: 11px; padding: 4px; border: 1px solid #1a1a1a; border-radius: 3px; }
            QPushButton:pressed { background-color: #28a745; }
            QPushButton:disabled { background-color: #222222; color: #444444; border: 1px solid #111; }
        """

        # ==========================================
        # 1. MONITOR DE ALARMAS, COORDENADAS Y OVERRIDE
        # ==========================================
        group_posicion = QGroupBox("Avisos y Sistema (TCP)")
        group_posicion.setStyleSheet("QGroupBox { font-weight: bold; color: #50fa7b; }")
        layout_posicion_v = QVBoxLayout(group_posicion)
        layout_posicion_v.setContentsMargins(5, 5, 5, 5)
        layout_posicion_v.setSpacing(4)
        
        # Fila Alarma
        fila_alarma_layout = QHBoxLayout()
        lbl_titulo_sub = QLabel("Estatus:")
        lbl_titulo_sub.setStyleSheet("color: #aaa; font-size: 11px;")
        self.lbl_alarma = QLabel("SISTEMA OK")
        self.lbl_alarma.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_alarma.setStyleSheet("QLabel { background-color: #1e7e34; color: white; font-weight: bold; font-family: 'Consolas'; font-size: 11px; padding: 3px 6px; border-radius: 4px; }")
        fila_alarma_layout.addWidget(lbl_titulo_sub)
        fila_alarma_layout.addWidget(self.lbl_alarma, stretch=1)
        layout_posicion_v.addLayout(fila_alarma_layout)
        
        # SECCIÓN DE CONTROL OVERRIDE DE VELOCIDAD
        fila_override = QHBoxLayout()
        lbl_ovr_title = QLabel("OVERRIDE:")
        lbl_ovr_title.setStyleSheet("color: #ffb86c; font-weight: bold; font-size: 11px;")
        
        self.lbl_override_val = QLabel(f"{self.override}%")
        self.lbl_override_val.setStyleSheet("color: white; font-family: 'Consolas'; font-weight: bold; font-size: 12px;")
        
        btn_ovr_menos = QPushButton("-")
        btn_ovr_mas = QPushButton("+")
        btn_ovr_menos.setFixedSize(22, 18)
        btn_ovr_mas.setFixedSize(22, 18)
        btn_ovr_menos.setStyleSheet("background-color: #444; color: white; font-weight: bold; border-radius: 2px;")
        btn_ovr_mas.setStyleSheet("background-color: #444; color: white; font-weight: bold; border-radius: 2px;")
        
        btn_ovr_menos.clicked.connect(lambda: self.cambiar_override(-5))
        btn_ovr_mas.clicked.connect(lambda: self.cambiar_override(5))
        
        fila_override.addWidget(lbl_ovr_title)
        fila_override.addWidget(self.lbl_override_val)
        fila_override.addWidget(btn_ovr_menos)
        fila_override.addWidget(btn_ovr_mas)
        layout_posicion_v.addLayout(fila_override)
        
        # Coordenadas XYZ
        fila_coords_layout = QHBoxLayout()
        self.lbl_x = QLabel("X: -- mm")
        self.lbl_y = QLabel("Y: -- mm")
        self.lbl_z = QLabel("Z: -- mm")
        for lbl in [self.lbl_x, self.lbl_y, self.lbl_z]:
            lbl.setStyleSheet("font-family: 'Consolas'; font-size: 11px; color: #fff; font-weight: bold;")
            fila_coords_layout.addWidget(lbl)
        layout_posicion_v.addLayout(fila_coords_layout)
        layout_principal.addWidget(group_posicion)

        # ==========================================
        # 2. CONFIGURACIÓN VISUAL / EJES
        # ==========================================
        group_visual = QGroupBox("Marcos de Referencia (Ejes)")
        group_visual.setStyleSheet("QGroupBox { font-weight: bold; color: #8be9fd; }")
        layout_visual = QHBoxLayout(group_visual)
        layout_visual.setContentsMargins(4, 4, 4, 4)
        
        self.chk_eje_world = QCheckBox("Origen (World)")
        self.chk_eje_tcp = QCheckBox("Gripper (Tool)")
        self.chk_eje_world.setChecked(True)
        self.chk_eje_tcp.setChecked(True)
        
        style_chk = "QCheckBox { color: #eee; font-size: 10px; } QCheckBox::indicator { width: 10px; height: 10px; }"
        self.chk_eje_world.setStyleSheet(style_chk)
        self.chk_eje_tcp.setStyleSheet(style_chk)
        
        self.chk_eje_world.stateChanged.connect(self.actualizar_visibilidad_ejes)
        self.chk_eje_tcp.stateChanged.connect(self.actualizar_visibilidad_ejes)
        
        layout_visual.addWidget(self.chk_eje_world)
        layout_visual.addWidget(self.chk_eje_tcp)
        layout_principal.addWidget(group_visual)

        # ==========================================
        # 3. PROGRAMA TP (EDITOR)
        # ==========================================
        group_editor = QGroupBox("Programa TP")
        group_editor.setStyleSheet("QGroupBox { font-weight: bold; color: #ff79c6; }")
        layout_editor = QVBoxLayout(group_editor)
        layout_editor.setContentsMargins(5, 5, 5, 5)
        self.txt_editor = QTextEdit()
        self.txt_editor.setPlaceholderText("Ejemplo:\nJ P[1] 100% FINE")
        self.txt_editor.setFixedHeight(75) 
        layout_editor.addWidget(self.txt_editor)
        self.btn_ejecutar = QPushButton("▶ EJECUTAR PROGRAMA (F3)")
        self.btn_ejecutar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 5px; font-size: 11px;")
        self.btn_ejecutar.clicked.connect(self.iniciar_secuencia_programa)
        layout_editor.addWidget(self.btn_ejecutar)
        layout_principal.addWidget(group_editor)

        # ==========================================
        # 4. ZONA INFERIOR FUSIONADA (COLUMNAS JOG + AUXILIAR)
        # ==========================================
        layout_columnas_aux = QHBoxLayout()
        layout_columnas_aux.setSpacing(6)

        # Columna Izquierda: Jog Manual Mini
        group_jog = QGroupBox("Jog Manual")
        layout_jog = QVBoxLayout(group_jog)
        layout_jog.setContentsMargins(4, 4, 4, 4)
        grid_ejes = QGridLayout()
        grid_ejes.setSpacing(2)
        
        ejes_labels = ["J1", "J2", "J3", "J4", "J5", "J6"]
        self.botones_jog = []
        for idx, nombre in enumerate(ejes_labels):
            lbl = QLabel(nombre) 
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 10px; color: #bbb; font-weight: bold;")
            grid_ejes.addWidget(lbl, idx, 1)
            
            btn_menos = QPushButton("-")
            btn_mas = QPushButton("+")
            btn_menos.setFixedSize(25, 19)
            btn_mas.setFixedSize(25, 19)
            btn_menos.setAutoRepeat(True)
            btn_menos.setAutoRepeatDelay(200)   
            btn_menos.setAutoRepeatInterval(40)  
            btn_mas.setAutoRepeat(True)
            btn_mas.setAutoRepeatDelay(200)
            btn_mas.setAutoRepeatInterval(40)
            btn_menos.setStyleSheet(estilo_botones_industrial)
            btn_mas.setStyleSheet(estilo_botones_industrial)
            
            limites = [180, 75, 120, 360, 125, 360]
            btn_menos.clicked.connect(partial(self.jog_eje, idx, -1.0, limites[idx])) 
            btn_mas.clicked.connect(partial(self.jog_eje, idx, 1.0, limites[idx]))
            grid_ejes.addWidget(btn_menos, idx, 0)
            grid_ejes.addWidget(btn_mas, idx, 2)
            self.botones_jog.extend([btn_menos, btn_mas])
        layout_jog.addLayout(grid_ejes)
        layout_columnas_aux.addWidget(group_jog, stretch=1)

        # Columna Derecha: Auxiliares
        panel_derecho_inputs = QWidget()
        layout_inputs_v = QVBoxLayout(panel_derecho_inputs)
        layout_inputs_v.setContentsMargins(0, 0, 0, 0)
        layout_inputs_v.setSpacing(4)

        self.btn_home = QPushButton("IR A HOME")
        self.btn_home.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 5px; font-size: 10px;")
        self.btn_home.clicked.connect(self.mover_a_home_animado)
        layout_inputs_v.addWidget(self.btn_home)
        
        group_teach = QGroupBox("Teach")
        # CORRECCIÓN DE ERROR CSS: Estilo directo al widget contenedor QGroupBox
        group_teach.setStyleSheet("QGroupBox { font-weight: bold; color: #fff; }")
        layout_teach = QVBoxLayout(group_teach)
        layout_teach.setContentsMargins(4, 4, 4, 4)
        self.btn_grab = QPushButton("Grabar P[1]")
        self.btn_grab.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 4px; font-size: 10px;")
        self.btn_grab.clicked.connect(self.grabar_posicion_actual)
        layout_teach.addWidget(self.btn_grab)
        layout_inputs_v.addWidget(group_teach)
        
        group_di = QGroupBox("DI (Digital Inputs)")
        group_di.setStyleSheet("QGroupBox { font-weight: bold; color: #fff; }")
        grid_di = QGridLayout(group_di)
        grid_di.setContentsMargins(4, 4, 4, 4)
        grid_di.setSpacing(3)
        for i in range(8):  # Se extiende a los 8 botones de tu interfaz física
            btn_di = QPushButton(f"{i+1}")
            btn_di.setFixedSize(20, 18)
            btn_di.setStyleSheet("font-size: 9px; background-color: #444; color: white; border-radius: 2px; font-weight: bold;")
            grid_di.addWidget(btn_di, i // 4, i % 4)
        layout_inputs_v.addWidget(group_di)
        
        layout_columnas_aux.addWidget(panel_derecho_inputs, stretch=1)
        layout_principal.addLayout(layout_columnas_aux)
        
        # Deadman Status Bar
        self.lbl_status_deadman = QLabel("Deadman Switch")
        self.lbl_status_deadman.setFixedHeight(20)
        self.lbl_status_deadman.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self.lbl_status_deadman)

        self.actualizar_interfaz_por_deadman()
        self.actualizar_robot_y_tcp()

    # --- MÉTODOS DE COMPORTAMIENTO INDUSTRIAL ---
    def cambiar_override(self, incremento):
        self.override = max(5, min(100, self.override + incremento))
        self.lbl_override_val.setText(f"{self.override}%")

    def actualizar_visibilidad_ejes(self):
        origen = self.chk_eje_world.isChecked()
        gripper = self.chk_eje_tcp.isChecked()
        self.viewer_3d.alternar_visibilidad_ejes(origen, gripper)

    # NUEVO MÉTODO CORREGIDO: Guarda las posiciones en el compilador TP
    def grabar_posicion_actual(self):
        if not self.deadman_activo:
            return
        self.compilador.guardar_punto(self.siguiente_id_punto, self.current_angles_deg)
        
        # Escribe automáticamente la instrucción en el editor
        texto_actual = self.txt_editor.toPlainText()
        nueva_linea = f"J P[{self.siguiente_id_punto}] 100% FINE"
        if texto_actual.strip():
            self.txt_editor.setText(f"{texto_actual}\n{nueva_linea}")
        else:
            self.txt_editor.setText(nueva_linea)
            
        self.siguiente_id_punto += 1
        self.btn_grab.setText(f"Grabar P[{self.siguiente_id_punto}]")

    def jog_eje(self, joint_idx, delta_deg, limite_max):
        if not self.deadman_activo:
            return
        paso_escalado = delta_deg * (self.override / 100.0)
        nuevo_angulo = self.current_angles_deg[joint_idx] + paso_escalado
        if abs(nuevo_angulo) > limite_max:
            return
        self.current_angles_deg[joint_idx] = nuevo_angulo
        self.actualizar_robot_y_tcp()

    def mover_a_home_animado(self):
        if not self.deadman_activo:
            return
        duracion_base = 1200
        duracion_ajustada = int(duracion_base * (100.0 / self.override))

        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(duracion_ajustada) 
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.setEasingCurve(QEasingCurve.Type.InOutCubic) 
        
        angulos_inicio = list(self.current_angles_deg)
        def interpolar_home(t):
            if not self.deadman_activo:
                self.animacion_movimiento.stop()
                return
            for i in range(6):
                distancia = 0.0 - angulos_inicio[i]
                self.current_angles_deg[i] = angulos_inicio[i] + (t * distancia)
            self.actualizar_robot_y_tcp()
            
        self.animacion_movimiento.valueChanged.connect(interpolar_home)
        self.animacion_movimiento.start()

    def actualizar_robot_y_tcp(self):
        if not self.viewer_3d.chain:
            return
        angulos_rad = np.radians(self.current_angles_deg)
        vector_full = [0.0] * len(self.viewer_3d.chain.links)
        vector_full[1:7] = angulos_rad

        matriz_homogena = self.viewer_3d.chain.forward_kinematics(vector_full)
        x_mm = matriz_homogena[0, 3] * 1000
        y_mm = matriz_homogena[1, 3] * 1000
        z_mm = matriz_homogena[2, 3] * 1000

        if z_mm < 15.0: 
            self.lbl_alarma.setText("⚠️ ALARMA SUELO")
            self.lbl_alarma.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; font-family: 'Consolas'; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            if self.animacion_movimiento and self.animacion_movimiento.state() == QVariantAnimation.State.Running:
                self.animacion_movimiento.stop()
            self.current_angles_deg = list(self.ultimos_angulos_seguros)
            return 
            
        self.lbl_alarma.setText("SISTEMA OK")
        self.lbl_alarma.setStyleSheet("background-color: #1e7e34; color: white; font-weight: bold; font-family: 'Consolas'; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        self.ultimos_angulos_seguros = list(self.current_angles_deg)

        self.viewer_3d.actualizar_posicion_visual(vector_full)
        self.lbl_x.setText(f"X: {x_mm:.2f}")
        self.lbl_y.setText(f"Y: {y_mm:.2f}")
        self.lbl_z.setText(f"Z: {z_mm:.2f}")

    def actualizar_estado_deadman(self, activo):
        self.deadman_activo = activo
        self.actualizar_interfaz_por_deadman()
        if not activo and self.animacion_movimiento:
            self.animacion_movimiento.stop()

    def actualizar_interfaz_por_deadman(self):
        for btn in self.botones_jog:
            btn.setEnabled(self.deadman_activo)
        self.btn_home.setEnabled(self.deadman_activo)
        self.btn_grab.setEnabled(self.deadman_activo)
        self.btn_ejecutar.setEnabled(self.deadman_activo)
        
        if self.deadman_activo:
            self.lbl_status_deadman.setText("DEADMAN ENERGIZADO (FALTA ACCIÓN)")
            self.lbl_status_deadman.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; font-size: 10px;")
        else:
            self.lbl_status_deadman.setText("ERROR: PRESIONA SHIFT (DEADMAN)")
            self.lbl_status_deadman.setStyleSheet("background-color: #555555; color: #ff6b6b; font-weight: bold; font-size: 10px;")

    def iniciar_secuencia_programa(self):
        if not self.deadman_activo:
            return
        texto_programa = self.txt_editor.toPlainText().strip().split('\n')
        if not texto_programa or texto_programa == ['']:
            return
        self.lineas_a_ejecutar = []
        for linea in texto_programa:
            partes = linea.split()
            if len(partes) >= 2:
                nombre_punto = partes[1]
                valores_articulares = self.compilador.obtener_punto(nombre_punto)
                if valores_articulares is not None:
                    self.lineas_a_ejecutar.append(valores_articulares)
        if not self.lineas_a_ejecutar:
            return
        self.indice_linea_actual = 0
        self._procesar_siguiente_linea()

    def _procesar_siguiente_linea(self):
        if not self.deadman_activo or self.indice_linea_actual >= len(self.lineas_a_ejecutar):
            return
        punto_destino = self.lineas_a_ejecutar[self.indice_linea_actual]
        
        duracion_base = 1500
        duracion_ajustada = int(duracion_base * (100.0 / self.override))

        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(duracion_ajustada)
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        angulos_inicio = list(self.current_angles_deg)
        def interpolar_valores(t):
            if not self.deadman_activo:
                self.animacion_movimiento.stop()
                return
            for i in range(6):
                distancia = punto_destino[i] - angulos_inicio[i]
                self.current_angles_deg[i] = angulos_inicio[i] + (t * distancia)
            self.actualizar_robot_y_tcp()
            
        self.animacion_movimiento.valueChanged.connect(interpolar_valores)
        def al_finalizar():
            self.indice_linea_actual += 1
            self._procesar_siguiente_linea()
        self.animacion_movimiento.finished.connect(al_finalizar)
        self.animacion_movimiento.start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenTP Simulator - FANUC M-900iA")
        self.resize(1200, 750)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QHBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        self.visor_3d = RobotViewer3D()
        layout_principal.addWidget(self.visor_3d, stretch=3) 
        self.panel_control = PanelControlIndustrial(viewer_3d=self.visor_3d) 
        layout_principal.addWidget(self.panel_control, stretch=1)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self.panel_control.actualizar_estado_deadman(True)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self.panel_control.actualizar_estado_deadman(False)
        super().keyReleaseEvent(event)