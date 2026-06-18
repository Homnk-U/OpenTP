import os
import csv
from datetime import datetime
from collections import deque

class RobotHistorian:
    def __init__(self, max_puntos_hmi=150):
        # 1. RESOLUCIÓN DE RUTA INTERNACIONAL / MULTI-PC
        # Crea una carpeta llamada 'OpenTP' dentro de los Documentos del usuario
        carpeta_documentos = os.path.join(os.path.expanduser("~"), "Documents", "OpenTP")
        os.makedirs(carpeta_documentos, exist_ok=True)
        
        # Genera un nombre de archivo único con el formato exacto solicitado
        timestamp_sesion = datetime.now().strftime("%Y%m%d_%H%M")
        self.ruta_csv = os.path.join(carpeta_documentos, f"sesion_opentp_{timestamp_sesion}.csv")
        
        # 2. CAPA VOLÁTIL: Búferes circulares rápidos (RAM) para el SCADA UI
        self.max_puntos = max_puntos_hmi
        self.hist_tiempo = deque(maxlen=self.max_puntos)
        self.hist_temp = [deque(maxlen=self.max_puntos) for _ in range(6)]
        self.hist_curr = [deque(maxlen=self.max_puntos) for _ in range(6)]
        self.tiempo_acumulado = 0.0
        
        # 3. CAPA PERSISTENTE: Inicialización del archivo infinito en Disco Duro
        self.archivo_abierto = open(self.ruta_csv, mode='w', newline='', encoding='utf-8')
        self.escritor_csv = csv.writer(self.archivo_abierto)
        
        # Escribimos las cabeceras del reporte industrial
        self.escritor_csv.writerow([
            "Tiempo (s)", "Modo Operacion", "X (mm)", "Y (mm)", "Z (mm)",
            "J1 (deg)", "J2 (deg)", "J3 (deg)", "J4 (deg)", "J5 (deg)", "J6 (deg)",
            "Vacuum Activo", "Payload (kg)",
            "I_J1 (A)", "I_J2 (A)", "I_J3 (A)", "I_J4 (A)", "I_J5 (A)", "I_J6 (A)",
            "T_J1 (C)", "T_J2 (C)", "T_J3 (C)", "T_J4 (C)", "T_J5 (C)", "T_J6 (C)"
        ])
        self.archivo_abierto.flush() # Forzamos la escritura inicial en disco
        print(f"[Historian] Archivo de persistencia creado con éxito en:\n{self.ruta_csv}")

    def registrar_paso(self, datos, dt=0.0333):
        """
        Recibe el diccionario de estado del robot a 30Hz.
        Alimenta la RAM para la gráfica y escribe el renglón infinito en el CSV.
        """
        self.tiempo_acumulado += dt
        
        # --- A. Actualizar Capa Volátil (RAM para pyqtgraph) ---
        self.hist_tiempo.append(self.tiempo_acumulado)
        for i in range(6):
            self.hist_curr[i].append(datos["corrientes_a"][i])
            self.hist_temp[i].append(datos["temperaturas_c"][i])
            
        # --- B. Actualizar Capa Persistente (Escribir en Disco Duro) ---
        # Bloqueo de seguridad: Si el archivo ya se cerró al salir de la app, ignorar.
        if self.archivo_abierto.closed:
            return

        try:
            self.escritor_csv.writerow([
                round(self.tiempo_acumulado, 4), datos["modo_operacion"],
                datos["x"], datos["y"], datos["z"],
                datos["j1"], datos["j2"], datos["j3"], datos["j4"], datos["j5"], datos["j6"],
                1 if datos["vacio_activo"] else 0, datos["payload_kg"],
                round(datos["corrientes_a"][0], 2), round(datos["corrientes_a"][1], 2),
                round(datos["corrientes_a"][2], 2), round(datos["corrientes_a"][3], 2),
                round(datos["corrientes_a"][4], 2), round(datos["corrientes_a"][5], 2),
                round(datos["temperaturas_c"][0], 2), round(datos["temperaturas_c"][1], 2),
                round(datos["temperaturas_c"][2], 2), round(datos["temperaturas_c"][3], 2),
                round(datos["temperaturas_c"][4], 2), round(datos["temperaturas_c"][5], 2)
            ])
            # Hacemos un flush controlado para asegurar que los datos se guarden 
            # sin el costo computacional de abrir/cerrar el archivo a 30Hz
            if len(self.hist_tiempo) % 10 == 0: 
                self.archivo_abierto.flush()
        except Exception as e:
            print(f"[Historian Error] Falló la escritura en disco: {e}")

    def obtener_datos_hmi(self):
        """Devuelve los datos listos en formato de lista para pyqtgraph"""
        return {
            "tiempo": list(self.hist_tiempo),
            "corrientes": [list(d) for d in self.hist_curr],
            "temperaturas": [list(d) for d in self.hist_temp]
        }

    def cerrar_historian(self):
        """Cierra el archivo limpiamente al salir de la aplicación"""
        if hasattr(self, 'archivo_abierto') and not self.archivo_abierto.closed:
            self.archivo_abierto.flush()
            self.archivo_abierto.close()
            print("[Historian] Archivo CSV cerrado y salvado de forma segura.")