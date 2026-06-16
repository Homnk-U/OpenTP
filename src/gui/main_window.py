import os
import numpy as np
from functools import partial
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QGridLayout, QPushButton, QGroupBox, QTextEdit, 
                               QApplication, QLabel, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor, QTextFormat, QColor

from gui.widgets_3d import RobotViewer3D
from core.robot_controller import RobotController  # <-- Importamos el Cerebro
from gui.scada_dashboard import DialogoInfoSistema

class PanelControlIndustrial(QWidget):
    def __init__(self, viewer_3d, parent=None):
        super().__init__(parent)
        self.setFixedWidth(380)
        
        # 1. Instanciamos el Controlador (El Cerebro) y le pasamos nuestra referencia
        self.controller = RobotController(viewer_3d, ui_panel=self)
        
        # 2. Timer exclusivo para actualizar el SCADA UI a 10Hz
        self.timer_dashboard = QTimer(self)
        self.timer_dashboard.timeout.connect(self.actualizar_pantalla_scada)
        self.timer_dashboard.start(100)
        
        # --- DISEÑO VISUAL (UI) ---
        layout_maestro = QVBoxLayout(self)
        layout_maestro.setContentsMargins(0, 0, 0, 0)
        area_scroll = QScrollArea()
        area_scroll.setWidgetResizable(True)
        area_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        contenedor_controles = QWidget()
        layout_principal = QVBoxLayout(contenedor_controles)
        area_scroll.setWidget(contenedor_controles)
        layout_maestro.addWidget(area_scroll)

        estilo_btns = "QPushButton { background-color: #333333; color: white; font-weight: bold; padding: 8px; border-radius: 4px; } QPushButton:pressed { background-color: #28a745; }"

        # Editor TP
        grupo_editor = QGroupBox("Programa TP (Editor)")
        layout_editor = QVBoxLayout(grupo_editor)
        self.editor_codigo = QTextEdit()
        self.editor_codigo.setStyleSheet("background-color: white; color: black; font-family: Consolas; font-size: 14px;")
        self.editor_codigo.setText("J P[1] 100% FINE\nJ P[2] 100% FINE")
        layout_editor.addWidget(self.editor_codigo)
        self.btn_ejecutar = QPushButton("EJECUTAR PROGRAMA")
        self.btn_ejecutar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_ejecutar.clicked.connect(self.iniciar_programa_ui)
        layout_editor.addWidget(self.btn_ejecutar)
        layout_principal.addWidget(grupo_editor)

        # Control Manual (Jog)
        grupo_jog = QGroupBox("Control Manual (Jog)")
        layout_jog = QGridLayout(grupo_jog)
        btn_home = QPushButton("HOME")
        btn_home.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_home.clicked.connect(self.controller.ir_a_home)
        layout_jog.addWidget(btn_home, 0, 0) 
        
        btn_reset = QPushButton("RESET FAULT")
        btn_reset.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_reset.clicked.connect(self.controller.resetear_falla)
        layout_jog.addWidget(btn_reset, 0, 1) 
        
        for fila, (t_neg, t_pos) in enumerate([("-J1", "+J1"), ("-J2", "+J2"), ("-J3", "+J3"), ("-J4", "+J4"), ("-J5", "+J5"), ("-J6", "+J6")]):
            b_neg, b_pos = QPushButton(t_neg), QPushButton(t_pos)
            for b in (b_neg, b_pos): b.setAutoRepeat(True); b.setStyleSheet(estilo_btns)
            b_neg.clicked.connect(partial(self.controller.procesar_jog_click, fila, -1))
            b_pos.clicked.connect(partial(self.controller.procesar_jog_click, fila, 1))
            layout_jog.addWidget(b_neg, fila + 1, 0); layout_jog.addWidget(b_pos, fila + 1, 1)

        self.btn_grabar_punto = QPushButton("Grabar posición P[1]")
        self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px; margin-top: 10px;")
        self.btn_grabar_punto.clicked.connect(self.grabar_punto_ui)
        layout_jog.addWidget(self.btn_grabar_punto, 7, 0, 1, 2) 
        layout_principal.addWidget(grupo_jog)

        # Macros
        grupo_macros = QGroupBox("Rutinas Predefinidas")
        layout_macros = QVBoxLayout(grupo_macros)
        self.btn_demo = QPushButton("DEMO PICK && PLACE")
        self.btn_demo.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_demo.clicked.connect(self.controller.iniciar_demo)
        layout_macros.addWidget(self.btn_demo)
        layout_principal.addWidget(grupo_macros)

        # Digital I/O
        grupo_io = QGroupBox("Digital I/O")
        layout_io = QGridLayout(grupo_io)
        layout_io.addWidget(QLabel("DI (Entradas)"), 0, 0, alignment=Qt.AlignCenter)
        layout_io.addWidget(QLabel("DO (Salidas)"), 0, 1, alignment=Qt.AlignCenter)
        self.leds_di, self.btns_do = [], []
        for i in range(8):
            btn_di = QPushButton(f"DI[{i+1}]"); btn_di.setCheckable(True)
            btn_di.setStyleSheet("QPushButton { background-color: #333333; color: white; } QPushButton:checked { background-color: #17a2b8; }")
            self.leds_di.append(btn_di); layout_io.addWidget(btn_di, i+1, 0)
            
            btn_do = QPushButton(f"DO[{i+1}]"); btn_do.setCheckable(True)
            btn_do.setStyleSheet("QPushButton { background-color: #4a4a4a; color: white; } QPushButton:checked { background-color: #28a745; }")
            self.btns_do.append(btn_do); layout_io.addWidget(btn_do, i+1, 1)

        self.btn_vacio = self.btns_do[0]
        self.btn_vacio.setText("DO[1]: VACUUM")
        self.btn_vacio.clicked.connect(self.controller.conmutar_vacio)
        layout_principal.addWidget(grupo_io)

    # --- CALLBACKS Y ACTUALIZACIONES DE LA UI ---
    def actualizar_pantalla_scada(self):
        # Le pedimos el diccionario maestro al Cerebro y se lo mandamos a la ventana Dashboard
        estado = self.controller.obtener_estado_diccionario()
        if hasattr(self.window(), 'dialogo_info') and self.window().dialogo_info.isVisible():
            self.window().dialogo_info.actualizar_datos(estado)

    def iniciar_programa_ui(self):
        lineas = [l.strip() for l in self.editor_codigo.toPlainText().split('\n') if l.strip()]
        self.controller.iniciar_secuencia_programa(lineas)

    def grabar_punto_ui(self):
        idx = self.controller.siguiente_id_punto
        angulos = self.controller.current_angles_deg
        self.controller.compilador.guardar_punto(idx, angulos)
        x, y, z = self.controller.current_x, self.current_y, self.current_z
        self.controller.viewer_3d.lista_puntos.addItem(f"P[{idx}]: X={x:6.1f}  Y={y:6.1f}  Z={z:6.1f}")
        
        self.controller.siguiente_id_punto += 1
        self.btn_grabar_punto.setText(f"Grabar posición P[{self.controller.siguiente_id_punto}]")

    def resaltar_linea_tp(self, numero_linea):
        cursor = self.editor_codigo.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, numero_linea)
        seleccion = QTextEdit.ExtraSelection()
        seleccion.format.setBackground(QColor("#d1d5db"))
        seleccion.format.setProperty(QTextFormat.FullWidthSelection, True)
        seleccion.cursor = cursor
        self.editor_codigo.setExtraSelections([seleccion])

    def limpiar_resaltado(self):
        self.editor_codigo.setExtraSelections([])

    def actualizar_ui_vacio(self, estado):
        self.btn_vacio.setChecked(estado)
        self.btn_vacio.setText("VACÍO ACTIVO" if estado else "ACTIVAR VACÍO (VENTOSA)")

    def actualizar_ui_demo(self, en_curso):
        if en_curso:
            self.btn_demo.setText("DETENER DEMO")
            self.btn_demo.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
            self.btn_demo.clicked.disconnect()
            self.btn_demo.clicked.connect(self.controller.detener_demo)
        else:
            self.btn_demo.setText("DEMO PICK && PLACE")
            self.btn_demo.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
            try: self.btn_demo.clicked.disconnect()
            except: pass
            self.btn_demo.clicked.connect(self.controller.iniciar_demo)

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
                self.panel_control.controller.actualizar_estado_deadman(True)
            elif event.key() == Qt.Key_Space and not event.isAutoRepeat():
                self.panel_control.controller.activar_paro_emergencia() 
        elif event.type() == QEvent.KeyRelease:
            if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
                self.panel_control.controller.actualizar_estado_deadman(False)
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        QApplication.instance().installEventFilter(self)
        super().showEvent(event)