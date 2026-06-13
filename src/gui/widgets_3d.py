import os
import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QLabel, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QVector3D, QFont, QIcon
import pyqtgraph.opengl as gl
import ikpy.chain
from stl import mesh

class RobotViewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ==========================================
        # EL TRUCO DEL OVERLAY (Sobreposición)
        # ==========================================
        layout_principal = QGridLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        # 1. EL FONDO (Lienzo 3D)
        self.canvas = gl.GLViewWidget()
        self.canvas.setBackgroundColor((40, 44, 52))
        layout_principal.addWidget(self.canvas, 0, 0)

        # 2. FLOTANTE SUPERIOR IZQUIERDO: Deadman Switch
        self.lbl_deadman = QLabel("DEADMAN SWITCH: RELEASED")
        self.lbl_deadman.setStyleSheet("""
            background-color: #dc3545; color: white; font-weight: bold; 
            padding: 8px 15px; border-radius: 4px; font-family: Arial; font-size: 14px;
            margin-top: 15px; margin-left: 15px;
        """)
        layout_principal.addWidget(self.lbl_deadman, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        # 3. FLOTANTE SUPERIOR DERECHO: Recuadro TCP
        self.group_tcp = QGroupBox("Posición Cartesiana (TCP)")
        self.group_tcp.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #5c6370; border-radius: 6px; 
                background-color: rgba(30, 30, 30, 220); 
                margin-top: 15px; margin-right: 15px; padding-top: 15px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 10px; padding: 0 5px; 
                color: #abb2bf; /* <-- Color Gris Claro para el Título */
                font-weight: bold; font-size: 14px; 
            }
        """)
        
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

        layout_principal.addWidget(self.group_tcp, 0, 0, Qt.AlignTop | Qt.AlignRight)

        # 4. FLOTANTE CENTRO DERECHA: Botones de Cámara (Iconos)
        self.toolbar_vista = QWidget()
        self.toolbar_vista.setFixedWidth(55)
        self.toolbar_vista.setStyleSheet("background-color: rgba(44, 49, 58, 200); border-radius: 6px; margin-right: 15px;")
        layout_toolbar = QVBoxLayout(self.toolbar_vista)
        layout_toolbar.setContentsMargins(5, 10, 5, 10)
        layout_toolbar.setSpacing(15)

        style_btn = """
            QPushButton { 
                background-color: #404552; border: 1px solid #1e2227; 
                border-radius: 6px; padding: 5px; 
            }
            QPushButton:hover { background-color: #528bff; }
            QPushButton:pressed { background-color: #28a745; }
        """

        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        icons_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "icons"))

        btn_home = QPushButton()
        btn_home.setIcon(QIcon(os.path.join(icons_path, "home.svg")))
        
        btn_fit = QPushButton()
        btn_fit.setIcon(QIcon(os.path.join(icons_path, "fit.svg")))
        
        btn_zoom_in = QPushButton()
        btn_zoom_in.setIcon(QIcon(os.path.join(icons_path, "zoom_in.svg")))
        
        btn_zoom_out = QPushButton()
        btn_zoom_out.setIcon(QIcon(os.path.join(icons_path, "zoom_out.svg")))
        
        self.btn_info = QPushButton()
        self.btn_info.setIcon(QIcon(os.path.join(icons_path, "info.svg"))) 
        
        for btn in (btn_home, btn_fit, btn_zoom_in, btn_zoom_out, self.btn_info):
            btn.setStyleSheet(btn.styleSheet() + style_btn) # Mantiene el estilo base
            btn.setIconSize(QSize(24, 24)) 
            btn.setFixedSize(45, 45)       
            layout_toolbar.addWidget(btn)
            
        btn_home.clicked.connect(self.view_home)
        btn_fit.clicked.connect(self.view_fit)
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out.clicked.connect(self.zoom_out)
        
        layout_principal.addWidget(self.toolbar_vista, 0, 0, Qt.AlignVCenter | Qt.AlignRight)

        # ==========================================
        # ENTORNO 3D (Mallas y Líneas)
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

        # ==========================================
        # CARGA DE CINEMÁTICA Y MALLAS (Lo que se había borrado)
        # ==========================================
        try:
            mascara_activos = [False, True, True, True, True, True, True, False, False]
            self.chain = ikpy.chain.Chain.from_urdf_file("src/assets/models/robot_fanuc.urdf", active_links_mask=mascara_activos)
        except Exception as e:
            print(f"[ERROR 3D] Falló la carga del URDF: {e}")
            self.chain = None

        self.mallas_visuales = []
        if self.chain:
            self.cargar_mallas_principales()
            self.actualizar_posicion_visual([0.0] * len(self.chain.links))
            self.view_home()

    # ==========================================
    # FUNCIONES DE INTERFAZ PÚBLICAS
    # ==========================================
    def set_deadman_state(self, presionado):
        if presionado:
            self.lbl_deadman.setText("DEADMAN SWITCH: READY")
            self.lbl_deadman.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; font-family: Arial; font-size: 14px; margin-top: 15px; margin-left: 15px;")
        else:
            self.lbl_deadman.setText("DEADMAN SWITCH: RELEASED")
            self.lbl_deadman.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; font-family: Arial; font-size: 14px; margin-top: 15px; margin-left: 15px;")

    def actualizar_tcp_ui(self, x, y, z):
        self.lbl_tcp_x.setText(f"{x:.2f}")
        self.lbl_tcp_y.setText(f"{y:.2f}")
        self.lbl_tcp_z.setText(f"{z:.2f}")

    # ==========================================
    # CONTROL DE CÁMARA
    # ==========================================
    def zoom_in(self):
        self.canvas.setCameraPosition(distance=max(self.canvas.opts['distance'] * 0.8, 0.1))

    def zoom_out(self):
        self.canvas.setCameraPosition(distance=min(self.canvas.opts['distance'] * 1.25, 20.0))

    def view_home(self):
        self.canvas.setCameraPosition(distance=9.0, elevation=25, azimuth=45, pos=QVector3D(0, 0, 1.0))

    def view_fit(self):
        self.canvas.setCameraPosition(distance=5.5, elevation=self.canvas.opts['elevation'], azimuth=self.canvas.opts['azimuth'], pos=QVector3D(0, 0, 1.2))

    # ==========================================
    # CARGA DE STL
    # ==========================================
    def cargar_mallas_principales(self):
            directorio_actual = os.path.dirname(os.path.abspath(__file__))
            base_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "meshes"))
            mapeo_links = {
                "Base link": "base_link.stl", 
                "joint_1": "link_1.stl", 
                "joint_2": "link_2.stl", 
                "joint_3": "link_3.stl", 
                "joint_4": "link_4.stl", 
                "joint_5": "link_5.stl", 
                "joint_6": "link_6.stl"
            }
            
            for i, link in enumerate(self.chain.links):
                if link.name in mapeo_links:
                    stl_path = os.path.join(base_path, mapeo_links[link.name])
                    if os.path.exists(stl_path):
                        try:
                            stl_data = mesh.Mesh.from_file(stl_path)
                            raw_vectors = stl_data.vectors.reshape(-1, 3)
                            rounded_vectors = np.round(raw_vectors, 6) 
                            vertices, caras = np.unique(rounded_vectors, axis=0, return_inverse=True)
                            caras = caras.reshape(-1, 3)
                            mesh_data = gl.MeshData(vertexes=vertices, faces=caras)
                            
                            dibujar_aristas = False
                            color_aristas = (0.2, 0.2, 0.2, 0.5)
                            
                            if link.name in ["Base link", "joint_6", "joint_4", "joint_2"]:
                                color_mesh = (0.4, 0.4, 0.42, 1.0) 
                                if link.name == "joint_6":
                                    dibujar_aristas = True
                            else:
                                color_mesh = (1.0, 0.85, 0.1, 1.0)
                                
                            item = gl.GLMeshItem(meshdata=mesh_data, smooth=True, computeNormals=True, 
                                                drawEdges=dibujar_aristas, edgeColor=color_aristas, 
                                                color=color_mesh, shader='shaded')
                            self.canvas.addItem(item)
                            self.mallas_visuales.append({"item": item, "joint_index": i})
                        except Exception as e:
                            print(f"Error cargando {link.name}: {e}")
                            
            # Crear geométricamente la ventosa
            try:
                # 1. Vástago: longitud 0.04
                md_cuerpo = gl.MeshData.cylinder(rows=10, cols=20, radius=[0.015, 0.015], length=0.04)
                self.item_ventosa_cuerpo = gl.GLMeshItem(meshdata=md_cuerpo, smooth=True, color=(0.6, 0.6, 0.6, 1.0), shader='shaded')
                
                # 2. Copa (Paredes laterales): Más grande, se abre hasta 0.08 (8 cm)
                # Color inicial: Rojo (0.8, 0.1, 0.1)
                md_copa = gl.MeshData.cylinder(rows=10, cols=30, radius=[0.015, 0.08], length=0.035)
                self.item_ventosa_copa = gl.GLMeshItem(meshdata=md_copa, smooth=True, color=(0.8, 0.1, 0.1, 1.0), shader='shaded')
                
                # 3. Tapa frontal: Cierra la copa reduciendo el radio de 0.08 a 0.0 para que se vea "rellena"
                md_tapa = gl.MeshData.cylinder(rows=2, cols=30, radius=[0.08, 0.0], length=0.001)
                self.item_ventosa_tapa = gl.GLMeshItem(meshdata=md_tapa, smooth=True, color=(0.8, 0.1, 0.1, 1.0), shader='shaded')
                
                self.canvas.addItem(self.item_ventosa_cuerpo)
                self.canvas.addItem(self.item_ventosa_copa)
                self.canvas.addItem(self.item_ventosa_tapa)
            except Exception as e:
                print(f"[VENTOSA ERROR] No se pudo inicializar la geometría: {e}")

    def actualizar_posicion_visual(self, joints_angles):
        if not self.chain or not self.mallas_visuales: return
        transformaciones = self.chain.forward_kinematics(joints_angles, full_kinematics=True)
        
        # Mover las mallas del robot (J1 a J6)
        for malla in self.mallas_visuales:
            malla["item"].setTransform(transformaciones[malla["joint_index"]])
            
        # Mover la ventosa acoplada rígidamente al extremo final
        if hasattr(self, 'item_ventosa_cuerpo') and hasattr(self, 'item_ventosa_copa'):
            matriz_final = transformaciones[-3] # El plato de acoplamiento
            
            # 1. Rotación 90° en Y para que apunte al frente
            angulo = np.pi / 2
            rotacion_ajuste = np.array([
                [np.cos(angulo),  0, np.sin(angulo), 0],
                [0,               1, 0,              0],
                [-np.sin(angulo), 0, np.cos(angulo), 0],
                [0,               0, 0,              1]
            ])
            
            # 2. AJUSTE DE BRECHA
            ajuste_brecha = np.eye(4)
            ajuste_brecha[2, 3] = -0.045 
            
            # Matriz del cuerpo
            matriz_cuerpo = np.dot(matriz_final, np.dot(rotacion_ajuste, ajuste_brecha))
            self.item_ventosa_cuerpo.setTransform(matriz_cuerpo)
            
            # Matriz de la copa (se desplaza la longitud del vástago: 0.04)
            desplazamiento_copa = np.eye(4)
            desplazamiento_copa[2, 3] = 0.04 
            matriz_copa = np.dot(matriz_cuerpo, desplazamiento_copa)
            self.item_ventosa_copa.setTransform(matriz_copa)
            
            # Matriz de la tapa (se desplaza la longitud del vástago + la longitud de la copa: 0.04 + 0.035)
            desplazamiento_tapa = np.eye(4)
            desplazamiento_tapa[2, 3] = 0.075
            matriz_tapa = np.dot(matriz_cuerpo, desplazamiento_tapa)
            self.item_ventosa_tapa.setTransform(matriz_tapa)

    def set_vacio_visual_state(self, activo):
        if hasattr(self, 'item_ventosa_copa') and hasattr(self, 'item_ventosa_tapa'):
            # Verde si está activo, Rojo si está desactivado
            color = (0.0, 0.8, 0.2, 1.0) if activo else (0.8, 0.1, 0.1, 1.0)
            self.item_ventosa_copa.setColor(color)
            self.item_ventosa_tapa.setColor(color)