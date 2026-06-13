import numpy as np

class MotorPhysics:
    def __init__(self):
        # Constantes térmicas y eléctricas
        self.t_amb = 25.0
        self.corriente_holding = 0.5  # Amperaje mínimo para mantener posición
        
        # Variables de estado (6 ejes)
        self.temperaturas = [self.t_amb] * 6
        self.corrientes = [self.corriente_holding] * 6
        
        # Coeficientes de la ecuación diferencial
        self.alfa = 0.005  # Tasa de calentamiento por efecto Joule
        self.beta = 0.005  # Tasa de disipación térmica (enfriamiento)

    def simular_paso_tiempo(self, deltas_angulos_deg):
        """
        Calcula el nuevo estado de corriente y temperatura basado en cuánto se movió 
        cada articulación en el último instante de tiempo.
        """
        for i in range(6):
            # 1. Simulación de Corriente (I)
            # La corriente sube proporcionalmente a la velocidad del movimiento
            velocidad = abs(deltas_angulos_deg[i])
            # Si no se mueve, regresa a la corriente de holding (0.5 A)
            self.corrientes[i] = self.corriente_holding + (velocidad * 1.5)
            
            # 2. Simulación de Temperatura (T)
            calor_generado = self.alfa * (self.corrientes[i] ** 2)
            calor_disipado = self.beta * (self.temperaturas[i] - self.t_amb)
            
            self.temperaturas[i] += (calor_generado - calor_disipado)