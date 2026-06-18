import os
import sys
import numpy as np
import ikpy.chain

class KinematicsEngine:
    def __init__(self):
        print("\n[BACKEND] --- Inicializando Motor Cinemático ---")
        
        # Resolución robusta de la ruta del URDF (apta para PyInstaller)
        if hasattr(sys, '_MEIPASS'):
            ruta_raiz = sys._MEIPASS
        else:
            ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        ruta_urdf = os.path.join(ruta_raiz, "assets", "models", "robot_fanuc.urdf")
        
        try:
            # Máscara para ignorar links virtuales en el URDF
            mascara_activos = [False, True, True, True, True, True, True, False, False]
            self.chain = ikpy.chain.Chain.from_urdf_file(ruta_urdf, active_links_mask=mascara_activos)
            print("[BACKEND] URDF cargado y cadena cinemática lista.")
        except Exception as e:
            print(f"[ERROR CINEMÁTICA] Falló la carga del URDF en {ruta_urdf}: {e}")
            self.chain = None

    def calcular_cinematica_directa(self, angulos_deg):
        """
        Recibe 6 ángulos en grados, los convierte a la estructura del URDF
        y devuelve las matrices de transformación de cada link.
        """
        if not self.chain:
            return None
            
        # Convertimos de Grados a Radianes
        angulos_rad = np.radians(angulos_deg)
        
        # El URDF de ikpy requiere un vector del tamaño exacto de TODOS los links (incluyendo inactivos)
        vector_full = [0.0] * len(self.chain.links)
        vector_full[1:7] = angulos_rad # Insertamos J1-J6 en las posiciones correctas
        
        # Calculamos la Cinemática Directa (Forward Kinematics)
        matrices_transformacion = self.chain.forward_kinematics(vector_full, full_kinematics=True)
        return matrices_transformacion