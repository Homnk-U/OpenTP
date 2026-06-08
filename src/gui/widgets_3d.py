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
        self.toolbar_vista.setFixedWidth(55) # Barra delgada
        self.toolbar_vista.setStyleSheet("background-color: #2c313a; border-left: 1px solid #1e2227;")
        layout_toolbar = QVBoxLayout(self.toolbar_vista)
        layout_toolbar.setContentsMargins(5, 10, 5, 10)
        layout_toolbar.setSpacing(15)

        # Estilo para botones cuadrados y oscuros
        style_btn = """
            QPushButton { 
                background-color: #404552; border: 1px solid #1e2227; color: white;
                font-weight: bold; font-size: 16px; border-radius: 6px; padding: 12px 0px;
            }
            QPushButton:hover { background-color: #528bff; }
            QPushButton:pressed { background-color: #28a745; }
        """

        # Crear botones
        btn_home = QPushButton("HOME")
        btn_fit = QPushButton("FIT")
        btn_zoom_in = QPushButton("+")
        btn_zoom_out = QPushButton("-")
        
        # Aplicar estilo
        btn_home.setStyleSheet(style_btn)
        btn_fit.setStyleSheet(style_btn + "font-size: 12px;")
        btn_zoom_in.setStyleSheet(style_btn)
        btn_zoom_out.setStyleSheet(style_btn)
        
        # Conectar funciones
        btn_home.clicked.connect(self.view_home)
        btn_fit.clicked.connect(self.view_fit)
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out.clicked.connect(self.zoom_out)
        
        # Acomodar arriba y empujar hacia arriba
        layout_toolbar.addWidget(btn_home)
        layout_toolbar.addWidget(btn_fit)
        layout_toolbar.addWidget(btn_zoom_in)
        layout_toolbar.addWidget(btn_zoom_out)
        layout_toolbar.addStretch()
        
        self.layout_principal.addWidget(self.toolbar_vista)

        # ==========================================
        # 2. ENTORNO 3D (Piso y Coordenadas 3D Reales)
        # ==========================================
        grid = gl.GLGridItem()
        grid.setSize(x=10, y=10, z=10)
        grid.setSpacing(x=0.5, y=0.5, z=0.5)
        self.canvas.addItem(grid)
        
        # --- Ejes Gruesos ---
        longitud_eje = 0.3
        grosor = 3
        
        eje_x = gl.GLLinePlotItem(pos=np.array([[0,0,0], [longitud_eje,0,0]]), color=(1,0,0,1), width=grosor, antialias=True)
        eje_y = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,longitud_eje,0]]), color=(0,1,0,1), width=grosor, antialias=True)
        eje_z = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,longitud_eje]]), color=(0.2,0.6,1,1), width=grosor, antialias=True) 
        
        for eje in (eje_x, eje_y, eje_z):
            eje.setDepthValue(1000) 
            self.canvas.addItem(eje)
        
        # --- Letras Flotantes 3D ---
        try:
            from pyqtgraph.opengl import GLTextItem
            fuente_ejes = QFont("Consolas", 8, QFont.Bold)
            
            # Colocamos las letras un poquito más adelante de la punta de cada línea
            lbl_x = GLTextItem(pos=[longitud_eje + 0.15, 0, 0], text="X", color=(255, 50, 50, 255), font=fuente_ejes)
            lbl_y = GLTextItem(pos=[0, longitud_eje + 0.15, 0], text="Y", color=(50, 255, 50, 255), font=fuente_ejes)
            lbl_z = GLTextItem(pos=[0, 0, longitud_eje + 0.15], text="Z", color=(100, 150, 255, 255), font=fuente_ejes)
            
            for lbl in (lbl_x, lbl_y, lbl_z):
                lbl.setDepthValue(1000)
                self.canvas.addItem(lbl)
        except ImportError:
            print("[Advertencia] Versión de pyqtgraph no soporta GLTextItem.")

        # ==========================================
        # 3. CARGA DE CINEMÁTICA Y MALLAS
        # ==========================================
        try:
            # Máscara booleana para los 9 eslabones: 
            # [Base, J1, J2, J3, J4, J5, J6, Flange, Tool0]
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
            self.view_home() # <-- Arrancamos viendo al robot de lejos

    # ==========================================
    # CONTROL DE CÁMARA
    # ==========================================
    def zoom_in(self):
        opts = self.canvas.opts
        self.canvas.setCameraPosition(distance=max(opts['distance'] * 0.8, 0.1))

    def zoom_out(self):
        opts = self.canvas.opts
        self.canvas.setCameraPosition(distance=min(opts['distance'] * 1.25, 20.0))

    def view_home(self):
        """Vista Isométrica alejada para ver todo el brazo"""
        # Distance=9.0 (más lejos) y center apuntando a Z=1.0m (el vientre del robot)
        self.canvas.setCameraPosition(distance=9.0, elevation=25, azimuth=45, pos=QVector3D(0, 0, 1.0))

    def view_fit(self):
        """Ajusta el zoom para que el robot ocupe toda la ventana sin importar de dónde lo mires"""
        opts = self.canvas.opts
        
        # Un FANUC M-900iA encaja perfectamente en una distancia focal de ~5.5 metros.
        # Apuntamos el centro de la cámara exactamente a la mitad de su altura (Z=1.2 metros)
        self.canvas.setCameraPosition(
            distance=5.5,
            elevation=opts['elevation'],
            azimuth=opts['azimuth'],
            pos=QVector3D(0, 0, 1.2)
        )
    # ==========================================
    # Superficies Lisas sin Facetas
    # ==========================================
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
                        # 1. Cargar el STL
                        stl_data = mesh.Mesh.from_file(stl_path)
                        
                        # Fusionar vértices duplicados
                        # Esto es necesario para que 'smooth=True' funcione en archivos STL
                        raw_vectors = stl_data.vectors.reshape(-1, 3)
                        rounded_vectors = np.round(raw_vectors, 6) 
                        vertices, caras = np.unique(rounded_vectors, axis=0, return_inverse=True)
                        caras = caras.reshape(-1, 3)
                        
                        mesh_data = gl.MeshData(vertexes=vertices, faces=caras)
                        
                        dibujar_aristas = False
                        color_aristas = (0.2, 0.2, 0.2, 0.5)
                        
                        # 3. Lógica de colores
                        if link.name in ["Base link", "joint_6", "joint_4", "joint_2"]:
                            color_mesh = (0.4, 0.4, 0.42, 1.0) 
                            if link.name == "joint_6":
                                dibujar_aristas = True
                                color_aristas = (0.2, 0.2, 0.2, 0.5)
                        else:
                            color_mesh = (1.0, 0.85, 0.1, 1.0)
                            
                        # 4. Inyectar con smooth=True y computeNormals=True
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

    def actualizar_posicion_visual(self, joints_angles):
        if not self.chain or not self.mallas_visuales:
            return
        transformaciones = self.chain.forward_kinematics(joints_angles, full_kinematics=True)
        for malla in self.mallas_visuales:
            malla["item"].setTransform(transformaciones[malla["joint_index"]])