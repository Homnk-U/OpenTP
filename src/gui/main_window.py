import numpy as np
from functools import partial
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGroupBox, QLabel, QApplication, QTextEdit
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from gui.widgets_3d import RobotViewer3D
from core.tp_compiler import TPCompiler

class PanelControlIndustrial(QWidget):
    def __init__(self, viewer_3d, parent=None):
        super().__init__(parent)
        self.viewer_3d = viewer_3d 
        layout_principal = QVBoxLayout(self)
        
        self.current_angles_deg = [0.0] * 6 
        self.deadman_activo = False # Variable de estado en tiempo real
        # --- INICIALIZAR EL CEREBRO DEL COMPILADOR ---
        self.compilador = TPCompiler()
        self.siguiente_id_punto = 1 # Empezaremos grabando el P[1]
        
        estilo_botones_industrial = """
            QPushButton { 
                background-color: #333333; color: white; 
                font-weight: bold; padding: 8px; border: 1px solid #1a1a1a; border-radius: 4px;
            }
            QPushButton:pressed { background-color: #28a745; }
        """

        # ==========================================
        # 1. ZONA DE POSICIÓN CARTESIANA (Estilo Terminal)
        # ==========================================
        grupo_tcp = QGroupBox("Posición Cartesiana (TCP)")
        grupo_tcp.setStyleSheet("QGroupBox { color: #4caf50; font-weight: bold; }")
        layout_tcp = QVBoxLayout(grupo_tcp)
        
        estilo_labels_tcp = "font-family: Consolas, monospace; font-size: 14px; color: #e0e0e0; margin: 2px;"
        self.lbl_tcp_x = QLabel("X:  0.00 mm")
        self.lbl_tcp_y = QLabel("Y:  0.00 mm")
        self.lbl_tcp_z = QLabel("Z:  0.00 mm")
        
        for lbl in (self.lbl_tcp_x, self.lbl_tcp_y, self.lbl_tcp_z):
            lbl.setStyleSheet(estilo_labels_tcp)
            layout_tcp.addWidget(lbl)
            
        layout_principal.addWidget(grupo_tcp)
        
        # ==========================================
        # 1.5 PANTALLA DEL iPendant (Editor de Código)
        # ==========================================
        grupo_editor = QGroupBox("Programa TP (Editor)")
        layout_editor = QVBoxLayout(grupo_editor)
        
        self.editor_codigo = QTextEdit()
        self.editor_codigo.setStyleSheet("background-color: white; color: black; font-family: Consolas; font-size: 14px;")
        self.editor_codigo.setPlaceholderText("Ejemplo:\nJ P[1] 100% FINE\nJ P[2] 100% FINE")
        layout_editor.addWidget(self.editor_codigo)
        
        self.btn_ejecutar = QPushButton("▶ EJECUTAR PROGRAMA (F3)")
        self.btn_ejecutar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_ejecutar.clicked.connect(self.iniciar_secuencia_programa)
        layout_editor.addWidget(self.btn_ejecutar)
        
        layout_principal.addWidget(grupo_editor)

        # ==========================================
        # 2. ZONA DE JOGGING Y BOTÓN HOME
        # ==========================================
        grupo_jog = QGroupBox("Control Manual (Jog)")
        layout_jog = QGridLayout(grupo_jog)
        
        # --- NUEVO: Botón de Home ---
        self.btn_home = QPushButton("HOME")
        self.btn_home.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 8px;")
        self.btn_home.clicked.connect(self.ir_a_home)
        layout_jog.addWidget(self.btn_home, 0, 0, 1, 2) # Ocupa las 2 columnas
        
        etiquetas_botones = [
            ("-X (J1)", "+X (J1)"), ("-Y (J2)", "+Y (J2)"), ("-Z (J3)", "+Z (J3)"),
            ("-X(W) (J4)", "+X(W) (J4)"), ("-Y(P) (J5)", "+Y(P) (J5)"), ("-Z(R) (J6)", "+Z(R) (J6)")
        ]
        
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
            
            # Sumamos 1 a la fila porque el botón Home está en la fila 0
            layout_jog.addWidget(btn_neg, fila + 1, 0)
            layout_jog.addWidget(btn_pos, fila + 1, 1)
            
        layout_principal.addWidget(grupo_jog)
        
        # ==========================================
        # 2.5 ZONA DE MEMORIA Y COMPILADOR (TEACH)
        # ==========================================
        grupo_memoria = QGroupBox("Memoria de Puntos (Teach)")
        layout_memoria = QVBoxLayout(grupo_memoria)
        
        self.btn_grabar_punto = QPushButton(f"Grabar P[{self.siguiente_id_punto}]")
        # Estilo amarillo clásico de las teclas especiales de FANUC
        self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_grabar_punto.clicked.connect(self.grabar_punto_actual)
        
        layout_memoria.addWidget(self.btn_grabar_punto)
        layout_principal.addWidget(grupo_memoria)
        
        # ==========================================
        # 3. ZONA DE ENTRADAS DIGITALES
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
            
        layout_principal.addWidget(grupo_di)
        
        # ==========================================
        # 4. INDICADOR DEL DEADMAN SWITCH (Dinámico)
        # ==========================================
        self.lbl_deadman = QLabel("Deadman Switch: Mantén presionado [Shift]")
        self.lbl_deadman.setAlignment(Qt.AlignCenter)
        self.lbl_deadman.setStyleSheet("color: #ff9800; font-style: italic; font-weight: bold; margin-top: 10px;")
        layout_principal.addWidget(self.lbl_deadman)
        
        layout_principal.addStretch()
        
        # Inicializar cálculos de TCP
        self.actualizar_robot_y_tcp()
    
        # ==========================================
        # 5. MOTOR DE INTERPOLACIÓN DE TRAYECTORIAS
        # ==========================================
        self.animacion_movimiento = QVariantAnimation(self)
        self.animacion_movimiento.setDuration(2000) # El viaje tomará exactamente 2 segundos (2000 ms)
        
        # InOutQuad simula las rampas de aceleración y frenado de un servomotor real
        self.animacion_movimiento.setEasingCurve(QEasingCurve.InOutQuad) 
        
        # Cada que el reloj avanza, llama a nuestra función matemática
        self.animacion_movimiento.valueChanged.connect(self._ejecutar_paso_interpolacion)
        
        # Avisa cuando el robot llega a su destino para leer la siguiente línea
        self.animacion_movimiento.finished.connect(self._procesar_siguiente_linea)
        
        # Variables para controlar la ejecución del programa
        self.lineas_programa = []
        self.linea_actual_idx = 0
        
        # Variables para recordar de dónde salimos y a dónde vamos
        self.angulos_inicio = [0.0] * 6
        self.angulos_destino = [0.0] * 6

    # --- LÓGICA DE ACTUALIZACIÓN VISUAL ---
    def actualizar_estado_deadman(self, presionado):
        """Llamado en tiempo real cuando el teclado detecta Shift"""
        self.deadman_activo = presionado
        if presionado:
            self.lbl_deadman.setStyleSheet("color: #28a745; font-weight: bold; margin-top: 10px;")
            self.lbl_deadman.setText("DEADMAN ACTIVO (Listo para mover)")
        else:
            self.lbl_deadman.setStyleSheet("color: #ff9800; font-style: italic; font-weight: bold; margin-top: 10px;")
            self.lbl_deadman.setText("Deadman Switch: Mantén presionado [Shift]")

    def ir_a_home(self):
        """Prepara las coordenadas y arranca el viaje suave hacia ceros"""
        if not self.deadman_activo:
            self.lbl_deadman.setStyleSheet("color: #dc3545; font-weight: bold; background-color: #f8d7da; margin-top: 10px;")
            return
            
        # 1. Guardar la "Foto" de dónde estamos ahora
        self.angulos_inicio = list(self.current_angles_deg)
        
        # 2. Definir a dónde vamos (Home = todo en 0)
        self.angulos_destino = [0.0] * 6
        
        # 3. Arrancar la animación desde t=0.0 (0%) hasta t=1.0 (100%)
        self.animacion_movimiento.setStartValue(0.0)
        self.animacion_movimiento.setEndValue(1.0)
        self.animacion_movimiento.start()

    def _ejecutar_paso_interpolacion(self, t):
        """Calcula los ángulos intermedios. 't' va de 0.0 a 1.0"""
        
        # ¡FRENO DE EMERGENCIA INDUSTRIAL!
        # Si el operador suelta la tecla Shift durante el viaje automático, paramos los motores.
        if not self.deadman_activo:
            self.animacion_movimiento.stop()
            return
            
        # Calcular el nuevo ángulo para cada uno de los 6 motores
        for i in range(6):
            distancia_total = self.angulos_destino[i] - self.angulos_inicio[i]
            self.current_angles_deg[i] = self.angulos_inicio[i] + (t * distancia_total)
            
        # Mover el modelo 3D y actualizar los números en pantalla
        self.actualizar_robot_y_tcp()

    def procesar_jog_click(self, joint_index, paso_grados):
        # Ahora usamos el estado en tiempo real
        if not self.deadman_activo:
            self.lbl_deadman.setStyleSheet("color: #dc3545; font-weight: bold; background-color: #f8d7da; margin-top: 10px;")
            return
        
        NUEVO_ANGULO = self.current_angles_deg[joint_index] + paso_grados
        limites = [180, 75, 120, 360, 125, 360]
        if abs(NUEVO_ANGULO) > limites[joint_index]:
            return 

        self.current_angles_deg[joint_index] = NUEVO_ANGULO
        self.actualizar_robot_y_tcp()
        
    def actualizar_robot_y_tcp(self):
        """Calcula cinemática, mueve el 3D y extrae el TCP"""
        angulos_rad = np.radians(self.current_angles_deg)
        len_cadena = len(self.viewer_3d.chain.links)
        vector_full = [0.0] * len_cadena
        vector_full[1:7] = angulos_rad 
        
        # 1. Actualizar modelo 3D
        self.viewer_3d.actualizar_posicion_visual(vector_full)
        
        # 2. Calcular y mostrar TCP Cartesiano (X, Y, Z) usando la matriz 4x4
        # El método forward_kinematics devuelve la matriz del efector final
        fk_matrix = self.viewer_3d.chain.forward_kinematics(vector_full)
        x_m, y_m, z_m = fk_matrix[:3, 3] # Extrae el vector de traslación en metros
        
        # Actualizar etiquetas convirtiendo a milímetros
        self.lbl_tcp_x.setText(f"X: {x_m * 1000:8.2f} mm")
        self.lbl_tcp_y.setText(f"Y: {y_m * 1000:8.2f} mm")
        self.lbl_tcp_z.setText(f"Z: {z_m * 1000:8.2f} mm")
        
    def grabar_punto_actual(self):
        """Toma la posición actual y la manda al disco duro del compilador"""
        # 1. Mandar guardar al core
        self.compilador.guardar_punto(self.siguiente_id_punto, self.current_angles_deg)
        
        # 2. Incrementar el contador (Para que el siguiente sea P[2], P[3]...)
        self.siguiente_id_punto += 1
        
        # 3. Actualizar el texto del botón en la interfaz
        self.btn_grabar_punto.setText(f"Grabar P[{self.siguiente_id_punto}]")
        
        # Opcional: Un pequeño destello verde en el botón para confirmar que se guardó
        self.btn_grabar_punto.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        
        # Regresar el color al amarillo después de medio segundo usando un QTimer en línea
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self.btn_grabar_punto.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px; border-radius: 4px;"))
        
    def iniciar_secuencia_programa(self):
        """Lee el texto del editor y arranca el programa"""
        if not self.deadman_activo:
            self.lbl_deadman.setStyleSheet("color: #dc3545; font-weight: bold; background-color: #f8d7da; margin-top: 10px;")
            return
            
        texto = self.editor_codigo.toPlainText()
        # Separamos el texto línea por línea ignorando las vacías
        self.lineas_programa = [linea.strip() for linea in texto.split('\n') if linea.strip()]
        self.linea_actual_idx = 0
        
        if not self.lineas_programa:
            return
            
        print("\n[TP] --- INICIANDO PROGRAMA ---")
        self._procesar_siguiente_linea()

    def _procesar_siguiente_linea(self):
        """Lee la instrucción actual y mueve el robot. Si termina, lee la siguiente."""
        if not self.deadman_activo:
            print("[TP] Programa abortado: Se soltó el Deadman Switch.")
            return

        # Si ya leímos todas las líneas, el programa terminó
        if self.linea_actual_idx >= len(self.lineas_programa):
            print("[TP] --- FIN DEL PROGRAMA ---")
            return
            
        linea_actual = self.lineas_programa[self.linea_actual_idx].upper()
        self.linea_actual_idx += 1
        
        print(f"[TP] Ejecutando: {linea_actual}")
        
        # --- PARSEO BÁSICO ---
        # Buscamos si la línea contiene un punto, por ejemplo "P[1]"
        if "P[" in linea_actual:
            inicio = linea_actual.find("P[")
            fin = linea_actual.find("]", inicio) + 1
            nombre_punto = linea_actual[inicio:fin]
            
            # Pedimos los ángulos a nuestra memoria (TPCompiler)
            angulos_destino = self.compilador.obtener_punto(nombre_punto)
            
            if angulos_destino:
                # Reciclamos tu motor de interpolación para ir a ese punto
                self.angulos_inicio = list(self.current_angles_deg)
                self.angulos_destino = angulos_destino
                
                self.animacion_movimiento.setStartValue(0.0)
                self.animacion_movimiento.setEndValue(1.0)
                self.animacion_movimiento.start()
            else:
                # Si el punto no existe, nos saltamos a la siguiente línea
                self._procesar_siguiente_linea()
        else:
            # Si es un comando que no reconocemos, pasamos al siguiente
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
        layout_principal.addWidget(self.visor_3d, stretch=3) 
        
        self.panel_control = PanelControlIndustrial(viewer_3d=self.visor_3d) 
        layout_principal.addWidget(self.panel_control, stretch=1)
        
        # --- FOCUS PARA EL TECLADO ---
        self.setFocusPolicy(Qt.StrongFocus)

    # ==========================================
    # EVENTOS DE TECLADO EN TIEMPO REAL (Interrupciones)
    # ==========================================
    def keyPressEvent(self, event):
        # isAutoRepeat evita que el panel parpadee si dejas la tecla presionada mucho tiempo
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self.panel_control.actualizar_estado_deadman(True)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self.panel_control.actualizar_estado_deadman(False)
        super().keyReleaseEvent(event)