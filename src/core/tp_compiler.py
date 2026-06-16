"""
Analizador de código TP. No es un compilador en el estricto sentido, pero funciona 
para interpretar algunos comandos fundamentales.
Hasta este momento, el analizador puede distinguir instrucciones para el movimiento 
articular con modulación de velocidad J P[x] %), actuación de pines digitales 
(DO[x]=ON/OFF), y retardos de bloque (WAIT).
"""

class TPCompiler:
    def __init__(self):
        # Memoria temporal de posiciones (Diccionario: "P[1]" -> [J1, J2, J3, J4, J5, J6])
        self.memoria_posiciones = {}
        
        # Parámetros cinemáticos base
        self.duracion_base_ms = 2500.0  # Tiempo que tarda un movimiento al 100%

    def guardar_punto(self, id_punto, angulos_actuales):
        """
        Guarda en memoria una copia exacta de los ángulos articulares.
        """
        nombre_punto = f"P[{id_punto}]"
        self.memoria_posiciones[nombre_punto] = list(angulos_actuales)
        print(f"[TP Core] Posición guardada exitosamente -> {nombre_punto}: {self.memoria_posiciones[nombre_punto]}")
        
    def obtener_punto(self, nombre_punto):
        """
        Busca y retorna un punto en la memoria, o None si no existe.
        """
        if nombre_punto in self.memoria_posiciones:
            return self.memoria_posiciones[nombre_punto]
        else:
            print(f"[TP Error] El punto {nombre_punto} no existe en la memoria.")
            return None

    def borrar_memoria(self):
        """
        Limpia todos los puntos guardados en la sesión.
        """
        self.memoria_posiciones.clear()
        print("[TP Core] Memoria de posiciones borrada.")

    def compilar_linea(self, linea_texto):
        """
        Analizador Léxico y Sintáctico para instrucciones FANUC TP.
        Retorna un diccionario estandarizado con la instrucción decodificada.
        """
        linea = linea_texto.strip().upper()
        
        if not linea:
            return {"comando": "EMPTY"}

        # 1. Instrucción de Movimiento Articular (Ej. "J P[1] 50% FINE")
        if linea.startswith("J P["):
            partes = linea.split()
            
            if len(partes) >= 2:
                nombre_punto = partes[1]
                angulos_destino = self.obtener_punto(nombre_punto)
                
                if not angulos_destino:
                    return {"comando": "ERROR", "mensaje": f"Punto {nombre_punto} no definido."}
                
                # Extracción de porcentaje de velocidad
                porcentaje_velocidad = 100.0
                if len(partes) >= 3 and "%" in partes[2]:
                    try:
                        porcentaje_velocidad = float(partes[2].replace("%", ""))
                    except ValueError:
                        pass
                
                # Restricciones de seguridad para el multiplicador de velocidad
                if porcentaje_velocidad <= 0: porcentaje_velocidad = 1.0 
                if porcentaje_velocidad > 100: porcentaje_velocidad = 100.0
                
                # Cálculo cinemático de tiempo de interpolación
                duracion_real_ms = int(self.duracion_base_ms * (100.0 / porcentaje_velocidad))
                
                return {
                    "comando": "MOVE",
                    "angulos": angulos_destino,
                    "duracion_ms": duracion_real_ms
                }
            else:
                return {"comando": "ERROR", "mensaje": "Sintaxis de movimiento incompleta."}

        # 2. Instrucción de Salidas Digitales (Ej. "DO[1]=ON")
        elif linea.startswith("DO["):
            if "=ON" in linea:
                return {"comando": "DO", "puerto": 1, "estado": True}
            elif "=OFF" in linea:
                return {"comando": "DO", "puerto": 1, "estado": False}
            else:
                return {"comando": "ERROR", "mensaje": "Valor lógico DO inválido."}

        # 3. Instrucción de Espera (WAIT)
        elif linea.startswith("WAIT "):
            # Sub-caso A: Espera de señal digital (Ej. "WAIT DI[1]=ON")
            if "DI[" in linea:
                try:
                    inicio = linea.find("[") + 1
                    fin = linea.find("]")
                    puerto = int(linea[inicio:fin])
                    estado = "=ON" in linea
                    return {"comando": "WAIT_DI", "puerto": puerto, "estado": estado}
                except ValueError:
                    return {"comando": "ERROR", "mensaje": "Sintaxis de puerto DI inválida."}
                    
            # Sub-caso B: Espera temporal clásica (Ej. "WAIT 0.5")
            else:
                try:
                    segundos = float(linea.replace("WAIT", "").strip())
                    milisegundos = int(segundos * 1000)
                    return {"comando": "WAIT_TIME", "tiempo_ms": milisegundos}
                except ValueError:
                    return {"comando": "ERROR", "mensaje": "Parámetro numérico WAIT inválido."}

        # Instrucción desconocida
        return {"comando": "UNKNOWN", "mensaje": f"Instrucción no reconocida: {linea}"}