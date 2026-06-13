import os
import numpy as np
from functools import partial
import json
import time
from collections import deque
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QGridLayout, QPushButton, QGroupBox, QTextEdit, 
                               QListWidget, QApplication, QDialog, QFormLayout, QLabel)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QTextCursor, QTextFormat, QColor
import pyqtgraph as pg

from gui.widgets_3d import RobotViewer3D
from core.tp_compiler import TPCompiler
from core.physics import MotorPhysics

class PanelControlIndustrial(QWidget):
    def __init__(self, viewer_3d, parent=None):
        super().__init__(parent)
        self.viewer_3d = viewer_3d 
        self.siguiente_id_punto = 1
        
        # ==========================================
        # VARIABLES DE PRODUCCIÓN Y FÍSICA
        # ==========================================
        self.fisica_motores = MotorPhysics()
        self.angulos_anteriores = [0.0] * 6
        self.ciclos_completados = 0
        self.tiempo_inicio_ciclo = 0.0
        self.ultimo_tiempo_ciclo_seg = 0.0
        self.paro_emergencia_activo = False
        self.modo_operacion = "MANUAL (JOG)"
        
        # --- Variables de simulación física para la Ventosa ---
        self.vacio_activo = False
        self.presion_vacio_kpa = 0.0
        self.consumo_aire_lpm = 0.0
        self.payload_kg = 0.0
        
        # ==========================================
        # BUCLES DE TIEMPO SEPARADOS
        # ==========================================
        # 1. Bucle de Física y Renderizado 3D (30 Hz)
        self.timer_fisica = QTimer(self)
        self.timer_fisica.timeout.connect(self.actualizar_bucle_fisico)
        self.timer_fisica.start(33) 
        
        # 2. Bucle de Actualización del Dashboard Local (10 Hz)
        self.timer_dashboard = QTimer(self)
        self.timer_dashboard.timeout.connect(self.actualizar_dashboard_local)
        self.timer_dashboard.start(100)
        
        self.setFixedWidth(380)
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(10, 10, 10, 10)
        
        self.current_angles_deg = [0.0] * 6 
        self.deadman_activo = False
        self.compilador = TPCompiler()

        estilo_botones_industrial = """
            QPushButton { background-color: #333333; color: white; font-weight: bold; padding: 8px; border: 1px solid #1a1a1a; border-radius: 4px; }
            QPushButton:pressed { background-color: #28a745; }
        """

        # ==========================================
        # 1. LISTA DE PUNTOS GUARDADOS
        # ==========================================
        grupo_lista = QGroupBox("Posiciones Guardadas (Cartesianas)")
        layout_lista = QVBoxLayout(grupo_lista)
        self.lista_puntos = QListWidget()
        self.lista_puntos.setStyleSheet("background-color: #282c34; color: #98c379; font-family: Consolas, monospace; font-size: 13px;")
        self.lista_puntos.setMaximumHeight(100)
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
        # 4. ZONA DE MEMORIA Y COMPILADOR
        # ==========================================
        grupo_memoria = QGroupBox("Memoria de Puntos (Teach)")
        layout_memoria = QVBoxLayout(grupo_memoria)
        self.btn_grabar_punto = QPushButton(f"Grabar posición P[{self.siguiente_id_punto}]")
        self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_grabar_punto.clicked.connect(self.grabar_punto_actual)
        layout_memoria.addWidget(self.btn_grabar_punto)
        layout_principal.addWidget(grupo_memoria, stretch=0)

        # ==========================================
        # 5. CONTROL DEL EFECTOR FINAL (Ventosa)
        # ==========================================
        grupo_ee = QGroupBox("Actuador Final (Herramienta)")
        layout_ee = QVBoxLayout(grupo_ee)
        self.btn_vacio = QPushButton("ACTIVAR VACÍO (VENTOSA)")
        self.btn_vacio.setStyleSheet("""
            QPushButton { background-color: #4a4a4a; color: white; font-weight: bold; padding: 10px; border-radius: 4px; }
            QPushButton:checked { background-color: #218838; border: 2px solid #1a6329; }
        """)
        self.btn_vacio.setCheckable(True)
        self.btn_vacio.clicked.connect(self.conmutar_vacio)
        layout_ee.addWidget(self.btn_vacio)
        layout_principal.addWidget(grupo_ee, stretch=0)
        
        self.actualizar_cinematica_local()
    
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

    # ==========================================
    # BUCLE DE FÍSICA Y CINEMÁTICA
    # ==========================================
    def actualizar_bucle_fisico(self):
        deltas = [self.current_angles_deg[i] - self.angulos_anteriores[i] for i in range(6)]
        self.fisica_motores.simular_paso_tiempo(deltas)
        self.angulos_anteriores = list(self.current_angles_deg)
        self.actualizar_cinematica_local()

    def conmutar_vacio(self, presionado):
        self.vacio_activo = presionado
        if self.vacio_activo:
            self.btn_vacio.setText("VACÍO ACTIVO")
            self.presion_vacio_kpa = -82.5  
            self.consumo_aire_lpm = 45.0
            self.payload_kg = 15.5 # Simulamos carga agarrada
        else:
            self.btn_vacio.setText("ACTIVAR VACÍO (VENTOSA)")
            self.presion_vacio_kpa = 0.0
            self.consumo_aire_lpm = 0.0
            self.payload_kg = 0.0
            
        self.viewer_3d.set_vacio_visual_state(self.vacio_activo)

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

    def ir_a_home(self):
        if not self.deadman_activo: return
        self.modo_operacion = "AUTOMÁTICO (HOME)"
        self.angulos_inicio = list(self.current_angles_deg)
        self.angulos_destino = [0.0] * 6
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.start()

    def _ejecutar_paso_interpolacion(self, t):
        if not self.deadman_activo:
            self.animacion_movimiento.stop()
            self.modo_operacion = "MANUAL (JOG)"
            return
        for i in range(6):
            distancia_total = self.angulos_destino[i] - self.angulos_inicio[i]
            self.current_angles_deg[i] = self.angulos_inicio[i] + (t * distancia_total)
        self.actualizar_cinematica_local()

    def procesar_jog_click(self, joint_index, paso_grados):
        if not self.deadman_activo: return
        self.modo_operacion = "MANUAL (JOG)"
        NUEVO_ANGULO = self.current_angles_deg[joint_index] + paso_grados
        limites = [180, 75, 120, 360, 125, 360]
        if abs(NUEVO_ANGULO) > limites[joint_index]: return 
        self.current_angles_deg[joint_index] = NUEVO_ANGULO
        self.actualizar_cinematica_local()
        
    def actualizar_cinematica_local(self):
        angulos_rad = np.radians(self.current_angles_deg)
        vector_full = [0.0] * len(self.viewer_3d.chain.links)
        vector_full[1:7] = angulos_rad 
        self.viewer_3d.actualizar_posicion_visual(vector_full)
        
        fk_matrix = self.viewer_3d.chain.forward_kinematics(vector_full)
        x_m, y_m, z_m = fk_matrix[:3, 3] 
        self.current_x = round(x_m * 1000, 2) 
        self.current_y = round(y_m * 1000, 2)
        self.current_z = round(z_m * 1000, 2)
        self.viewer_3d.actualizar_tcp_ui(self.current_x, self.current_y, self.current_z)

    # ==========================================
    # ACTUALIZACIÓN DE DASHBOARD LOCAL (10 Hz)
    # ==========================================
    def actualizar_dashboard_local(self):
        if not hasattr(self, 'current_x'): return 
        
        datos_industriales = {
            "x": self.current_x, "y": self.current_y, "z": self.current_z,
            "j1": self.current_angles_deg[0], "j2": self.current_angles_deg[1],
            "j3": self.current_angles_deg[2], "j4": self.current_angles_deg[3],
            "j5": self.current_angles_deg[4], "j6": self.current_angles_deg[5],
            "vacio_activo": self.vacio_activo,
            "presion_kpa": self.presion_vacio_kpa,
            "payload_kg": self.payload_kg,
            "corrientes_a": list(self.fisica_motores.corrientes),
            "temperaturas_c": list(self.fisica_motores.temperaturas),
            "ciclos_total": self.ciclos_completados,
            "tiempo_ciclo_s": self.ultimo_tiempo_ciclo_seg,
            "modo_operacion": self.modo_operacion,
            "seguridad": {
                "deadman": self.deadman_activo,
                "e_stop": self.paro_emergencia_activo
            }
        }
        
        main_window = self.window()
        if hasattr(main_window, 'dialogo_info') and main_window.dialogo_info.isVisible():
            main_window.dialogo_info.actualizar_datos(datos_industriales)
            
    def grabar_punto_actual(self):
        self.compilador.guardar_punto(self.siguiente_id_punto, self.current_angles_deg)
        fk_matrix = self.viewer_3d.chain.forward_kinematics([0.0] + list(np.radians(self.current_angles_deg)) + [0.0]*2)
        x, y, z = fk_matrix[:3, 3] * 1000 
        
        self.lista_puntos.addItem(f"P[{self.siguiente_id_punto}]: X={x:6.1f}  Y={y:6.1f}  Z={z:6.1f}")
        self.lista_puntos.scrollToBottom()
        
        self.siguiente_id_punto += 1
        self.btn_grabar_punto.setText(f"Grabar posición P[{self.siguiente_id_punto}]")
        self.btn_grabar_punto.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        QTimer.singleShot(500, lambda: self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;"))
        
    def iniciar_secuencia_programa(self):
        if not self.deadman_activo or self.paro_emergencia_activo: return
        self.modo_operacion = "AUTOMÁTICO (TP RUN)"
        texto = self.editor_codigo.toPlainText()
        self.lineas_programa = [linea.strip() for linea in texto.split('\n') if linea.strip()]
        self.linea_actual_idx = 0
        self.tiempo_inicio_ciclo = time.time() 
        if not self.lineas_programa: return
        self._procesar_siguiente_linea()

    def _procesar_siguiente_linea(self):
        if not self.deadman_activo or self.paro_emergencia_activo: 
            self.modo_operacion = "MANUAL (JOG)"
            return
        
        if self.linea_actual_idx >= len(self.lineas_programa):
            self.editor_codigo.setExtraSelections([]) 
            self.ciclos_completados += 1
            self.ultimo_tiempo_ciclo_seg = round(time.time() - self.tiempo_inicio_ciclo, 2)
            self.modo_operacion = "MANUAL (JOG)"
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

# ==========================================
# DASHBOARD GRÁFICO LOCAL SCADA (PyQtGraph)
# ==========================================
class DialogoInfoSistema(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SCADA Dashboard - OpenTP")
        self.resize(1000, 700) # Ventana más ancha para las gráficas
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; font-size: 13px; font-weight: bold; }
            QLabel#valor { color: #4ec9b0; font-family: Consolas; font-size: 14px; }
            QLabel#alerta { color: #f14c4c; font-family: Consolas; font-weight: bold;}
            QLabel#titulo { color: #569cd6; font-size: 16px; margin-bottom: 5px;}
            QGroupBox { border: 1px solid #404040; border-radius: 4px; margin-top: 15px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #c586c0; font-size: 13px;}
        """)

        layout_principal = QHBoxLayout(self)
        
        # --- COLUMNA IZQUIERDA (Estado y Texto) ---
        # SOLUCIÓN: Creamos un QWidget contenedor para poder fijarle el ancho
        contenedor_izq = QWidget()
        contenedor_izq.setFixedWidth(300) 
        col_izq = QVBoxLayout(contenedor_izq) # El layout ahora vive dentro del contenedor
        col_izq.setContentsMargins(0, 0, 10, 0)
        
        # Estado General
        grupo_estado = QGroupBox("Estado del Sistema")
        form_estado = QFormLayout(grupo_estado)
        self.lbl_modo = QLabel("-"); self.lbl_modo.setObjectName("valor")
        self.lbl_deadman = QLabel("-"); self.lbl_deadman.setObjectName("alerta")
        self.lbl_estop = QLabel("-"); self.lbl_estop.setObjectName("valor")
        form_estado.addRow("Modo Operación:", self.lbl_modo)
        form_estado.addRow("Deadman Switch:", self.lbl_deadman)
        form_estado.addRow("E-Stop:", self.lbl_estop)
        col_izq.addWidget(grupo_estado)
        
        # Efector y Producción
        grupo_produccion = QGroupBox("Carga y Producción")
        form_prod = QFormLayout(grupo_produccion)
        self.lbl_vacio = QLabel("-"); self.lbl_vacio.setObjectName("valor")
        self.lbl_payload = QLabel("-"); self.lbl_payload.setObjectName("valor")
        self.lbl_ciclos = QLabel("-"); self.lbl_ciclos.setObjectName("valor")
        self.lbl_tiempo = QLabel("-"); self.lbl_tiempo.setObjectName("valor")
        form_prod.addRow("Estado Ventosa:", self.lbl_vacio)
        form_prod.addRow("Payload Actual:", self.lbl_payload)
        form_prod.addRow("Ciclos Totales:", self.lbl_ciclos)
        form_prod.addRow("Último Ciclo:", self.lbl_tiempo)
        col_izq.addWidget(grupo_produccion)
        
        # Cinemática Actual
        grupo_cine = QGroupBox("Cinemática TCP (mm)")
        form_cine = QFormLayout(grupo_cine)
        self.lbl_x = QLabel("-"); self.lbl_x.setObjectName("valor")
        self.lbl_y = QLabel("-"); self.lbl_y.setObjectName("valor")
        self.lbl_z = QLabel("-"); self.lbl_z.setObjectName("valor")
        form_cine.addRow("X:", self.lbl_x)
        form_cine.addRow("Y:", self.lbl_y)
        form_cine.addRow("Z:", self.lbl_z)
        col_izq.addWidget(grupo_cine)
        
        col_izq.addStretch()
        
        # Agregamos el contenedor al layout principal en lugar del QVBoxLayout directamente
        layout_principal.addWidget(contenedor_izq)

        # --- COLUMNA DERECHA (Gráficas Osciloscopio) ---
        col_der = QVBoxLayout()
        
        # Buffers de historial (150 puntos para que el osciloscopio se vea continuo)
        self.max_historia = 150
        self.hist_tiempo = deque(maxlen=self.max_historia)
        self.hist_temp = [deque(maxlen=self.max_historia) for _ in range(6)]
        self.hist_curr = [deque(maxlen=self.max_historia) for _ in range(6)]
        self.tiempo_x = 0.0

        # Colores consistentes para los 6 motores
        self.colores = [(255,100,100), (100,255,100), (100,100,255), (255,255,100), (255,100,255), (100,255,255)]

        # Configuración común para las gráficas
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#d4d4d4')

        # Gráfica Temperatura
        self.plot_temp = pg.PlotWidget(title="Telemetría: Temperatura de Motores (°C)")
        self.plot_temp.showGrid(x=True, y=True, alpha=0.3)
        self.plot_temp.addLegend(offset=(10, 10))
        self.curvas_temp = []
        for i in range(6):
            curva = self.plot_temp.plot(pen=pg.mkPen(color=self.colores[i], width=2), name=f"J{i+1}")
            self.curvas_temp.append(curva)
        col_der.addWidget(self.plot_temp)

        # Gráfica Corriente
        self.plot_curr = pg.PlotWidget(title="Telemetría: Consumo Eléctrico (A)")
        self.plot_curr.showGrid(x=True, y=True, alpha=0.3)
        self.plot_curr.addLegend(offset=(10, 10))
        self.curvas_curr = []
        for i in range(6):
            curva = self.plot_curr.plot(pen=pg.mkPen(color=self.colores[i], width=2), name=f"J{i+1}")
            self.curvas_curr.append(curva)
        col_der.addWidget(self.plot_curr)

        layout_principal.addLayout(col_der)

    def actualizar_datos(self, datos):
        """Alimenta la interfaz de texto y avanza las gráficas"""
        # --- 1. Textos Lógicos y Numéricos ---
        self.lbl_modo.setText(datos["modo_operacion"])
        self.lbl_modo.setStyleSheet("color: #ce9178;" if "MANUAL" in datos["modo_operacion"] else "color: #4ec9b0;")
        
        es_seguro = datos["seguridad"]["deadman"]
        self.lbl_deadman.setText("ACTIVO" if es_seguro else "INACTIVO")
        self.lbl_deadman.setObjectName("valor" if es_seguro else "alerta")
        self.lbl_estop.setText("EMERGENCIA" if datos["seguridad"]["e_stop"] else "OK")
        
        self.lbl_vacio.setText("SUCCIONANDO" if datos["vacio_activo"] else "APAGADO")
        self.lbl_payload.setText(f"{datos['payload_kg']:.1f} kg")
        
        self.lbl_ciclos.setText(str(datos["ciclos_total"]))
        self.lbl_tiempo.setText(f"{datos['tiempo_ciclo_s']} s")
        
        self.lbl_x.setText(f"{datos['x']:.2f}")
        self.lbl_y.setText(f"{datos['y']:.2f}")
        self.lbl_z.setText(f"{datos['z']:.2f}")

        # Estilo dinámico temporal
        self.lbl_deadman.style().unpolish(self.lbl_deadman)
        self.lbl_deadman.style().polish(self.lbl_deadman)

        # --- 2. Avance del Osciloscopio ---
        self.tiempo_x += 0.1 # Añade 100ms
        self.hist_tiempo.append(self.tiempo_x)
        
        for i in range(6):
            self.hist_temp[i].append(datos["temperaturas_c"][i])
            self.hist_curr[i].append(datos["corrientes_a"][i])
            
            # Pintamos las curvas pasando los arrays a formato numpy por velocidad
            t_axis = list(self.hist_tiempo)
            self.curvas_temp[i].setData(t_axis, list(self.hist_temp[i]))
            self.curvas_curr[i].setData(t_axis, list(self.hist_curr[i]))

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
        
        self.dialogo_info = DialogoInfoSistema(self)
        self.visor_3d.btn_info.clicked.connect(self.dialogo_info.show)

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
        QApplication.instance().installEventFilter(self)
        super().showEvent(event)