
import numpy as np

def probar_matematicas():
    print("\n[BACKEND] --- Ejecutando prueba de matrices ---")
    # Creamos un vector de prueba (por ejemplo, ángulos de joints)
    angulos_prueba = np.array([0.0, 45.0, 90.0, 0.0, -45.0, 0.0])
    print(f"NumPy cargado con éxito. Ángulos iniciales: {angulos_prueba}")
    print("[BACKEND] --- Capa de cinemática lista ---\n")
    return angulos_prueba