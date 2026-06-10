import numpy as np
from functools import partial
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QGridLayout, QPushButton, QGroupBox, QTextEdit, QListWidget)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QTextCursor, QTextFormat, QColor
from gui.widgets_3d import RobotViewer3D
from core.tp_compiler import TPCompiler

class PanelControlIndustrial(QWidget):
    def __init__(self, viewer_3d, parent=None):
        super().__init__(parent)
        self.viewer_3d = viewer_3d 
        
        self.setFixedWidth(380)
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(10, 10, 10, 10)
        layout_principal.setSpacing(10)
        
        self.current_angles_deg = [0.0] * 6 
        self.deadman_activo = False
        self.compilador = TPCompiler()
        self.siguiente_id_punto = 1 
        
        estilo_botones_industrial = """
            QPushButton { background-color: #333333; color: white; font-weight: bold; padding: 8px; border: 1px solid #1a1a1a; border-radius: 4px; }
            QPushButton:pressed { background-color: #28a745; }
        """

        # ==========================================
        # 1. LISTA DE PUNTOS GUARDADOS (CARTESIANOS)
        # ==========================================
        grupo_lista = QGroupBox("Posiciones Guardadas")
        layout_lista = QVBoxLayout(grupo_lista)
        
        self.lista_puntos = QListWidget()
        self.lista_puntos.setStyleSheet("background-color: #282c34; color: #98c379; font-family: Consolas, monospace; font-size: 13px;")
        self.lista_puntos.setMaximumHeight(100) # Mantener compacto
        layout_lista.addWidget(self.lista_puntos)
        
        layout_principal.addWidget(grupo_lista, stretch=0)

        # ==========================================
        # 2. PANTALLA DEL iPendant (Editor de Código TP)
        # ==========================================
        grupo_editor = QGroupBox("Programa TP (Editor)")
        layout_editor = QVBoxLayout(grupo_editor)
        
        self.editor_codigo = QTextEdit()
        self.editor_codigo.setStyleSheet("background-color: white; color: black; font-family: Consolas; font-size: 14px;")
        self.editor_codigo.setText("J P[1] 100% FINE\nJ P[2] 100% FINE")
        layout_editor.addWidget(self.editor_codigo)
        
        self.btn_ejecutar = QPushButton("▶ EJECUTAR PROGRAMA (F3)")
        self.btn_ejecutar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_ejecutar.clicked.connect(self.iniciar_secuencia_programa)
        layout_editor.addWidget(self.btn_ejecutar)
        
        layout_principal.addWidget(grupo_editor, stretch=2)

        # ==========================================
        # 3. ZONA DE JOGGING Y BOTÓN HOME
        # ==========================================
        grupo_jog = QGroupBox("Control Manual (Jog)")
        layout_jog = QGridLayout(grupo_jog)
        
        self.btn_home = QPushButton("HOME")
        self.btn_home.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_home.clicked.connect(self.ir_a_home)
        layout_jog.addWidget(self.btn_home, 0, 0, 1, 2)
        
        etiquetas_botones = [("-J1", "+J1"), ("-J2", "+J2"), ("-J3", "+J3"), ("-J4", "+J4"), ("-J5", "+J5"), ("-J6", "+J6")]
        
        for fila, (texto_neg, texto_pos) in enumerate(etiquetas_botones):
            btn_neg = QPushButton(texto_neg)
            btn_pos = QPushButton(texto_pos)
            
            for btn in (btn_neg, btn_pos):
                btn.setAutoRepeat(True)        
                btn.setAutoRepeatDelay(100)    
                btn.setAutoRepeatInterval(30)  
                btn.setStyleSheet(estilo_botones_industrial) 
            
            joint_id = fila 
            btn_neg.clicked.connect(partial(self.procesar_jog_click, joint_id, -1))
            btn_pos.clicked.connect(partial(self.procesar_jog_click, joint_id, 1))
            
            layout_jog.addWidget(btn_neg, fila + 1, 0)
            layout_jog.addWidget(btn_pos, fila + 1, 1)
            
        layout_principal.addWidget(grupo_jog, stretch=0)

        # ==========================================
        # 4. ZONA DE MEMORIA Y COMPILADOR (TEACH)
        # ==========================================
        grupo_memoria = QGroupBox("Memoria de Puntos (Teach)")
        layout_memoria = QVBoxLayout(grupo_memoria)
        
        self.btn_grabar_punto = QPushButton(f"Grabar posición P[{self.siguiente_id_punto}]")
        self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_grabar_punto.clicked.connect(self.grabar_punto_actual)
        layout_memoria.addWidget(self.btn_grabar_punto)
        
        layout_principal.addWidget(grupo_memoria, stretch=0)

        # ==========================================
        # 5. ZONA DE ENTRADAS DIGITALES
        # ==========================================
        grupo_di = QGroupBox("Entradas Digitales (DI)")
        layout_di = QGridLayout(grupo_di)
        
        for i in range(8):
            btn_di = QPushButton(f"DI [{i+1}]")
            btn_di.setCheckable(True)
            btn_di.setStyleSheet("""
                QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 5px; }
                QPushButton:checked { background-color: #218838; font-weight: bold; border: 2px solid #1a6329; }
            """)
            layout_di.addWidget(btn_di, i // 4, i % 4)
            
        layout_principal.addWidget(grupo_di, stretch=0)
        
        # Inicializar posición al arrancar
        self.actualizar_robot_y_tcp()
    
        # ==========================================
        # MOTOR DE INTERPOLACIÓN DE TRAYECTORIAS
        # ==========================================
        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(3000)
        self.animacion_movimiento.setEasingCurve(QEasingCurve.InOutQuad) 
        self.animacion_movimiento.valueChanged.connect(self._ejecutar_paso_interpolacion)
        self.animacion_movimiento.finished.connect(self._procesar_siguiente_linea)
        
        self.lineas_programa = []
        self.linea_actual_idx = 0
        self.angulos_inicio = [0.0] * 6
        self.angulos_destino = [0.0] * 6

    # --- LÓGICA DE INTERFAZ ---
    def actualizar_estado_deadman(self, presionado):
        self.deadman_activo = presionado
        self.viewer_3d.set_deadman_state(presionado)

    def resaltar_linea_tp(self, numero_linea):
        cursor = self.editor_codigo.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, numero_linea)
        
        seleccion = QTextEdit.ExtraSelection()
        seleccion.format.setBackground(QColor("#d1d5db"))
        seleccion.format.setProperty(QTextFormat.FullWidthSelection, True)
        seleccion.cursor = cursor
        seleccion.cursor.clearSelection()
        self.editor_codigo.setExtraSelections([seleccion])

    # --- LÓGICA DEL ROBOT ---
    def ir_a_home(self):
        if not self.deadman_activo: return
        self.angulos_inicio = list(self.current_angles_deg)
        self.angulos_destino = [0.0] * 6
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.start()

    def _ejecutar_paso_interpolacion(self, t):
        if not self.deadman_activo:
            self.animacion_movimiento.stop()
            return
            
        for i in range(6):
            distancia_total = self.angulos_destino[i] - self.angulos_inicio[i]
            self.current_angles_deg[i] = self.angulos_inicio[i] + (t * distancia_total)
            
        self.actualizar_robot_y_tcp()

    def procesar_jog_click(self, joint_index, paso_grados):
        if not self.deadman_activo: return
        
        NUEVO_ANGULO = self.current_angles_deg[joint_index] + paso_grados
        limites = [180, 75, 120, 360, 125, 360]
        if abs(NUEVO_ANGULO) > limites[joint_index]: return 

        self.current_angles_deg[joint_index] = NUEVO_ANGULO
        self.actualizar_robot_y_tcp()
        
    def actualizar_robot_y_tcp(self):
        angulos_rad = np.radians(self.current_angles_deg)
        vector_full = [0.0] * len(self.viewer_3d.chain.links)
        vector_full[1:7] = angulos_rad 
        
        self.viewer_3d.actualizar_posicion_visual(vector_full)
        
        fk_matrix = self.viewer_3d.chain.forward_kinematics(vector_full)
        x_m, y_m, z_m = fk_matrix[:3, 3] 
        self.viewer_3d.actualizar_tcp_ui(x_m * 1000, y_m * 1000, z_m * 1000)
        
    def grabar_punto_actual(self):
        # 1. Guardar los ángulos en el compilador
        self.compilador.guardar_punto(self.siguiente_id_punto, self.current_angles_deg)
        
        # 2. Calcular los valores cartesianos para la UI usando cinemática directa
        angulos_rad = np.radians(self.current_angles_deg)
        vector_full = [0.0] * len(self.viewer_3d.chain.links)
        vector_full[1:7] = angulos_rad 
        fk_matrix = self.viewer_3d.chain.forward_kinematics(vector_full)
        x, y, z = fk_matrix[:3, 3] * 1000 # Convertir a milímetros
        
        # 3. Formatear y mostrar en la lista superior
        texto_lista = f"P[{self.siguiente_id_punto}]: X={x:6.1f}  Y={y:6.1f}  Z={z:6.1f}"
        self.lista_puntos.addItem(texto_lista)
        self.lista_puntos.scrollToBottom()
        
        # 4. Actualizar botón
        self.siguiente_id_punto += 1
        self.btn_grabar_punto.setText(f"Grabar posición P[{self.siguiente_id_punto}]")
        
        self.btn_grabar_punto.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;"))
        
    def iniciar_secuencia_programa(self):
        if not self.deadman_activo: return
            
        texto = self.editor_codigo.toPlainText()
        self.lineas_programa = [linea.strip() for linea in texto.split('\n') if linea.strip()]
        self.linea_actual_idx = 0
        
        if not self.lineas_programa: return
        self._procesar_siguiente_linea()

    def _procesar_siguiente_linea(self):
        if not self.deadman_activo: return

        if self.linea_actual_idx >= len(self.lineas_programa):
            self.editor_codigo.setExtraSelections([]) 
            return
            
        self.resaltar_linea_tp(self.linea_actual_idx)
            
        linea_actual = self.lineas_programa[self.linea_actual_idx].upper()
        self.linea_actual_idx += 1
        
        if "P[" in linea_actual:
            inicio = linea_actual.find("P[")
            fin = linea_actual.find("]", inicio) + 1
            nombre_punto = linea_actual[inicio:fin]
            
            angulos_destino = self.compilador.obtener_punto(nombre_punto)
            
            if angulos_destino:
                self.angulos_inicio = list(self.current_angles_deg)
                self.angulos_destino = angulos_destino
                self.animacion_movimiento.setStartValue(0.0)
                self.animacion_movimiento.setEndValue(1.0)
                self.animacion_movimiento.start()
            else:
                self._procesar_siguiente_linea()
        else:
            self._procesar_siguiente_linea()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenTP Simulator - FANUC M-900iA")
        self.resize(1200, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout_principal = QHBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        
        self.visor_3d = RobotViewer3D()
        self.panel_control = PanelControlIndustrial(viewer_3d=self.visor_3d) 
        
        layout_principal.addWidget(self.visor_3d, stretch=3) 
        layout_principal.addWidget(self.panel_control, stretch=1)
        
        self.setFocusPolicy(Qt.StrongFocus)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
                self.panel_control.actualizar_estado_deadman(True)
                
        elif event.type() == QEvent.KeyRelease:
            if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
                self.panel_control.actualizar_estado_deadman(False)
                
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        """Aseguramos que el filtro se instale una vez que la ventana existe"""
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)
        super().showEvent(event)