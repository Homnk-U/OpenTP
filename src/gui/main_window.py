import os
import numpy as np
from functools import partial
import time
from collections import deque
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QGridLayout, QPushButton, QGroupBox, QTextEdit, 
                               QListWidget, QApplication, QDialog, QFormLayout, QLabel)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QTextCursor, QTextFormat, QColor
import pyqtgraph as pg
import pyqtgraph.opengl as gl 
from stl import mesh

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
        
        self.vacio_activo = False
        self.presion_vacio_kpa = 0.0
        self.consumo_aire_lpm = 0.0
        self.payload_kg = 0.0
        self.caja_agarrada = False
        
        # ==========================================
        # OBJETO 3D SÓLIDO (LA CAJA FÍSICA DESDE STL)
        # ==========================================
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        caja_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "meshes", "caja.stl"))
        
        try:
            if os.path.exists(caja_path):
                stl_caja = mesh.Mesh.from_file(caja_path)
                raw_vectors = stl_caja.vectors.reshape(-1, 3)
                
                # Mantuve la escala en 0.2 como la enviaste, cámbiala a 0.025 si la caja se ve muy grande
                escala = 0.2 
                raw_vectors = raw_vectors * escala
                
                rounded_vectors = np.round(raw_vectors, 6)
                vertices, caras = np.unique(rounded_vectors, axis=0, return_inverse=True)
                caras = caras.reshape(-1, 3)
                md_caja = gl.MeshData(vertexes=vertices, faces=caras)
                
                self.caja_visual = gl.GLMeshItem(meshdata=md_caja, smooth=False, color=(0.8, 0.5, 0.2, 1.0), shader='shaded')
                self.viewer_3d.canvas.addItem(self.caja_visual)
            else:
                print("[ADVERTENCIA] No se encontró caja.stl. Verifica la ruta.")
        except Exception as e:
            print(f"[CAJA ERROR] Falló la carga del STL: {e}")

        # Matriz inicial de la caja 
        self.matriz_caja_mundo = np.eye(4)
        self.matriz_caja_mundo[0, 3] = 1.35  
        self.matriz_caja_mundo[2, 3] = 0.15  
        
        if hasattr(self, 'caja_visual'):
            self.caja_visual.setTransform(self.matriz_caja_mundo)

        # ==========================================
        # BUCLES DE TIEMPO SEPARADOS
        # ==========================================
        self.timer_fisica = QTimer(self)
        self.timer_fisica.timeout.connect(self.actualizar_bucle_fisico)
        self.timer_fisica.start(33) # Física a 30Hz
        
        self.timer_dashboard = QTimer(self)
        self.timer_dashboard.timeout.connect(self.actualizar_dashboard_local)
        self.timer_dashboard.start(100) # SCADA a 10Hz
        
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

        # 1. LISTA DE PUNTOS GUARDADOS
        grupo_lista = QGroupBox("Posiciones Guardadas (Cartesianas)")
        layout_lista = QVBoxLayout(grupo_lista)
        self.lista_puntos = QListWidget()
        self.lista_puntos.setStyleSheet("background-color: #282c34; color: #98c379; font-family: Consolas, monospace; font-size: 13px;")
        self.lista_puntos.setMaximumHeight(100)
        layout_lista.addWidget(self.lista_puntos)
        layout_principal.addWidget(grupo_lista, stretch=0)

        # 2. PANTALLA DEL iPendant (Editor de Código TP)
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
        
        self.btn_demo = QPushButton("🔁 DEMO PICK & PLACE")
        self.btn_demo.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_demo.clicked.connect(self.iniciar_demo)
        layout_editor.addWidget(self.btn_demo)
        
        layout_principal.addWidget(grupo_editor, stretch=2)

        # 3. ZONA DE JOGGING Y BOTÓN HOME
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

        # 4. ZONA DE MEMORIA Y COMPILADOR
        grupo_memoria = QGroupBox("Memoria de Puntos (Teach)")
        layout_memoria = QVBoxLayout(grupo_memoria)
        self.btn_grabar_punto = QPushButton(f"Grabar posición P[{self.siguiente_id_punto}]")
        self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_grabar_punto.clicked.connect(self.grabar_punto_actual)
        layout_memoria.addWidget(self.btn_grabar_punto)
        layout_principal.addWidget(grupo_memoria, stretch=0)

        # 5. CONTROL DEL EFECTOR FINAL (Ventosa)
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
        self.animacion_movimiento.setDuration(2500)
        self.animacion_movimiento.setEasingCurve(QEasingCurve.InOutQuad) 
        self.animacion_movimiento.valueChanged.connect(self._ejecutar_paso_interpolacion)
        self.animacion_movimiento.finished.connect(self.enrutador_animacion)
        
        self.lineas_programa = []
        self.linea_actual_idx = 0
        self.angulos_inicio = [0.0] * 6
        self.angulos_destino = [0.0] * 6


    # ==========================================
    # SISTEMA DE SEGURIDAD INDUSTRIAL: LÍMITES DCS
    # ==========================================
    def verificar_limites_seguros(self, angulos):
        """
        DCS (Dual Check Safety): Evalúa límites mecánicos Y colisiones cartesianas.
        """
        # 1. SOFT LIMITS (Límites articulares para evitar que se desgarre)
        limites = [
            [-180.0, 180.0],  # J1
            [-50.0,   85.0],  # J2 
            [-100.0, 110.0],  # J3
            [-360.0, 360.0],  # J4
            [-130.0, 130.0],  # J5
            [-360.0, 360.0]   # J6
        ]
        
        for i in range(6):
            if angulos[i] < limites[i][0] or angulos[i] > limites[i][1]:
                print(f"⚠️ [DCS] Límite mecánico superado en J{i+1}: {angulos[i]:.1f}°")
                return False

        # 2. CARTESIAN SAFETY ZONE (Colisión con el piso o su propia base)
        if hasattr(self.viewer_3d, 'chain') and self.viewer_3d.chain:
            angulos_rad = np.radians(angulos)
            vector_full = [0.0] * len(self.viewer_3d.chain.links)
            vector_full[1:7] = angulos_rad
            
            # Simulamos matemáticamente dónde VA A QUEDAR el brazo antes de moverlo visualmente
            matrices = self.viewer_3d.chain.forward_kinematics(vector_full, full_kinematics=True)
            
            # Revisamos la altura de J5 y J6
            for idx in [-2, -1]:
                x, y, z = matrices[idx][:3, 3]
                
                # Regla de Piso: Absolutamente nada puede bajar de 5 centímetros
                if z < 0.05:
                    print(f"⚠️ [DCS] Riesgo de colisión con el suelo (Z={z:.2f}m)")
                    return False
                    
                # Regla de Base: El brazo no puede meterse a su propia base de hierro
                radio = np.sqrt(x**2 + y**2)
                if radio < 0.40 and z < 0.8:
                    print("⚠️ [DCS] Riesgo de auto-colisión con la base detectado.")
                    return False
                    
        return True

    def procesar_jog_click(self, joint_index, paso_grados):
        if not self.deadman_activo: return
        
        # --- BLOQUEO ESTRICTO DE HARDWARE ---
        # Si el robot entró en pánico, ignoramos los clics aunque dejes el botón presionado
        if self.paro_emergencia_activo: return
        
        self.modo_operacion = "MANUAL (JOG)"
        
        angulos_tentativos = list(self.current_angles_deg)
        angulos_tentativos[joint_index] += paso_grados
        
        if self.verificar_limites_seguros(angulos_tentativos):
            # Es seguro: Movemos el robot
            self.current_angles_deg[joint_index] = angulos_tentativos[joint_index]
            self.actualizar_cinematica_local()
        else:
            # PELIGRO: Congelamos el mando virtual por 1 segundo y disparamos SCADA
            self.paro_emergencia_activo = True
            QTimer.singleShot(1000, lambda: setattr(self, 'paro_emergencia_activo', False))

    def _ejecutar_paso_interpolacion(self, t):
        if not self.deadman_activo:
            self.animacion_movimiento.stop()
            self.modo_operacion = "MANUAL (JOG)"
            return
            
        angulos_paso = [0.0] * 6
        for i in range(6):
            distancia_total = self.angulos_destino[i] - self.angulos_inicio[i]
            angulos_paso[i] = self.angulos_inicio[i] + (t * distancia_total)
            
        if self.verificar_limites_seguros(angulos_paso):
            self.current_angles_deg = angulos_paso
            self.actualizar_cinematica_local()
        else:
            # Abortamos trayectoria y mandamos a Emergencia
            self.animacion_movimiento.stop()
            self.detener_demo()
            print("🛑 [CRITICAL STOP] Trayectoria automática abortada por violación de límites.")
            self.paro_emergencia_activo = True
            QTimer.singleShot(1500, lambda: setattr(self, 'paro_emergencia_activo', False))

    # ==========================================
    # LÓGICA DE LA DEMO PICK & PLACE
    # ==========================================
    def iniciar_demo(self):
        if not self.deadman_activo: 
            self.actualizar_estado_deadman(True) 
            
        self.modo_operacion = "AUTOMÁTICO (DEMO)"
        self.btn_demo.setText("⏹ DETENER DEMO")
        self.btn_demo.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_demo.clicked.disconnect()
        self.btn_demo.clicked.connect(self.detener_demo)
        
        self.tiempo_inicio_ciclo = time.time()
        
        self.pasos_demo = [
            {"j": [0.0, 30.0, -15.0, 0.0, -105.0, 0.0], "vacio": False}, 
            {"j": [0.0, 30.0, -15.0, 0.0, -105.0, 0.0], "vacio": True},  
            {"j": [0.0, 0.0, 0.0, 0.0, -90.0, 0.0], "vacio": True},     
            {"j": [75.0, 0.0, 0.0, 0.0, -90.0, 0.0], "vacio": True},    
            {"j": [75.0, 30.0, -15.0, 0.0, -105.0, 0.0], "vacio": True}, 
            {"j": [75.0, 30.0, -15.0, 0.0, -105.0, 0.0], "vacio": False},
            {"j": [75.0, 0.0, 0.0, 0.0, -90.0, 0.0], "vacio": False},   
            {"j": [0.0, 0.0, 0.0, 0.0, -90.0, 0.0], "vacio": False},    
        ]
        
        target_j_rad = np.radians(self.pasos_demo[0]["j"])
        vec = [0.0] * len(self.viewer_3d.chain.links)
        vec[1:7] = target_j_rad
        matriz_fk = self.viewer_3d.chain.forward_kinematics(vec)
        
        angulo = np.pi / 2
        rotacion_ajuste = np.array([[np.cos(angulo),0,np.sin(angulo),0],[0,1,0,0],[-np.sin(angulo),0,np.cos(angulo),0],[0,0,0,1]])
        ajuste_brecha = np.eye(4); ajuste_brecha[2, 3] = -0.045
        matriz_cuerpo = np.dot(matriz_fk, np.dot(rotacion_ajuste, ajuste_brecha))
        desplazamiento_tapa = np.eye(4); desplazamiento_tapa[2, 3] = 0.075
        matriz_ventosa = np.dot(matriz_cuerpo, desplazamiento_tapa)
        
        self.matriz_caja_inicial = np.eye(4)
        self.matriz_caja_inicial[0, 3] = matriz_ventosa[0, 3]
        self.matriz_caja_inicial[1, 3] = matriz_ventosa[1, 3]
        self.matriz_caja_inicial[2, 3] = 0.15 
        
        self.matriz_caja_mundo = np.copy(self.matriz_caja_inicial)
        if hasattr(self, 'caja_visual'):
            self.caja_visual.setTransform(self.matriz_caja_mundo)
            
        self.caja_agarrada = False
        self.paso_actual_demo = 0
        self.ejecutar_siguiente_paso_demo()

    def detener_demo(self):
        self.modo_operacion = "MANUAL (JOG)"
        self.animacion_movimiento.stop()
        self.btn_demo.setText("🔁 DEMO PICK & PLACE")
        self.btn_demo.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_demo.clicked.disconnect()
        self.btn_demo.clicked.connect(self.iniciar_demo)

    def ejecutar_siguiente_paso_demo(self):
        if self.modo_operacion != "AUTOMÁTICO (DEMO)": return
        
        if self.paso_actual_demo >= len(self.pasos_demo):
            self.ciclos_completados += 1
            self.ultimo_tiempo_ciclo_seg = round(time.time() - self.tiempo_inicio_ciclo, 2)
            self.tiempo_inicio_ciclo = time.time()
            self.paso_actual_demo = 0 
            
            if hasattr(self, 'caja_visual'):
                self.matriz_caja_mundo = np.copy(self.matriz_caja_inicial)
                self.caja_visual.setTransform(self.matriz_caja_mundo)

        paso = self.pasos_demo[self.paso_actual_demo]
        self.paso_actual_demo += 1
        
        if self.vacio_activo != paso["vacio"]:
            self.btn_vacio.setChecked(paso["vacio"])
            self.conmutar_vacio(paso["vacio"])
            QTimer.singleShot(600, self.ejecutar_siguiente_paso_demo)
            return

        self.angulos_inicio = list(self.current_angles_deg)
        self.angulos_destino = paso["j"]
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.start()

    def enrutador_animacion(self):
        if self.modo_operacion == "AUTOMÁTICO (TP RUN)":
            self._procesar_siguiente_linea()
        elif self.modo_operacion == "AUTOMÁTICO (DEMO)":
            self.ejecutar_siguiente_paso_demo()

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
            self.payload_kg = 15.5 if self.caja_agarrada else 0.0
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
        # CINEMÁTICA ESTRICTA URDF: ATRAPE DE CAJA
        # ==========================================
        angulo = np.pi / 2
        rotacion_ajuste = np.array([[np.cos(angulo),0,np.sin(angulo),0],[0,1,0,0],[-np.sin(angulo),0,np.cos(angulo),0],[0,0,0,1]])
        ajuste_brecha = np.eye(4); ajuste_brecha[2, 3] = -0.045
        matriz_cuerpo = np.dot(fk_matrix, np.dot(rotacion_ajuste, ajuste_brecha))
        desplazamiento_tapa = np.eye(4); desplazamiento_tapa[2, 3] = 0.075
        matriz_ventosa = np.dot(matriz_cuerpo, desplazamiento_tapa)
        
        pos_ventosa = matriz_ventosa[:3, 3]
        pos_caja = self.matriz_caja_mundo[:3, 3]
        distancia = np.linalg.norm(pos_ventosa - pos_caja)
        
        if hasattr(self, 'caja_visual'):
            if self.vacio_activo and distancia < 0.35: 
                self.caja_agarrada = True
                self.payload_kg = 15.5
            elif not self.vacio_activo:
                if self.caja_agarrada:
                    self.matriz_caja_mundo = np.copy(self.caja_visual.transform().matrix())
                    self.matriz_caja_mundo[2, 3] = 0.15 
                    self.caja_visual.setTransform(self.matriz_caja_mundo)
                self.caja_agarrada = False
                self.payload_kg = 0.0

            if self.caja_agarrada:
                desplazamiento_agarre = np.eye(4)
                desplazamiento_agarre[2, 3] = 0.15 
                matriz_caja_final = np.dot(matriz_ventosa, desplazamiento_agarre)
                self.caja_visual.setTransform(matriz_caja_final)
            else:
                self.caja_visual.setTransform(self.matriz_caja_mundo)

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
        self.resize(1000, 700) 
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
        
        contenedor_izq = QWidget()
        contenedor_izq.setFixedWidth(300) 
        col_izq = QVBoxLayout(contenedor_izq) 
        col_izq.setContentsMargins(0, 0, 10, 0)
        
        grupo_estado = QGroupBox("Estado del Sistema")
        form_estado = QFormLayout(grupo_estado)
        self.lbl_modo = QLabel("-"); self.lbl_modo.setObjectName("valor")
        self.lbl_deadman = QLabel("-"); self.lbl_deadman.setObjectName("alerta")
        self.lbl_estop = QLabel("-"); self.lbl_estop.setObjectName("valor")
        form_estado.addRow("Modo Operación:", self.lbl_modo)
        form_estado.addRow("Deadman Switch:", self.lbl_deadman)
        form_estado.addRow("E-Stop:", self.lbl_estop)
        col_izq.addWidget(grupo_estado)
        
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
        layout_principal.addWidget(contenedor_izq)

        col_der = QVBoxLayout()
        
        self.max_historia = 150
        self.hist_tiempo = deque(maxlen=self.max_historia)
        self.hist_temp = [deque(maxlen=self.max_historia) for _ in range(6)]
        self.hist_curr = [deque(maxlen=self.max_historia) for _ in range(6)]
        self.tiempo_x = 0.0

        self.colores = [(255,100,100), (100,255,100), (100,100,255), (255,255,100), (255,100,255), (100,255,255)]
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#d4d4d4')

        self.plot_temp = pg.PlotWidget(title="Telemetría: Temperatura de Motores (°C)")
        self.plot_temp.showGrid(x=True, y=True, alpha=0.3)
        self.plot_temp.addLegend(offset=(10, 10))
        self.curvas_temp = []
        for i in range(6):
            curva = self.plot_temp.plot(pen=pg.mkPen(color=self.colores[i], width=2), name=f"J{i+1}")
            self.curvas_temp.append(curva)
        col_der.addWidget(self.plot_temp)

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

        self.lbl_deadman.style().unpolish(self.lbl_deadman)
        self.lbl_deadman.style().polish(self.lbl_deadman)

        self.tiempo_x += 0.1 
        self.hist_tiempo.append(self.tiempo_x)
        
        for i in range(6):
            self.hist_temp[i].append(datos["temperaturas_c"][i])
            self.hist_curr[i].append(datos["corrientes_a"][i])
            
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