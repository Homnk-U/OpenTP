import os
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QThread, Signal, Qt
import pyqtgraph.opengl as gl
import ikpy.chain
from stl import mesh

# --- 1. EL HILO TRABAJADOR (BACKGROUND WORKER) ---
class HiloCargadorRobot(QThread):
    """Hilo secundario encargado de procesar la geometría pesada sin congelar la app."""
    # Señal que emitirá (objeto chain, lista de datos de mallas procesadas)
    carga_terminada = Signal(object, list)

    def __init__(self, ruta_urdf, base_path, mapeo_links):
        super().__init__()
        self.ruta_urdf = ruta_urdf
        self.base_path = base_path
        self.mapeo_links = mapeo_links

    def run(self):
        try:
            # 1. Carga asíncrona de la cadena cinemática
            chain = ikpy.chain.Chain.from_urdf_file(self.ruta_urdf)
            mallas_datos = []
            
            # 2. Procesamiento matemático pesado de vectores de los STL
            for i, link in enumerate(chain.links):
                if link.name in self.mapeo_links:
                    stl_name = self.mapeo_links[link.name]
                    stl_path = os.path.join(self.base_path, stl_name)
                    
                    if os.path.exists(stl_path):
                        try:
                            stl_data = mesh.Mesh.from_file(stl_path)
                            vertices = stl_data.vectors.reshape(-1, 3)
                            caras = np.arange(vertices.shape[0]).reshape(-1, 3)
                            
                            # Guardamos los vectores listos para OpenGL en memoria temporal
                            mallas_datos.append({
                                "joint_index": i,
                                "name": link.name,
                                "vertices": vertices,
                                "caras": caras,
                                "stl_name": stl_name
                            })
                        except Exception as e:
                            print(f"[Thread Error] Falló preprocesar {stl_name}: {e}")
            
            # Enviamos los datos procesados de vuelta al hilo principal
            self.carga_terminada.emit(chain, mallas_datos)
            
        except Exception as e:
            print(f"[Thread Error Crítico] Falló carga de robot: {e}")
            self.carga_terminada.emit(None, [])


# --- 2. EL COMPONENTE VISUAL REESTRUCTURADO ---
class RobotViewer3D(QWidget):
    # Señal para avisar a la MainWindow que cree los sliders dinámicos
    robot_listo_interfaz = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chain = None
        self.mallas_visuales = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Etiqueta temporal estática de carga
        self.lbl_cargando = QLabel("⌛ Cargando modelo geométrico 3D (FANUC M-900iA)...")
        self.lbl_cargando.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cargando.setStyleSheet("color: #ffb86c; font-family: 'Consolas', monospace; font-size: 14px; background-color: #282c34;")
        layout.addWidget(self.lbl_cargando)
        
        # 1. Configurar lienzo OpenGL de inmediato
        self.canvas = gl.GLViewWidget()
        self.canvas.setCameraPosition(distance=4.0, elevation=25, azimuth=45)
        self.canvas.setBackgroundColor((40, 44, 52))
        
        grid = gl.GLGridItem()
        grid.setSize(x=10, y=10, z=10)
        grid.setSpacing(x=0.5, y=0.5, z=0.5)
        self.canvas.addItem(grid)
        
        # Configurar rutas y mapeos para el hilo
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_urdf = os.path.abspath(os.path.join(directorio_actual, "..", "assets", "models", "robot_fanuc.urdf"))
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
        
        # --- 2. DISPARAR LA OPTIMIZACIÓN POR HILO ---
        self.hilo = HiloCargadorRobot(ruta_urdf, base_path, mapeo_links)
        self.hilo.carga_terminada.connect(self.inyectar_robot_al_entorno)
        self.hilo.start()

    def inyectar_robot_al_entorno(self, chain_procesada, mallas_datos):
        """Se ejecuta en el hilo principal de PySide cuando el hilo secundario termina."""
        if not chain_procesada:
            self.lbl_cargando.setText("❌ Error al cargar la configuración cinemática.")
            return
            
        self.chain = chain_procesada
        
        # Quitamos el label de carga e inyectamos el canvas de golpe
        self.lbl_cargando.deleteLater()
        self.layout().addWidget(self.canvas)
        
        # Inyectar las mallas precalculadas directamente a OpenGL
        for datos in mallas_datos:
            mesh_data = gl.MeshData(vertexes=datos["vertices"], faces=datos["caras"])
            
            if datos["name"] == "Base link":
                color_mesh = (0.2, 0.2, 0.22, 1.0)
            else:
                color_mesh = (0.96, 0.76, 0.13, 1.0) # Amarillo FANUC
                
            item = gl.GLMeshItem(
                meshdata=mesh_data, 
                smooth=True, 
                drawEdges=True,                  
                edgeColor=(0.3, 0.2, 0.0, 0.3),  
                color=color_mesh,
                shader='shaded'                  
            )
            
            self.canvas.addItem(item)
            self.mallas_visuales.append({"item": item, "joint_index": datos["joint_index"], "name": datos["name"]})
            
        # Sincronizamos a la posición 0° inicial
        self.actualizar_posicion_visual([0.0] * len(self.chain.links))
        
        # Avisamos a la ventana principal que active los sliders dinámicos
        self.robot_listo_interfaz.emit()

    def actualizar_posicion_visual(self, joints_angles):
        if not self.chain or not self.mallas_visuales:
            return
        transformaciones = self.chain.forward_kinematics(joints_angles, full_kinematics=True)
        for malla in self.mallas_visuales:
            idx = malla["joint_index"]
            item = malla["item"]
            item.setTransform(transformaciones[idx])