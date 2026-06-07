import os
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph.opengl as gl
import ikpy.chain
from stl import mesh

class RobotViewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Configurar lienzo OpenGL
        self.canvas = gl.GLViewWidget()
        layout.addWidget(self.canvas)
        self.canvas.setCameraPosition(distance=4.0, elevation=25, azimuth=45)
        
        # --- Color de fondo ---
        self.canvas.setBackgroundColor((40, 44, 52))
        
        # Piso (Cuadrícula)
        grid = gl.GLGridItem()
        grid.setSize(x=10, y=10, z=10)
        grid.setSpacing(x=0.5, y=0.5, z=0.5)
        
        # --- Opcional, para suavizar el color de la cuadrícula ---
        # grid.setColor((150, 150, 150, 100)) # Gris claro semitransparente
        
        self.canvas.addItem(grid)
        
        # 2. Cargar la cadena cinemática con ikpy
        try:
            self.chain = ikpy.chain.Chain.from_urdf_file("src/assets/models/robot_fanuc.urdf")
            print(f"[3D] URDF cargado con éxito.")
        except Exception as e:
            print(f"[ERROR 3D] Falló la carga del URDF: {e}")
            self.chain = None

        self.mallas_visuales = []
        
        # 3. Cargar mallas e inicializar posición
        if self.chain:
            self.cargar_mallas_principales()
            self.actualizar_posicion_visual([0.0] * len(self.chain.links))

    def cargar_mallas_principales(self):
        """
        Mapea con precisión quirúrgica los eslabones físicos seriales del URDF.
        Utiliza rutas absolutas para evitar que Python se pierda al buscar los STL.
        """
        # 1. Obtenemos la ruta real de este archivo (src/gui/widgets_3d.py)
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        # 2. Navegamos hacia atrás a 'src' y entramos a la carpeta de mallas
        base_path = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "meshes"))
        
        print(f"\n[DEBUG 3D] Buscando archivos STL exactamente en la carpeta:\n -> {base_path}\n")
        
        # Diccionario: "Nombre del joint en ikpy" -> "Archivo físico STL"
        mapeo_links = {
            "Base link": "base_link.stl",  # ikpy siempre pone la B mayúscula y espacio
            "joint_1": "link_1.stl",
            "joint_2": "link_2.stl",
            "joint_3": "link_3.stl",
            "joint_4": "link_4.stl",
            "joint_5": "link_5.stl",
            "joint_6": "link_6.stl"
        }
        
        for i, link in enumerate(self.chain.links):
            if link.name in mapeo_links:
                stl_name = mapeo_links[link.name]
                stl_path = os.path.join(base_path, stl_name)
                
                if os.path.exists(stl_path):
                    try:
                        # 1. Leemos el archivo STL 
                        stl_data = mesh.Mesh.from_file(stl_path)
                        
                        # 2. Extraemos geometría
                        vertices = stl_data.vectors.reshape(-1, 3)
                        caras = np.arange(vertices.shape[0]).reshape(-1, 3)
                        mesh_data = gl.MeshData(vertexes=vertices, faces=caras)
                        
                        # 3. Colores industriales
                        if link.name == "Base link":
                            color_mesh = (0.2, 0.2, 0.22, 1.0) # Gris oscuro base
                        else:
                            color_mesh = (0.96, 0.76, 0.13, 1.0) # Amarillo FANUC
                            
                        # 4. Renderizado Seguro con 'shaded' y aristas de detalle
                        item = gl.GLMeshItem(
                            meshdata=mesh_data, 
                            smooth=True, 
                            drawEdges=True,                  # Encendemos las aristas para dar relieve mecánico
                            edgeColor=(0.3, 0.2, 0.0, 0.3),  # Aristas oscuras y muy transparentes
                            color=color_mesh,
                            shader='shaded'                  # Sombreado dinámico básico
                        )
                        
                        # Inyectar al lienzo
                        self.canvas.addItem(item)
                        self.mallas_visuales.append({"item": item, "joint_index": i, "name": link.name})
                        print(f"[3D] Geometría inyectada con éxito: {link.name} -> {stl_name}")
                        
                    except Exception as e:
                        print(f"[3D Error] Falló la inyección de {stl_name}: {e}")
                else:
                    print(f"[ALERTA] No se encontró el archivo físico en: {stl_path}")

    def actualizar_posicion_visual(self, joints_angles):
        if not self.chain or not self.mallas_visuales:
            return
            
        # Calcular la cinemática directa (Matrices absolutas 4x4)
        transformaciones = self.chain.forward_kinematics(joints_angles, full_kinematics=True)
        
        # Posicionar cada STL usando su matriz correspondiente sin desfasamientos
        for malla in self.mallas_visuales:
            idx = malla["joint_index"]
            item = malla["item"]
            
            # Extraemos la matriz calculada para ese eslabón específico
            matriz_kinematics = transformaciones[idx]
            
            # Aplicar transformación directa en OpenGL
            item.setTransform(matriz_kinematics)