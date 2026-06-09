import numpy as np
from functools import partial
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGroupBox, QLabel, QTextEdit
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
        
        self.current_angles_deg = [0.0] * 6 
        self.deadman_activo = False 
        self.ultimos_angulos_seguros = list(self.current_angles_deg)
        
        # Guardamos la referencia aquí para evitar que el Garbage Collector la borre
        self.animacion_movimiento = None
        
        # --- CEREBRO DEL COMPILADOR ---
        self.compilador = TPCompiler()
        self.siguiente_id_punto = 1 
        
        estilo_botones_industrial = """
            QPushButton { 
                background-color: #333333; color: white; 
                font-weight: bold; font-size: 11px;
                padding: 4px; border: 1px solid #1a1a1a; border-radius: 3px;
            }
            QPushButton:pressed { background-color: #28a745; }
            QPushButton:disabled { background-color: #222222; color: #444444; border: 1px solid #111; }
        """

        # ==========================================
        # 1. MONITOR DE ALARMAS Y COORDENADAS (ALTA PRIORIDAD)
        # ==========================================
        group_posicion = QGroupBox("Avisos y Sistema (TCP)")
        group_posicion.setStyleSheet("QGroupBox { font-weight: bold; color: #50fa7b; }")
        layout_posicion_v = QVBoxLayout(group_posicion)
        layout_posicion_v.setContentsMargins(6, 6, 6, 6)
        
        fila_alarma_layout = QHBoxLayout()
        lbl_titulo_sub = QLabel("Estatus:")
        lbl_titulo_sub.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.lbl_alarma = QLabel("SISTEMA OK")
        self.lbl_alarma.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_alarma.setStyleSheet("""
            QLabel {
                background-color: #1e7e34; color: white;
                font-weight: bold; font-family: 'Consolas';
                font-size: 11px; padding: 4px 8px; border-radius: 4px;
            }
        """)
        fila_alarma_layout.addWidget(lbl_titulo_sub)
        fila_alarma_layout.addWidget(self.lbl_alarma, stretch=1)
        layout_posicion_v.addLayout(fila_alarma_layout)
        
        fila_coords_layout = QHBoxLayout()
        self.lbl_x = QLabel("X: -- mm")
        self.lbl_y = QLabel("Y: -- mm")
        self.lbl_z = QLabel("Z: -- mm")
        
        for lbl in [self.lbl_x, self.lbl_y, self.lbl_z]:
            lbl.setStyleSheet("font-family: 'Consolas'; font-size: 12px; color: #fff; font-weight: bold;")
            fila_coords_layout.addWidget(lbl)
            
        layout_posicion_v.addLayout(fila_coords_layout)
        layout_principal.addWidget(group_posicion)

        # ==========================================
        # 2. PROGRAMA TP (EDITOR)
        # ==========================================
        group_editor = QGroupBox("Programa TP (Editor)")
        layout_editor = QVBoxLayout(group_editor)
        layout_editor.setContentsMargins(6, 6, 6, 6)
        
        self.txt_editor = QTextEdit()
        self.txt_editor.setPlaceholderText("Ejemplo:\nJ P[1] 100% FINE\nL P[2] 100% FINE")
        self.txt_editor.setFixedHeight(90) 
        layout_editor.addWidget(self.txt_editor)
        
        self.btn_ejecutar = QPushButton("▶ EJECUTAR PROGRAMA (F3)")
        self.btn_ejecutar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px; font-size: 11px;")
        self.btn_ejecutar.clicked.connect(self.iniciar_secuencia_programa)
        layout_editor.addWidget(self.btn_ejecutar)
        
        layout_principal.addWidget(group_editor)

        # ==========================================
        # 3. ZONA INFERIOR FUSIONADA (COLUMNA JOG + COLUMNA AUXILIAR)
        # ==========================================
        layout_columnas_aux = QHBoxLayout()
        layout_columnas_aux.setSpacing(6)

        # ---- COLUMNA IZQUIERDA: Jog Manual Mini ----
        group_jog = QGroupBox("Jog Manual")
        layout_jog = QVBoxLayout(group_jog)
        layout_jog.setContentsMargins(4, 4, 4, 4)
        layout_jog.setSpacing(4)
        
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
            
            btn_menos.setFixedSize(25, 20)
            btn_mas.setFixedSize(25, 20)
            
            btn_menos.setAutoRepeat(True)
            btn_menos.setAutoRepeatDelay(200)   
            btn_menos.setAutoRepeatInterval(40)  
            
            btn_mas.setAutoRepeat(True)
            btn_mas.setAutoRepeatDelay(200)
            btn_mas.setAutoRepeatInterval(40)
            
            btn_menos.setStyleSheet(estilo_botones_industrial)
            btn_mas.setStyleSheet(estilo_botones_industrial)
            
            # Límites originales del FANUC definidos por tu compañero
            limites = [180, 75, 120, 360, 125, 360]
            btn_menos.clicked.connect(partial(self.jog_eje, idx, -2.0, limites[idx])) 
            btn_mas.clicked.connect(partial(self.jog_eje, idx, 2.0, limites[idx]))
            
            grid_ejes.addWidget(btn_menos, idx, 0)
            grid_ejes.addWidget(btn_mas, idx, 2)
            
            self.botones_jog.extend([btn_menos, btn_mas])
            
        layout_jog.addLayout(grid_ejes)
        layout_columnas_aux.addWidget(group_jog, stretch=1)

        # ---- COLUMNA DERECHA: Home + Teach + DI ----
        panel_derecho_inputs = QWidget()
        layout_inputs_v = QVBoxLayout(panel_derecho_inputs)
        layout_inputs_v.setContentsMargins(0, 0, 0, 0)
        layout_inputs_v.setSpacing(4)

        # Botón HOME Cinemático
        self.btn_home = QPushButton("IR A HOME")
        self.btn_home.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 6px; font-size: 10px;")
        self.btn_home.clicked.connect(self.mover_a_home_animado)
        layout_inputs_v.addWidget(self.btn_home)
        
        group_teach = QGroupBox("Teach")
        layout_teach = QVBoxLayout(group_teach)
        layout_teach.setContentsMargins(4, 4, 4, 4)
        self.btn_grab = QPushButton("Grabar P[1]")
        self.btn_grab.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 5px; font-size: 10px;")
        self.btn_grab.clicked.connect(self.grabar_posicion_actual)
        layout_teach.addWidget(self.btn_grab)
        layout_inputs_v.addWidget(group_teach)
        
        # [SOLUCIÓN AL CRASH]: El estilo visual blanco se aplica al QGroupBox, no a su layout interno invisible
        group_di = QGroupBox("DI (Digital Inputs)")
        group_di.setStyleSheet("QGroupBox { font-weight: bold; color: #fff; }")
        grid_di = QGridLayout(group_di)
        grid_di.setContentsMargins(4, 4, 4, 4)
        grid_di.setSpacing(3)
        for i in range(4): 
            btn_di = QPushButton(f"{i+1}")
            btn_di.setFixedSize(20, 18)
            btn_di.setStyleSheet("font-size: 9px; background-color: #444; color: white; border-radius: 2px; font-weight: bold;")
            grid_di.addWidget(btn_di, 0, i)
        layout_inputs_v.addWidget(group_di)
        
        layout_columnas_aux.addWidget(panel_derecho_inputs, stretch=1)
        layout_principal.addLayout(layout_columnas_aux)
        
        # ==========================================
        # 4. BARRA DE NOTIFICACIÓN DEADMAN
        # ==========================================
        self.lbl_status_deadman = QLabel("Deadman Switch")
        self.lbl_status_deadman.setFixedHeight(22)
        self.lbl_status_deadman.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self.lbl_status_deadman)

        self.actualizar_interfaz_por_deadman()
        self.actualizar_robot_y_tcp()

    def actualizar_estado_deadman(self, activo):
        self.deadman_activo = activo
        self.actualizar_interfaz_por_deadman()
        if not self.deadman_activo and self.animacion_movimiento:
            if self.animacion_movimiento.state() == QVariantAnimation.State.Running:
                self.animacion_movimiento.stop()

    def actualizar_interfaz_por_deadman(self):
        for btn in self.botones_jog:
            btn.setEnabled(self.deadman_activo)
        self.btn_home.setEnabled(self.deadman_activo)
        self.btn_ejecutar.setEnabled(self.deadman_activo)
        self.btn_grab.setEnabled(self.deadman_activo)
        
        if self.deadman_activo:
            self.lbl_status_deadman.setText("✓ DEADMAN OK (JOG ACTIVO)")
            self.lbl_status_deadman.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; font-size: 10px; border-radius: 3px;")
        else:
            self.lbl_status_deadman.setText("⚠️ DEADMAN LIBERADO [SHIFT]")
            self.lbl_status_deadman.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; font-size: 10px; border-radius: 3px;")

    def jog_eje(self, joint_idx, delta_deg, limite_max):
        if not self.deadman_activo:
            return
        nuevo_angulo = self.current_angles_deg[joint_idx] + delta_deg
        if abs(nuevo_angulo) > limite_max:
            return
        self.current_angles_deg[joint_idx] = nuevo_angulo
        self.actualizar_robot_y_tcp()

    def grabar_posicion_actual(self):
        if not self.deadman_activo:
            return
        self.compilador.guardar_punto(self.siguiente_id_point_or_num(), self.current_angles_deg)
        self.siguiente_id_punto += 1
        self.btn_grab.setText(f"Grabar P[{self.siguiente_id_punto}]")

    def siguiente_id_point_or_num(self):
        return self.siguiente_id_punto

    def mover_a_home_animado(self):
        if not self.deadman_activo:
            return
            
        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(1500) 
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

    # [RESTAURACIÓN FIEL DEL BACKEND]: Mapeo exacto vector_full[1:7] de la cadena original
    def actualizar_robot_y_tcp(self):
        if not self.viewer_3d.chain:
            return

        angulos_rad = np.radians(self.current_angles_deg)
        len_cadena = len(self.viewer_3d.chain.links)
        vector_full = [0.0] * len_cadena
        vector_full[1:7] = angulos_rad # Mapeo exacto del robot_fanuc.urdf de tu compañero

        # Cálculo unificado de Cinemática Directa 4x4
        matriz_homogena = self.viewer_3d.chain.forward_kinematics(vector_full)
        x_mm = matriz_homogena[0, 3] * 1000
        y_mm = matriz_homogena[1, 3] * 1000
        z_mm = matriz_homogena[2, 3] * 1000

        # Alarma de proximidad del suelo simulado
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

        # Renderizado síncrono ultra-veloz
        self.viewer_3d.actualizar_posicion_visual(vector_full)
        
        self.lbl_x.setText(f"X: {x_mm:.2f}")
        self.lbl_y.setText(f"Y: {y_mm:.2f}")
        self.lbl_z.setText(f"Z: {z_mm:.2f}")

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
        
        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(1500)
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