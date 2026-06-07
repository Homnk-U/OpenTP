import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph.opengl as gl
import ikpy.chain

class RobotViewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.canvas = gl.GLViewWidget()
        layout.addWidget(self.canvas)
        self.canvas.setCameraPosition(distance=5.0, elevation=30, azimuth=45)
        
        grid = gl.GLGridItem()
        grid.setSize(x=10, y=10, z=10)
        grid.setSpacing(x=1, y=1, z=1)
        self.canvas.addItem(grid)
        
        try:
            self.chain = ikpy.chain.Chain.from_urdf_file("src/assets/models/robot_fanuc.urdf")
            print(f"[3D] URDF cargado con éxito. Links: {len(self.chain.links)}")
        except Exception as e:
            print(f"[ERROR 3D] No se pudo cargar el URDF: {e}")
            self.chain = None

        # Lista donde guardaremos los cilindros para poder moverlos después
        self.cilindros_visuales = []
        
        # Inicializar el dibujo en posición home
        if self.chain:
            self.actualizar_posicion_visual([0.0] * len(self.chain.links))

    def actualizar_posicion_visual(self, joints_angles):
        if not self.chain:
            return
            
        # 1. Limpiar los cilindros anteriores
        for cilindro in self.cilindros_visuales:
            self.canvas.removeItem(cilindro)
        self.cilindros_visuales.clear()
        
        # 2. Calcular la cinemática directa (Matrices 4x4 de cada eslabón)
        transformaciones = self.chain.forward_kinematics(joints_angles, full_kinematics=True)
        
        # 3. Dibujar las mallas orientadas por matriz
        for i in range(len(transformaciones) - 1):
            m1 = transformaciones[i]
            m2 = transformaciones[i+1]
            
            # Puntos de inicio y fin de este eslabón
            p1 = m1[:3, 3]
            p2 = m2[:3, 3]
            
            vector = p2 - p1
            longitud = np.linalg.norm(vector)
            
            # Saltamos eslabones virtuales o vacíos
            if longitud < 0.01:
                continue
                
            # Definir grosor según el eslabón (gordo abajo, delgado arriba)
            radio = max(0.20 - (i * 0.025), 0.06)
            
            # Crear la malla cilíndrica nativa
            malla_datos = gl.MeshData.cylinder(rows=12, cols=12, radius=[radio, radio], length=longitud)
            cilindro = gl.GLMeshItem(meshdata=malla_datos, smooth=True, drawEdges=True, 
                                     color=(0.95, 0.7, 0.0, 1.0), edgeColor=(0.5, 0.4, 0.0, 1.0))
            
            # --- CONSTRUIR LA MATRIZ DE TRANSFORMACIÓN GRÁFICA ---
            # En lugar de rotar y trasladar a ciegas, aplicamos la matriz de orientación 
            # que calcula cómo alinear el cilindro nativo (eje Z) con el vector real del robot.
            z_axis = np.array([0, 0, 1])
            v_norm = vector / longitud
            cos_angle = np.dot(z_axis, v_norm)
            
            # Matriz de transformación final para este cilindro específico
            matriz_final = np.eye(4)
            
            if cos_angle < 0.999:
                axis = np.cross(z_axis, v_norm)
                norm_axis = np.linalg.norm(axis)
                if norm_axis > 0.001:
                    axis = axis / norm_axis
                    angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
                    
                    # Matriz de rotación Rodrigues básica
                    K = np.array([[0, -axis[2], axis[1]],
                                  [axis[2], 0, -axis[0]],
                                  [-axis[1], axis[0], 0]])
                    R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * np.dot(K, K)
                    matriz_final[:3, :3] = R
            
            # La base del cilindro debe arrancar exactamente en el punto de la articulación p1
            matriz_final[:3, 3] = p1
            
            # Le cargamos la matriz completa de 4x4 al objeto de OpenGL de PyQtGraph
            cilindro.setTransform(matriz_final)
            
            # Añadir al lienzo
            self.canvas.addItem(cilindro)
            self.cilindros_visuales.append(cilindro)