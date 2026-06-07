class TPCompiler:
    def __init__(self):
        # El "Disco Duro" temporal de nuestro robot
        # Es un diccionario que vinculará un texto "P[1]" con una lista de 6 grados
        self.memoria_posiciones = {}

    def guardar_punto(self, id_punto, angulos_actuales):
        """
        Toma el ID del punto (ej. 1) y la lista de 6 ángulos, y los guarda en memoria.
        """
        nombre_punto = f"P[{id_punto}]"
        
        # IMPORTANTE: Usamos list() para guardar una COPIA exacta de los ángulos en este momento.
        # Si no hacemos copia, el punto se seguiría moviendo junto con el robot en vivo.
        self.memoria_posiciones[nombre_punto] = list(angulos_actuales)
        
        print(f"[TP Core] Posición guardada exitosamente -> {nombre_punto}: {self.memoria_posiciones[nombre_punto]}")
        
    def obtener_punto(self, nombre_punto):
        """
        Busca un punto en la memoria (ej. "P[1]").
        Devuelve la lista de 6 ángulos si existe, o None si no se ha grabado.
        """
        if nombre_punto in self.memoria_posiciones:
            return self.memoria_posiciones[nombre_punto]
        else:
            print(f"[TP Error] El punto {nombre_punto} no existe en la memoria.")
            return None

    def borrar_memoria(self):
        """Limpia todos los puntos guardados (Útil para crear un programa nuevo)"""
        self.memoria_posiciones.clear()
        print("[TP Core] Memoria de posiciones borrada.")
