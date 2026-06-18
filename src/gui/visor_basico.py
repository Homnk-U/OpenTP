from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QGroupBox
from gui.widgets_custom.radial_gauge import RadialGauge

class VisorBasico(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(5, 5, 5, 5)

        # --- SECCIÓN 1: TEMPERATURA ---
        grupo_temp = QGroupBox("Temperatura de Motores (°C)")
        grupo_temp.setStyleSheet("QGroupBox { font-weight: bold; color: #4ec9b0; }")
        layout_temp = QGridLayout(grupo_temp)
        
        self.gauges_temp = []
        for i in range(6):
            gauge = RadialGauge(label=f"J{i+1}", suffix="°C", min_val=0, max_val=100, yellow_th=45, red_th=65)
            self.gauges_temp.append(gauge)
            # Acomodamos en 2 filas de 3 columnas para que no se aplasten
            fila = i // 3
            columna = i % 3
            layout_temp.addWidget(gauge, fila, columna)
            
        layout_principal.addWidget(grupo_temp)

        # --- SECCIÓN 2: CORRIENTE ---
        grupo_curr = QGroupBox("Consumo Eléctrico (A)")
        grupo_curr.setStyleSheet("QGroupBox { font-weight: bold; color: #4ec9b0; }")
        layout_curr = QGridLayout(grupo_curr)
        
        self.gauges_curr = []
        for i in range(6):
            gauge = RadialGauge(label=f"J{i+1}", suffix="A", min_val=0, max_val=20, yellow_th=8, red_th=14)
            self.gauges_curr.append(gauge)
            fila = i // 3
            columna = i % 3
            layout_curr.addWidget(gauge, fila, columna)

        layout_principal.addWidget(grupo_curr)

    def actualizar_datos(self, estado):
        """Esta función será llamada a 2.5Hz por el Dashboard"""
        temps = estado.get("temperaturas_c", [0]*6)
        currs = estado.get("corrientes_a", [0]*6)
        
        for i in range(6):
            self.gauges_temp[i].set_value(temps[i])
            self.gauges_curr[i].set_value(currs[i])