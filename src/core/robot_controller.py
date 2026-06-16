import time
import numpy as np
from PySide6.QtCore import QObject, QTimer, QVariantAnimation, QEasingCurve

from core.tp_compiler import TPCompiler
from core.physics import MotorPhysics

class RobotController(QObject):
    def __init__(self, viewer_3d, ui_panel=None):
        super().__init__()
        self.viewer_3d = viewer_3d
        self.ui_panel = ui_panel  # Referencia a la UI para actualizar botones/textos visuales
        self.compilador = TPCompiler()
        self.fisica_motores = MotorPhysics()
        
        # Estado del Robot
        self.current_angles_deg = [0.0] * 6 
        self.angulos_anteriores = [0.0] * 6
        self.angulos_inicio = [0.0] * 6
        self.angulos_destino = [0.0] * 6
        self.current_x, self.current_y, self.current_z = 0.0, 0.0, 0.0
        
        # Variables de Producción y Seguridad
        self.modo_operacion = "MANUAL (JOG)"
        self.paro_emergencia_activo = False
        self.deadman_activo = False
        
        self.vacio_activo = False
        self.presion_vacio_kpa = 0.0
        self.consumo_aire_lpm = 0.0
        self.payload_kg = 0.0
        self.caja_agarrada = False
        
        self.ciclos_completados = 0
        self.tiempo_inicio_ciclo = 0.0
        self.ultimo_tiempo_ciclo_seg = 0.0
        self.siguiente_id_punto = 1

        # Carga del Entorno 3D
        self.matriz_caja_inicial = np.eye(4)
        self.matriz_caja_inicial[0, 3] = 1.33383  
        self.matriz_caja_mundo = np.copy(self.matriz_caja_inicial)
        self.viewer_3d.cargar_caja_entorno()
        self.viewer_3d.set_pose_caja(self.matriz_caja_mundo)

        # Motor de Interpolación
        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(2500)
        self.animacion_movimiento.setEasingCurve(QEasingCurve.InOutQuad) 
        self.animacion_movimiento.valueChanged.connect(self._ejecutar_paso_interpolacion)
        self.animacion_movimiento.finished.connect(self.enrutador_animacion)

        # Bucle Físico Interno (30Hz)
        self.timer_fisica = QTimer(self)
        self.timer_fisica.timeout.connect(self.actualizar_bucle_fisico)
        self.timer_fisica.start(33)
        
        self.lineas_programa = []
        self.linea_actual_idx = 0
        self.pasos_demo = []
        self.paso_actual_demo = 0

    # ==========================================
    # LÓGICA DE SEGURIDAD (DCS)
    # ==========================================
    def verificar_limites_seguros(self, angulos):
        limites = [[-180.0, 180.0], [-50.0, 85.0], [-100.0, 110.0], [-360.0, 360.0], [-130.0, 130.0], [-360.0, 360.0]]
        for i in range(6):
            if angulos[i] < limites[i][0] or angulos[i] > limites[i][1]:
                print(f"[DCS] Límite mecánico superado en J{i+1}: {angulos[i]:.1f}°")
                return False

        if hasattr(self.viewer_3d, 'chain') and self.viewer_3d.chain:
            angulos_rad = np.radians(angulos)
            vector_full = [0.0] * len(self.viewer_3d.chain.links)
            vector_full[1:7] = angulos_rad
            matrices = self.viewer_3d.chain.forward_kinematics(vector_full, full_kinematics=True)
            for idx in [-2, -1]:
                x, y, z = matrices[idx][:3, 3]
                if z < 0.05: return False
                if np.sqrt(x**2 + y**2) < 0.40 and z < 0.8: return False
        return True

    def activar_paro_emergencia(self):
        if self.paro_emergencia_activo: return
        self.paro_emergencia_activo = True
        self.animacion_movimiento.stop()
        if self.modo_operacion == "AUTOMÁTICO (DEMO)":
            self.viewer_3d.set_visibilidad_caja(False)
            self.conmutar_vacio(False)
        self.modo_operacion = "FALLA (E-STOP)"
        self.viewer_3d.mostrar_alerta("PARO DE EMERGENCIA ACTIVADO")

    def resetear_falla(self):
        if self.paro_emergencia_activo:
            self.paro_emergencia_activo = False
            self.modo_operacion = "MANUAL (JOG)"
            self.viewer_3d.ocultar_alerta()

    def actualizar_estado_deadman(self, presionado):
        self.deadman_activo = presionado
        self.viewer_3d.set_deadman_state(presionado)
        if presionado and not self.paro_emergencia_activo:
            self.viewer_3d.ocultar_alerta()

    # ==========================================
    # MOVIMIENTO Y CINEMÁTICA
    # ==========================================
    def procesar_jog_click(self, joint_index, paso_grados):
        if self.paro_emergencia_activo:
            self.viewer_3d.mostrar_alerta("FALLA DE SISTEMA: PRESIONE RESET FAULT")
            return
        if not self.deadman_activo:
            self.viewer_3d.mostrar_alerta("ADVERTENCIA: PRESIONE DEADMAN (SHIFT) PARA MOVER")
            return

        self.modo_operacion = "MANUAL (JOG)"
        angulos_tentativos = list(self.current_angles_deg)
        angulos_tentativos[joint_index] += paso_grados
        
        if self.verificar_limites_seguros(angulos_tentativos):
            self.current_angles_deg[joint_index] = angulos_tentativos[joint_index]
            self.actualizar_cinematica_local()
            if self.viewer_3d.alarma_activa and "LÍMITE" in self.viewer_3d.lbl_estado.text():
                self.viewer_3d.ocultar_alerta()
        else:
            self.viewer_3d.mostrar_alerta("ADVERTENCIA: LÍMITE DE MOVIMIENTO ALCANZADO")

    def ir_a_home(self):
        if not self.deadman_activo: return
        self.modo_operacion = "AUTOMÁTICO (HOME)"
        self.angulos_inicio = list(self.current_angles_deg)
        self.angulos_destino = [0.0] * 6
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.start()

    def _ejecutar_paso_interpolacion(self, t):
        if self.paro_emergencia_activo:
            self.animacion_movimiento.stop()
            return
        if self.modo_operacion == "MANUAL (JOG)" and not self.deadman_activo:
            self.animacion_movimiento.stop()
            return
            
        angulos_paso = [0.0] * 6
        for i in range(6):
            distancia_total = self.angulos_destino[i] - self.angulos_inicio[i]
            angulos_paso[i] = self.angulos_inicio[i] + (t * distancia_total)
            
        if self.verificar_limites_seguros(angulos_paso):
            self.current_angles_deg = angulos_paso
            self.actualizar_cinematica_local()
        else:
            self.animacion_movimiento.stop()
            if self.modo_operacion == "AUTOMÁTICO (DEMO)": self.detener_demo()
            self.activar_paro_emergencia()

    def actualizar_bucle_fisico(self):
        deltas = [self.current_angles_deg[i] - self.angulos_anteriores[i] for i in range(6)]
        self.fisica_motores.simular_paso_tiempo(deltas)
        self.angulos_anteriores = list(self.current_angles_deg)
        self.actualizar_cinematica_local()

    def actualizar_cinematica_local(self):
        angulos_rad = np.radians(self.current_angles_deg)
        vector_full = [0.0] * len(self.viewer_3d.chain.links)
        vector_full[1:7] = angulos_rad 
        self.viewer_3d.actualizar_posicion_visual(vector_full)
        
        fk_matrix = self.viewer_3d.chain.forward_kinematics(vector_full)
        x_m, y_m, z_m = fk_matrix[:3, 3] 
        self.current_x, self.current_y, self.current_z = round(x_m * 1000, 2), round(y_m * 1000, 2), round(z_m * 1000, 2)
        self.viewer_3d.actualizar_tcp_ui(self.current_x, self.current_y, self.current_z)

        # Lógica Física de la Ventosa
        angulo = np.pi / 2
        rot_ajuste = np.array([[np.cos(angulo),0,np.sin(angulo),0],[0,1,0,0],[-np.sin(angulo),0,np.cos(angulo),0],[0,0,0,1]])
        ajuste_brecha = np.eye(4); ajuste_brecha[2, 3] = -0.045
        matriz_cuerpo = np.dot(fk_matrix, np.dot(rot_ajuste, ajuste_brecha))
        desplazamiento_tapa = np.eye(4); desplazamiento_tapa[2, 3] = 0.075
        matriz_ventosa = np.dot(matriz_cuerpo, desplazamiento_tapa)
        
        distancia = np.linalg.norm(matriz_ventosa[:3, 3] - self.matriz_caja_mundo[:3, 3])
        
        if self.vacio_activo and distancia < 0.40: 
            if not self.caja_agarrada:
                self.caja_agarrada, self.payload_kg = True, 15.5
                self.matriz_relativa_agarre = np.dot(np.linalg.inv(matriz_ventosa), self.matriz_caja_mundo)
        elif not self.vacio_activo:
            if self.caja_agarrada:
                self.matriz_caja_mundo = self.viewer_3d.obtener_pose_caja()
                if self.matriz_caja_mundo[2, 3] < 0.0: self.matriz_caja_mundo[2, 3] = 0.0 
                self.viewer_3d.set_pose_caja(self.matriz_caja_mundo)
            self.caja_agarrada, self.payload_kg = False, 0.0

        if self.caja_agarrada:
            self.viewer_3d.set_pose_caja(np.dot(matriz_ventosa, self.matriz_relativa_agarre))
        else:
            self.viewer_3d.set_pose_caja(self.matriz_caja_mundo)

    def conmutar_vacio(self, presionado):
        self.vacio_activo = presionado
        self.presion_vacio_kpa = -82.5 if presionado else 0.0
        self.consumo_aire_lpm = 45.0 if presionado else 0.0
        self.payload_kg = 15.5 if (presionado and self.caja_agarrada) else 0.0
        self.viewer_3d.set_vacio_visual_state(self.vacio_activo)
        if self.ui_panel: self.ui_panel.actualizar_ui_vacio(self.vacio_activo)

    # ==========================================
    # LÓGICA DE PROGRAMAS (TP / DEMO)
    # ==========================================
    def iniciar_demo(self):
        if self.paro_emergencia_activo: return 
        self.modo_operacion = "AUTOMÁTICO (DEMO)"
        self.viewer_3d.set_texto_estado_base("EJECUTANDO DEMO...")
        if self.ui_panel: self.ui_panel.actualizar_ui_demo(True)
        self.viewer_3d.set_visibilidad_caja(True)
        self.vacio_activo, self.caja_agarrada = False, False
        self.tiempo_inicio_ciclo = time.time()
        
        J_PICK, J_PLACE = [0.0, 2.0, -62.0, 0.0, -26.0, 0.0], [180.0, 2.0, -62.0, 0.0, -26.0, 0.0]
        J_APP_PICK, J_APP_PLACE = [0.0, -20.0, -40.0, 0.0, -26.0, 0.0], [180.0, -20.0, -40.0, 0.0, -26.0, 0.0]
        self.pasos_demo = [
            {"j": J_APP_PICK, "vacio": False}, {"j": J_PICK, "vacio": False}, {"j": J_PICK, "vacio": True},
            {"j": J_APP_PICK, "vacio": True}, {"j": J_APP_PLACE, "vacio": True}, {"j": J_PLACE, "vacio": True},
            {"j": J_PLACE, "vacio": False}, {"j": J_APP_PLACE, "vacio": False}
        ]
        self.matriz_caja_mundo = np.copy(self.matriz_caja_inicial)
        self.viewer_3d.set_pose_caja(self.matriz_caja_mundo)
        self.paso_actual_demo = 0
        self.ejecutar_siguiente_paso_demo()

    def detener_demo(self):
        self.modo_operacion = "MANUAL (JOG)"
        self.viewer_3d.set_texto_estado_base("ROBOT EN ESPERA")
        self.animacion_movimiento.stop()
        self.viewer_3d.set_visibilidad_caja(False)
        self.conmutar_vacio(False)
        if self.ui_panel: self.ui_panel.actualizar_ui_demo(False)

    def ejecutar_siguiente_paso_demo(self):
        if self.modo_operacion != "AUTOMÁTICO (DEMO)": return
        if self.paso_actual_demo >= len(self.pasos_demo):
            self.ciclos_completados += 1
            self.ultimo_tiempo_ciclo_seg = round(time.time() - self.tiempo_inicio_ciclo, 2)
            self.tiempo_inicio_ciclo = time.time()
            self.paso_actual_demo = 0 
            self.matriz_caja_mundo = np.copy(self.matriz_caja_inicial)
            self.viewer_3d.set_pose_caja(self.matriz_caja_mundo)

        paso = self.pasos_demo[self.paso_actual_demo]
        self.paso_actual_demo += 1
        if self.vacio_activo != paso["vacio"]:
            self.conmutar_vacio(paso["vacio"])
            QTimer.singleShot(600, self.ejecutar_siguiente_paso_demo)
            return

        self.angulos_inicio = list(self.current_angles_deg)
        self.angulos_destino = paso["j"]
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.start()

    def iniciar_secuencia_programa(self, lineas):
        if self.paro_emergencia_activo: return
        self.modo_operacion = "AUTOMÁTICO (TP RUN)"
        self.viewer_3d.set_texto_estado_base("EJECUTANDO PROGRAMA TP...")
        self.lineas_programa = lineas
        self.linea_actual_idx = 0
        self.tiempo_inicio_ciclo = time.time() 
        if not self.lineas_programa: return
        self._procesar_siguiente_linea()

    def _procesar_siguiente_linea(self):
        if self.paro_emergencia_activo: 
            self.modo_operacion = "FALLA (E-STOP)"
            return
        if self.linea_actual_idx >= len(self.lineas_programa):
            if self.ui_panel: self.ui_panel.limpiar_resaltado()
            self.ciclos_completados += 1
            self.ultimo_tiempo_ciclo_seg = round(time.time() - self.tiempo_inicio_ciclo, 2)
            self.modo_operacion = "MANUAL (JOG)"
            self.viewer_3d.set_texto_estado_base("ROBOT EN ESPERA")
            return
            
        if self.ui_panel: self.ui_panel.resaltar_linea_tp(self.linea_actual_idx)
        instruccion = self.compilador.compilar_linea(self.lineas_programa[self.linea_actual_idx])
        self.linea_actual_idx += 1
        comando = instruccion.get("comando")
        
        if comando == "MOVE":
            self.angulos_inicio = list(self.current_angles_deg)
            self.angulos_destino = instruccion["angulos"]
            self.animacion_movimiento.setDuration(instruccion["duracion_ms"])
            self.animacion_movimiento.setStartValue(0.0)
            self.animacion_movimiento.setEndValue(1.0)
            self.animacion_movimiento.start()
        elif comando == "DO":
            if instruccion.get("puerto") == 1: self.conmutar_vacio(instruccion["estado"])
            self._procesar_siguiente_linea()
        elif comando == "WAIT_TIME":
            QTimer.singleShot(instruccion["tiempo_ms"], self._procesar_siguiente_linea)
        elif comando == "WAIT_DI":
            puerto = instruccion["puerto"] - 1 
            estado_actual = self.ui_panel.leds_di[puerto].isChecked() if self.ui_panel else False
            if estado_actual == instruccion["estado"]:
                self._procesar_siguiente_linea()
            else:
                self.linea_actual_idx -= 1
                QTimer.singleShot(100, self._procesar_siguiente_linea)
        else:
            self._procesar_siguiente_linea()

    def enrutador_animacion(self):
        if self.modo_operacion == "AUTOMÁTICO (TP RUN)": self._procesar_siguiente_linea()
        elif self.modo_operacion == "AUTOMÁTICO (DEMO)": self.ejecutar_siguiente_paso_demo()

    # ==========================================
    # EXPORTACIÓN DE TELEMETRÍA (PARA SCADA Y WEBSOCKETS)
    # ==========================================
    def obtener_estado_diccionario(self):
        return {
            "x": self.current_x, "y": self.current_y, "z": self.current_z,
            "j1": self.current_angles_deg[0], "j2": self.current_angles_deg[1],
            "j3": self.current_angles_deg[2], "j4": self.current_angles_deg[3],
            "j5": self.current_angles_deg[4], "j6": self.current_angles_deg[5],
            "vacio_activo": self.vacio_activo, "presion_kpa": self.presion_vacio_kpa, "payload_kg": self.payload_kg,
            "corrientes_a": list(self.fisica_motores.corrientes), "temperaturas_c": list(self.fisica_motores.temperaturas),
            "ciclos_total": self.ciclos_completados, "tiempo_ciclo_s": self.ultimo_tiempo_ciclo_seg,
            "modo_operacion": self.modo_operacion,
            "seguridad": {"deadman": self.deadman_activo, "e_stop": self.paro_emergencia_activo}
        }