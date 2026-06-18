import numpy as np

class MotorPhysics:
    def __init__(self):
        self.t_amb = 25.0
        
        self.corriente_holding = [2.0, 4.0, 2.5, 0.5, 0.5, 0.5] 
        self.kv = [0.05, 0.08, 0.05, 0.02, 0.02, 0.02] 
        self.corriente_maxima = [35.0, 45.0, 35.0, 15.0, 15.0, 15.0]

        # 2. INERCIA TÉRMICA BLINDADA
        # J1 ajustado: Alta generación (0.0008) pero alta disipación (0.004)
        # T_max sostenida a 14A = 25 + (0.0008/0.004)*(14^2) = 64.2°C
        self.alfa = [0.0008, 0.0005, 0.0004, 0.0006, 0.0006, 0.0006] 
        self.beta = [0.004, 0.002, 0.002, 0.003, 0.003, 0.003]
        
        self.filtro_i = 0.15

        self.temperaturas = [self.t_amb] * 6
        self.corrientes = list(self.corriente_holding)

    def simular_paso_tiempo(self, deltas_angulos_deg):
        dt = 0.0333 
        
        for i in range(6):
            velocidad_grados_seg = abs(deltas_angulos_deg[i]) / dt
            corriente_demanda = self.corriente_holding[i] + (velocidad_grados_seg * self.kv[i])
            
            if corriente_demanda > self.corriente_maxima[i]:
                corriente_demanda = self.corriente_maxima[i]
            
            self.corrientes[i] = (self.corrientes[i] * (1.0 - self.filtro_i)) + (corriente_demanda * self.filtro_i)
            
            calor_generado = self.alfa[i] * (self.corrientes[i] ** 2)
            calor_disipado = self.beta[i] * (self.temperaturas[i] - self.t_amb)
            
            self.temperaturas[i] += (calor_generado - calor_disipado)
            
            if self.temperaturas[i] < self.t_amb:
                self.temperaturas[i] = self.t_amb