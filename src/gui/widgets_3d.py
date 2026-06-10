import os
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D, QFont
import pyqtgraph.opengl as gl
import ikpy.chain
from stl import mesh

class RobotViewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ==========================================
        # 1. LAYOUT HORIZONTAL (Canvas Izq | Botones Der)
        # ==========================================
        self.layout_principal = QHBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0) 

        # --- Zona de Canvas OpenGL ---
        self.canvas = gl.GLViewWidget()
        self.canvas.setBackgroundColor((40, 44, 52))
        self.layout_principal.addWidget(self.canvas, stretch=1) 
        
        # --- Zona de Botones ---
        self.toolbar_vista = QWidget()
        self.toolbar_vista.setFixedWidth(55) 
        self.toolbar_vista.setStyleSheet("background-color: #2c313a; border-left: 1px solid #1e2227;")
        layout_toolbar = QVBoxLayout(self.toolbar_vista)
        layout_toolbar.setContentsMargins(5, 10, 5, 10)
        layout_toolbar.setSpacing(15)

        style_btn = """
            QPushButton { 
                background-color: #404552; border: 1px solid #1e2227; color: white;
                font-weight: bold; font-size: 16px; border-radius: 6px; padding: 12px 0px;
            }
            QPushButton:hover { background-color: #528bff; }
            QPushButton:pressed { background-color: #28a745; }
        """

        btn_home = QPushButton("HOME")
        btn_fit = QPushButton("FIT")
        btn_zoom_in = QPushButton("+")
        btn_zoom_out = QPushButton("-")
        
        btn_home.setStyleSheet(style_btn)
        btn_fit.setStyleSheet(style_btn + "font-size: 12px;")
        btn_zoom_in.setStyleSheet(style_btn)
        btn_zoom_out.setStyleSheet(style_btn)
        
        btn_home.clicked.connect(self.view_home)
        btn_fit.clicked.connect(self.view_fit)
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out.clicked.connect(self.zoom_out)
        
        layout_toolbar.addWidget(btn_home)
        layout_toolbar.addWidget(btn_fit)
        layout_toolbar.addWidget(btn_zoom_in)
        layout_toolbar.addWidget(btn_zoom_out)
        layout_toolbar.addStretch()
        
        self.layout_principal.addWidget(self.toolbar_vista)

# ==========================================
        # 2. ENTORNO 3D (Piso y Coordenadas con Letras)
        # ==========================================
        grid = gl.GLGridItem()
        grid.setSize(x=10, y=10, z=10)
        grid.setSpacing(x=0.5, y=0.5, z=0.5)
        self.canvas.addItem(grid)
        
        # Fuente compacta para las etiquetas industriales
        fuente_ejes = QFont("Consolas", 10, QFont.Weight.Bold)
        
        # --- CONFIGURACIÓN ORIGEN (WORLD) ---
        self.eje_origen = gl.GLAxisItem()
        self.eje_origen.setSize(x=0.6, y=0.6, z=0.6)
        # Desplazamos un milímetro en Z para evitar el z-fighting (parpadeo) con el piso gris
        self.eje_origen.translate(0, 0, 0.001)
        self.canvas.addItem(self.eje_origen)
        
        # Letras para el Origen
        self.txt_w_x = gl.GLTextItem(text="X (World)", font=fuente_ejes, color=(255, 100, 100, 255))
        self.txt_w_y = gl.GLTextItem(text="Y (World)", font=fuente_ejes, color=(100, 255, 100, 255))
        self.txt_w_z = gl.GLTextItem(text="Z (World)", font=fuente_ejes, color=(100, 100, 255, 255))
        
        # Posicionamos las letras en las puntas de los vectores del origen
        self.txt_w_x.setData(pos=np.array([0.6, 0.0, 0.0]))
        self.txt_w_y.setData(pos=np.array([0.0, 0.6, 0.0]))
        self.txt_w_z.setData(pos=np.array([0.0, 0.0, 0.6]))
        
        for txt in [self.txt_w_x, self.txt_w_y, self.txt_w_z]:
            self.canvas.addItem(txt)
        
        # --- CONFIGURACIÓN GRIPPER (TOOL/TCP) ---
        self.eje_gripper = gl.GLAxisItem()
        self.eje_gripper.setSize(x=0.4, y=0.4, z=0.4) 
        self.canvas.addItem(self.eje_gripper)
        
        # Letras para el Gripper
        self.txt_t_x = gl.GLTextItem(text="X (Tool)", font=fuente_ejes, color=(255, 50, 50, 255))
        self.txt_t_y = gl.GLTextItem(text="Y (Tool)", font=fuente_ejes, color=(50, 255, 50, 255))
        self.txt_t_z = gl.GLTextItem(text="Z (Tool)", font=fuente_ejes, color=(50, 50, 255, 255))
        
        for txt in [self.txt_t_x, self.txt_t_y, self.txt_t_z]:
            self.canvas.addItem(txt)

        # ==========================================
        # 3. CARGA DE CINEMÁTICA Y MALLAS
        # ==========================================
        try:
            mascara_activos = [False, True, True, True, True, True, True, False, False]
            self.chain = ikpy.chain.Chain.from_urdf_file(
                "src/assets/models/robot_fanuc.urdf",
                active_links_mask=mascara_activos
            )
        except Exception as e:
            print(f"[ERROR 3D] Falló la carga del URDF: {e}")
            self.chain = None

        self.mallas_visuales = []
        
        if self.chain:
            self.cargar_mallas_principales()
            self.actualizar_posicion_visual([0.0] * len(self.chain.links))
            self.view_home()

    # CONTROL DE CÁMARA
    def zoom_in(self):
        opts = self.canvas.opts
        self.canvas.setCameraPosition(distance=max(opts['distance'] * 0.8, 0.1))

    def zoom_out(self):
        opts = self.canvas.opts
        self.canvas.setCameraPosition(distance=min(opts['distance'] * 1.25, 20.0))

    def view_home(self):
        self.canvas.setCameraPosition(distance=9.0, elevation=25, azimuth=45, pos=QVector3D(0, 0, 1.0))

    def view_fit(self):
        opts = self.canvas.opts
        self.canvas.setCameraPosition(distance=5.5, elevation=opts['elevation'], azimuth=opts['azimuth'], pos=QVector3D(0, 0, 1.2))

    # Carga de archivos STL
    def cargar_mallas_principales(self):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "meshes"))
        
        mapeo_links = {
            "Base link": "base_link.stl", "joint_1": "link_1.stl", "joint_2": "link_2.stl",
            "joint_3": "link_3.stl", "joint_4": "link_4.stl", "joint_5": "link_5.stl", "joint_6": "link_6.stl"
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
                            
                        item = gl.GLMeshItem(
                            meshdata=mesh_data, 
                            smooth=True,
                            computeNormals=True,
                            drawEdges=dibujar_aristas, 
                            edgeColor=color_aristas, 
                            color=color_mesh, 
                            shader='shaded'
                        )
                        
                        self.canvas.addItem(item)
                        self.mallas_visuales.append({"item": item, "joint_index": i})
                    except Exception as e:
                        print(f"Error cargando {link.name}: {e}")

    def alternar_visibilidad_ejes(self, mostrar_origen, mostrar_gripper):
        self.eje_origen.setVisible(mostrar_origen)
        self.txt_w_x.setVisible(mostrar_origen)
        self.txt_w_y.setVisible(mostrar_origen)
        self.txt_w_z.setVisible(mostrar_origen)
        
        self.eje_gripper.setVisible(mostrar_gripper)
        self.txt_t_x.setVisible(mostrar_gripper)
        self.txt_t_y.setVisible(mostrar_gripper)
        self.txt_t_z.setVisible(mostrar_gripper)


    # MÉTODO ACTUALIZADO: Hace que las letras del Gripper viajen y roten junto al robot
    def actualizar_posicion_visual(self, joints_angles):
        if not self.chain:
            return
            
        transformaciones = self.chain.forward_kinematics(joints_angles, full_kinematics=True)
        
        # Mover las mallas del robot
        for malla in self.mallas_visuales:
            idx = malla["joint_index"]
            malla["item"].setTransform(transformaciones[idx])
            
        # Orientar y posicionar el eje físico del Gripper (Brida/Link 6)
        matriz_tcp = transformaciones[-1]
        self.eje_gripper.setTransform(matriz_tcp)
        
        # Extraer la posición XYZ actual de la matriz para colocar las letras flotantes
        pos_tcp = matriz_tcp[:3, 3] # Coordenadas en metros (x, y, z) de la punta
        rot_tcp = matriz_tcp[:3, :3] # Matriz de rotación 3x3 del gripper
        
        # Calculamos la posición de las puntas de los vectores del gripper rotados en el espacio
        # Tamaño del vector del gripper = 0.4 metros
        offset_x = pos_tcp + rot_tcp.dot([0.4, 0.0, 0.0])
        offset_y = pos_tcp + rot_tcp.dot([0.0, 0.4, 0.0])
        offset_z = pos_tcp + rot_tcp.dot([0.0, 0.0, 0.4])
        
        # Actualizamos las posiciones de las etiquetas en tiempo real
        self.txt_t_x.setData(pos=offset_x)
        self.txt_t_y.setData(pos=offset_y)
        self.txt_t_z.setData(pos=offset_z)