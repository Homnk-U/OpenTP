import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox
from PySide6.QtCore import Qt

class VisorDetallado(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Diseño maestro del contenedor detallado
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(10)

        # Contenedor visual tipo Grupo Industrial
        grupo_graficas = QGroupBox("Histórico de Telemetría")
        grupo_graficas.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #404040; 
                border-radius: 4px; 
                margin-top: 15px; 
                padding: 10px; 
                font-weight: bold; 
                color: #ffc107; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
            }
        """)
        layout_graficas = QVBoxLayout(grupo_graficas)
        layout_graficas.setSpacing(15)
        
        # Paleta de colores para identificar cada una de las 6 articulaciones (J1 a J6)
        self.colores = [
            (255, 100, 100),  # J1: Rojo claro
            (100, 255, 100),  # J2: Verde claro
            (100, 100, 255),  # J3: Azul claro
            (255, 255, 100),  # J4: Amarillo
            (255, 100, 255),  # J5: Magenta
            (100, 255, 255)   # J6: Cian
        ]
        
        # Configuración del entorno gráfico oscuro de PyQtGraph
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#d4d4d4')

        # --- 1. GRÁFICA DE TEMPERATURA ---
        self.plot_temp = pg.PlotWidget(title="Temperatura de Motores (°C)")
        self.plot_temp.showGrid(x=True, y=True, alpha=0.3)
        self.plot_temp.addLegend(offset=(10, 10))
        self.plot_temp.setLimits(xMin=0)
        self.curvas_temp = []
        
        for i in range(6):
            curva = self.plot_temp.plot(
                pen=pg.mkPen(color=self.colores[i], width=2), 
                name=f"J{i+1}"
            )
            self.curvas_temp.append(curva)
        layout_graficas.addWidget(self.plot_temp)

        # --- 2. GRÁFICA DE CORRIENTE ---
        self.plot_curr = pg.PlotWidget(title="Consumo Eléctrico (A)")
        self.plot_curr.showGrid(x=True, y=True, alpha=0.3)
        self.plot_curr.addLegend(offset=(10, 10))
        self.plot_curr.setLimits(xMin=0)
        self.curvas_curr = []
        
        for i in range(6):
            curva = self.plot_curr.plot(
                pen=pg.mkPen(color=self.colores[i], width=2), 
                name=f"J{i+1}"
            )
            self.curvas_curr.append(curva)
        layout_graficas.addWidget(self.plot_curr)

        layout_principal.addWidget(grupo_graficas)

    def actualizar_graficas(self, datos_historicos):
        """
        Recibe los arreglos históricos directamente del enrutador maestro.
        Cero cálculos, solo renderizado de alta velocidad.
        """
        t_axis = datos_historicos.get("tiempo", [])
        
        # Solo procedemos si el búfer circular ya contiene muestras
        if t_axis:
            temps = datos_historicos.get("temperaturas", [])
            corrientes = datos_historicos.get("corrientes", [])
            
            for i in range(6):
                if i < len(temps):
                    self.curvas_temp[i].setData(t_axis, temps[i])
                if i < len(corrientes):
                    self.curvas_curr[i].setData(t_axis, corrientes[i])