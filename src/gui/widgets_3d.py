import os
import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QLabel, QGroupBox, QGridLayout, QHBoxLayout)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QVector3D, QFont, QIcon
import pyqtgraph.opengl as gl
from stl import mesh

class RobotViewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ==========================================
        # CALIBRACIÓN DEL STL DE LA VENTOSA
        # ==========================================
        self.ventosa_offset_x = 0.06  
        self.ventosa_offset_y = 0.0
        self.ventosa_offset_z = 0.0
        
        self.ventosa_rot_x = 180
        self.ventosa_rot_y = 90
        self.ventosa_rot_z = 0
        # ==========================================
        
        layout_principal = QGridLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        self.canvas = gl.GLViewWidget()
        self.canvas.setBackgroundColor((40, 44, 52))
        layout_principal.addWidget(self.canvas, 0, 0)

        # ==========================================
        # BARRA DE ESTADO INDUSTRIAL Y DEADMAN
        # ==========================================
        contenedor_estado = QWidget()
        contenedor_estado.setAttribute(Qt.WA_TransparentForMouseEvents) 
        layout_estado = QVBoxLayout(contenedor_estado)
        layout_estado.setContentsMargins(15, 15, 0, 0)
        layout_estado.setSpacing(10)

        self.lbl_estado = QLabel("Standby")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setFixedWidth(450)

        self.lbl_deadman = QLabel("DEADMAN SWITCH: RELEASED")
        self.lbl_deadman.setAlignment(Qt.AlignCenter)
        self.lbl_deadman.setFixedWidth(450)

        layout_estado.addWidget(self.lbl_estado)
        layout_estado.addWidget(self.lbl_deadman)
        
        layout_principal.addWidget(contenedor_estado, 0, 0, Qt.AlignTop | Qt.AlignLeft)
        
        self.timer_alarma = QTimer(self)
        self.timer_alarma.timeout.connect(self._animar_alarma)
        self.alarma_activa = False
        self.fase_alarma = False
        self.nivel_alarma = "OK"

        self.ocultar_alerta()
        self.set_deadman_state(False)

        # ==========================================
        # PANELES DE TELEMETRÍA TCP Y PUNTOS
        # ==========================================
        self.group_tcp = QGroupBox("Posición Cartesiana (TCP)")
        self.group_tcp.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #5c6370; border-radius: 6px; 
                background-color: rgba(30, 30, 30, 220); 
                margin-top: 15px; margin-right: 15px; padding-top: 15px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 10px; padding: 0 5px; 
                color: #abb2bf; font-weight: bold; font-size: 14px; 
            }
        """)
        self.group_tcp.setMaximumHeight(150)
        
        layout_tcp = QGridLayout(self.group_tcp)
        layout_tcp.setSpacing(8)
        layout_tcp.setContentsMargins(15, 15, 15, 10)
        font_mono = QFont("Consolas", 13, QFont.Bold)
        
        def crear_fila_tcp(fila, eje_letra):
            lbl_letra = QLabel(f"{eje_letra}:")
            lbl_letra.setStyleSheet("color: white; background: transparent;")
            lbl_letra.setFont(font_mono)
            lbl_valor = QLabel("0.00")
            lbl_valor.setStyleSheet("color: #e5c07b; background: transparent;")
            lbl_valor.setFont(font_mono)
            lbl_valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_valor.setMinimumWidth(80) 
            lbl_unidad = QLabel("mm")
            lbl_unidad.setStyleSheet("color: white; background: transparent;")
            lbl_unidad.setFont(font_mono)
            layout_tcp.addWidget(lbl_letra, fila, 0)
            layout_tcp.addWidget(lbl_valor, fila, 1)
            layout_tcp.addWidget(lbl_unidad, fila, 2)
            return lbl_valor

        self.lbl_tcp_x = crear_fila_tcp(0, "X")
        self.lbl_tcp_y = crear_fila_tcp(1, "Y")
        self.lbl_tcp_z = crear_fila_tcp(2, "Z")

        contenedor_overlay = QWidget()
        layout_overlay = QHBoxLayout(contenedor_overlay)
        layout_overlay.setContentsMargins(0, 0, 15, 0)
        
        layout_overlay.addWidget(self.group_tcp)
        
        self.group_puntos = QGroupBox("Posiciones Guardadas")
        self.group_puntos.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #5c6370; border-radius: 6px; 
                background-color: rgba(30, 30, 30, 220); 
                margin-top: 15px; padding-top: 15px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 10px; padding: 0 5px; 
                color: #abb2bf; font-weight: bold; font-size: 14px; 
            }
        """)
        self.group_puntos.setMaximumHeight(150)
        layout_puntos = QVBoxLayout(self.group_puntos)
        layout_puntos.setContentsMargins(10, 15, 10, 10)
        
        from PySide6.QtWidgets import QListWidget
        self.lista_puntos = QListWidget()
        self.lista_puntos.setStyleSheet("background-color: transparent; color: #98c379; font-family: Consolas; font-size: 13px; border: none;")
        self.lista_puntos.setFixedWidth(200)
        layout_puntos.addWidget(self.lista_puntos)
        
        layout_overlay.addWidget(self.group_puntos)
        layout_principal.addWidget(contenedor_overlay, 0, 0, Qt.AlignTop | Qt.AlignRight)

        # ==========================================
        # BARRA DE HERRAMIENTAS DE CÁMARA
        # ==========================================
        self.toolbar_vista = QWidget()
        self.toolbar_vista.setFixedWidth(55)
        self.toolbar_vista.setStyleSheet("background-color: rgba(44, 49, 58, 200); border-radius: 6px; margin-right: 15px;")
        layout_toolbar = QVBoxLayout(self.toolbar_vista)
        layout_toolbar.setContentsMargins(5, 10, 5, 10)
        layout_toolbar.setSpacing(15)

        style_btn = """
            QPushButton { background-color: #404552; border: 1px solid #1e2227; border-radius: 6px; padding: 5px; }
            QPushButton:hover { background-color: #528bff; }
            QPushButton:pressed { background-color: #28a745; }
        """
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        icons_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "icons"))

        btn_home, btn_fit, btn_zoom_in, btn_zoom_out, self.btn_info = [QPushButton() for _ in range(5)]
        iconos = ["home.svg", "fit.svg", "zoom_in.svg", "zoom_out.svg", "info.svg"]
        
        for i, btn in enumerate([btn_home, btn_fit, btn_zoom_in, btn_zoom_out, self.btn_info]):
            btn.setIcon(QIcon(os.path.join(icons_path, iconos[i])))
            btn.setStyleSheet(style_btn)
            btn.setIconSize(QSize(24, 24)) 
            btn.setFixedSize(45, 45)       
            layout_toolbar.addWidget(btn)
            
        btn_home.clicked.connect(self.view_home)
        btn_fit.clicked.connect(self.view_fit)
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out.clicked.connect(self.zoom_out)
        
        layout_principal.addWidget(self.toolbar_vista, 0, 0, Qt.AlignVCenter | Qt.AlignRight)

        # ==========================================
        # ENTORNO 3D Y CARGA DE MALLAS
        # ==========================================
        grid = gl.GLGridItem()
        grid.setSize(x=10, y=10, z=10)
        grid.setSpacing(x=0.5, y=0.5, z=0.5)
        self.canvas.addItem(grid)
        
        longitud_eje = 0.3
        eje_x = gl.GLLinePlotItem(pos=np.array([[0,0,0], [longitud_eje,0,0]]), color=(1,0,0,1), width=3, antialias=True)
        eje_y = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,longitud_eje,0]]), color=(0,1,0,1), width=3, antialias=True)
        eje_z = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,longitud_eje]]), color=(0.2,0.6,1,1), width=3, antialias=True) 
        for eje in (eje_x, eje_y, eje_z):
            eje.setDepthValue(1000) 
            self.canvas.addItem(eje)

        self.mallas_visuales = []
        self.cargar_mallas_principales()
        self.view_home()

    # ==========================================
    # MÉTODOS DE LA INTERFAZ
    # ==========================================
    def set_deadman_state(self, presionado):
        if presionado:
            self.lbl_deadman.setText("DEADMAN SWITCH: READY")
            self.lbl_deadman.setStyleSheet("""
                background-color: #28a745; color: white; font-weight: bold; 
                padding: 10px; border-radius: 4px; font-family: Consolas; font-size: 14px;
                border: 1px solid #1e7e34;
            """)
        else:
            self.lbl_deadman.setText("DEADMAN SWITCH: RELEASED")
            self.lbl_deadman.setStyleSheet("""
                background-color: #dc3545; color: white; font-weight: bold; 
                padding: 10px; border-radius: 4px; font-family: Consolas; font-size: 14px;
                border: 1px solid #c82333;
            """)        
    
    def actualizar_tcp_ui(self, x, y, z):
        self.lbl_tcp_x.setText(f"{x:.2f}")
        self.lbl_tcp_y.setText(f"{y:.2f}")
        self.lbl_tcp_z.setText(f"{z:.2f}")

    def zoom_in(self): self.canvas.setCameraPosition(distance=max(self.canvas.opts['distance'] * 0.8, 0.1))
    def zoom_out(self): self.canvas.setCameraPosition(distance=min(self.canvas.opts['distance'] * 1.25, 20.0))
    def view_home(self): self.canvas.setCameraPosition(distance=9.0, elevation=25, azimuth=45, pos=QVector3D(0, 0, 1.0))
    def view_fit(self): self.canvas.setCameraPosition(distance=5.5, elevation=self.canvas.opts['elevation'], azimuth=self.canvas.opts['azimuth'], pos=QVector3D(0, 0, 1.2))

    def cargar_mallas_principales(self):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "meshes"))
        
        eslabones_ordenados = [
            ("Base link", "base_link.stl"),
            ("joint_1", "link_1.stl"),
            ("joint_2", "link_2.stl"),
            ("joint_3", "link_3.stl"),
            ("joint_4", "link_4.stl"),
            ("joint_5", "link_5.stl"),
            ("joint_6", "link_6.stl")
        ]
        
        for i, (nombre_link, archivo_stl) in enumerate(eslabones_ordenados):
            stl_path = os.path.join(base_path, archivo_stl)
            if os.path.exists(stl_path):
                try:
                    stl_data = mesh.Mesh.from_file(stl_path)
                    raw_vectors = stl_data.vectors.reshape(-1, 3)
                    rounded_vectors = np.round(raw_vectors, 6) 
                    vertices, caras = np.unique(rounded_vectors, axis=0, return_inverse=True)
                    caras = caras.reshape(-1, 3)
                    mesh_data = gl.MeshData(vertexes=vertices, faces=caras)
                    
                    color_mesh = (0.4, 0.4, 0.42, 1.0) if nombre_link in ["Base link", "joint_6", "joint_4", "joint_2"] else (1.0, 0.85, 0.1, 1.0)
                    
                    item = gl.GLMeshItem(meshdata=mesh_data, smooth=True, computeNormals=True, color=color_mesh, shader='shaded')
                    self.canvas.addItem(item)
                    
                    self.mallas_visuales.append({"item": item, "joint_index": i})
                except Exception as e:
                    print(f"Error cargando {nombre_link}: {e}")
                    
        try:
            ventosa_path = os.path.join(base_path, "ventosa.stl")
            if os.path.exists(ventosa_path):
                stl_ventosa = mesh.Mesh.from_file(ventosa_path)
                raw_vectors = stl_ventosa.vectors.reshape(-1, 3)
                
                escala_ventosa = 0.05
                raw_vectors = raw_vectors * escala_ventosa
                
                rounded_vectors = np.round(raw_vectors, 6) 
                vertices, caras = np.unique(rounded_vectors, axis=0, return_inverse=True)
                caras = caras.reshape(-1, 3)
                mesh_data = gl.MeshData(vertexes=vertices, faces=caras)
                
                self.item_ventosa = gl.GLMeshItem(meshdata=mesh_data, smooth=True, color=(0.4, 0.4, 0.4, 1.0), shader='shaded')
                self.canvas.addItem(self.item_ventosa)
        except Exception as e:
            print(f"[VENTOSA ERROR] No se pudo cargar el STL: {e}")

    def actualizar_posicion_visual(self, matrices_transformacion):
        if not self.mallas_visuales or matrices_transformacion is None: return
        
        for malla in self.mallas_visuales:
            malla["item"].setTransform(matrices_transformacion[malla["joint_index"]])
            
        if hasattr(self, 'item_ventosa') and len(matrices_transformacion) >= 3:
            matriz_brida = matrices_transformacion[-3] 
            
            rot_x = np.radians(self.ventosa_rot_x)
            rot_y = np.radians(self.ventosa_rot_y)
            rot_z = np.radians(self.ventosa_rot_z)
            
            Rx = np.array([[1, 0, 0, 0], [0, np.cos(rot_x), -np.sin(rot_x), 0], [0, np.sin(rot_x), np.cos(rot_x), 0], [0, 0, 0, 1]])
            Ry = np.array([[np.cos(rot_y), 0, np.sin(rot_y), 0], [0, 1, 0, 0], [-np.sin(rot_y), 0, np.cos(rot_y), 0], [0, 0, 0, 1]])
            Rz = np.array([[np.cos(rot_z), -np.sin(rot_z), 0, 0], [np.sin(rot_z), np.cos(rot_z), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
            
            T = np.eye(4)
            T[0, 3] = self.ventosa_offset_x
            T[1, 3] = self.ventosa_offset_y
            T[2, 3] = self.ventosa_offset_z
            
            matriz_ajuste_local = np.dot(T, np.dot(Rz, np.dot(Ry, Rx)))
            matriz_ventosa_stl = np.dot(matriz_brida, matriz_ajuste_local)
            
            self.item_ventosa.setTransform(matriz_ventosa_stl)

    def set_vacio_visual_state(self, activo):
        if hasattr(self, 'item_ventosa'):
            color = (0.0, 0.8, 0.2, 1.0) if activo else (0.4, 0.4, 0.4, 1.0)
            self.item_ventosa.setColor(color)
            
    # ==========================================
    # MOTOR DE BARRA DE ESTADO (ALARMAS)
    # ==========================================
    def mostrar_alerta(self, mensaje):
        self.lbl_estado.setText(mensaje)
        self.alarma_activa = True
        
        # Inferencia de prioridad
        if "FALLA" in mensaje.upper() or "EMERGENCIA" in mensaje.upper():
            self.nivel_alarma = "CRIT"
        else:
            self.nivel_alarma = "WARN"
            
        if not self.timer_alarma.isActive():
            self.fase_alarma = True
            self._animar_alarma() 
            self.timer_alarma.start(800)

    def ocultar_alerta(self):
        self.timer_alarma.stop()
        self.alarma_activa = False
        self.nivel_alarma = "OK"
        self.texto_estado_base = "ROBOT EN ESPERA"
        self.lbl_estado.setText(self.texto_estado_base)
        self.lbl_estado.setStyleSheet("""
            background-color: transparent; 
            color: rgba(152, 195, 121, 150);
            font-weight: bold; 
            padding: 10px; 
            font-family: Consolas; font-size: 14px;
            border: none;
        """)

    def _animar_alarma(self):
        if not self.alarma_activa: return
        self.fase_alarma = not self.fase_alarma
        
        if self.nivel_alarma == "CRIT":
            bg = "#ff0000" if self.fase_alarma else "#8b0000"
            fg = "white"
            border = "#ff4d4d" if self.fase_alarma else "#5c0000"
        else:
            bg = "#ffc107" if self.fase_alarma else "#b38600"
            fg = "black"
            border = "#ffeeba" if self.fase_alarma else "#806000"
            
        self.lbl_estado.setStyleSheet(f"""
            background-color: {bg}; color: {fg}; font-weight: bold; 
            padding: 10px; border-radius: 4px; font-family: Consolas; font-size: 14px;
            border: 2px solid {border};
        """)
        
    def set_texto_estado_base(self, texto):
        self.texto_estado_base = texto
        if not self.alarma_activa:
            self.lbl_estado.setText(texto)
            
    def cargar_caja_entorno(self):
        import os
        import numpy as np
        from stl import mesh
        import pyqtgraph.opengl as gl
        
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        caja_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "meshes", "caja.stl"))
        
        try:
            if os.path.exists(caja_path):
                stl_caja = mesh.Mesh.from_file(caja_path)
                raw_vectors = stl_caja.vectors.reshape(-1, 3) * 0.2
                vertices, caras = np.unique(np.round(raw_vectors, 6), axis=0, return_inverse=True)
                md_caja = gl.MeshData(vertexes=vertices, faces=caras.reshape(-1, 3))
                
                self.caja_visual = gl.GLMeshItem(meshdata=md_caja, smooth=False, color=(0.8, 0.5, 0.2, 1.0), shader='shaded')
                self.canvas.addItem(self.caja_visual)
                self.caja_visual.setVisible(False)
                print("[3D Viewer] Caja STL cargada correctamente.")
            else:
                print("[ADVERTENCIA] No se encontró caja.stl.")
        except Exception as e:
            print(f"[CAJA ERROR] Falló la carga del STL: {e}")

    def set_pose_caja(self, matriz_4x4):
        if hasattr(self, 'caja_visual'):
            self.caja_visual.setTransform(matriz_4x4)
            
    def obtener_pose_caja(self):
        import numpy as np
        if hasattr(self, 'caja_visual'):
            return np.copy(self.caja_visual.transform().matrix())
        return np.eye(4)

    def set_visibilidad_caja(self, visible):
        if hasattr(self, 'caja_visual'):
            self.caja_visual.setVisible(visible)