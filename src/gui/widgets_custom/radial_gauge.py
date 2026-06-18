import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtCore import Qt, QRectF, QVariantAnimation, QEasingCurve

class RadialGauge(QWidget):
    def __init__(self, label="J1", suffix="", min_val=0.0, max_val=100.0, yellow_th=45.0, red_th=65.0, parent=None):
        super().__init__(parent)
        self.label = label
        self.suffix = suffix
        self.min_value = float(min_val)
        self.max_value = float(max_val)
        self.yellow_threshold = float(yellow_th)
        self.red_threshold = float(red_th)
        
        # Separamos la lógica: el valor destino vs el valor que se está dibujando animado
        self.value = float(min_val)
        self.display_value = float(min_val) 
        
        # Paleta de colores industriales
        self.color_fondo_arco = QColor("#2d2d2d")
        self.color_texto_etiqueta = QColor("#858585")
        self.color_texto_valores = QColor("#d4d4d4")
        
        self.color_verde = QColor("#4ec9b0")
        self.color_amarillo = QColor("#ffc107")
        self.color_rojo = QColor("#f14c4c")
        
        self.setMinimumSize(120, 120)

        # === MOTOR DE ANIMACIÓN FLUIDA ===
        self.animacion = QVariantAnimation(self)
        self.animacion.setDuration(250) # Desliza la aguja en 250 milisegundos
        self.animacion.setEasingCurve(QEasingCurve.OutCubic) # Desacelera suavemente al llegar
        self.animacion.valueChanged.connect(self._actualizar_display)

    def set_value(self, nuevo_valor):
        """Actualiza el valor disparando una transición animada de bajo coste."""
        try:
            val = float(nuevo_valor)
        except (ValueError, TypeError):
            val = self.min_value
            
        val = max(self.min_value, min(val, self.max_value))
        
        if val != self.value:
            self.animacion.stop()
            self.animacion.setStartValue(self.display_value)
            self.animacion.setEndValue(val)
            self.value = val
            self.animacion.start()

    def _actualizar_display(self, val):
        """Callback que se ejecuta en cada frame de la animación."""
        self.display_value = val
        self.update()

    def _obtener_color_actual(self):
        """Evalúa los umbrales lógicos sobre el valor que se está dibujando."""
        if self.display_value >= self.red_threshold:
            return self.color_rojo
        elif self.display_value >= self.yellow_threshold:
            return self.color_amarillo
        return self.color_verde

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) 
        
        ancho = self.width()
        alto = self.height()
        diametro = min(ancho, alto) - 20
        x = (ancho - diametro) / 2
        y = (alto - diametro) / 2
        rect_arco = QRectF(x, y, diametro, diametro)
        
        angulo_inicio = 225 * 16 
        angulo_total_barrido = -270 * 16 
        
        grosor_linea = max(6, int(diametro * 0.06))
        
        # Dibujar riel de fondo
        pen_fondo = QPen(self.color_fondo_arco, grosor_linea, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_fondo)
        painter.drawArc(rect_arco, angulo_inicio, angulo_total_barrido)
        
        # Calcular la longitud animada del arco activo
        rango = self.max_value - self.min_value
        porcentaje = (self.display_value - self.min_value) / rango if rango > 0 else 0.0
        angulo_activo = -int(porcentaje * 270 * 16)
        
        color_activo = self._obtener_color_actual()
        
        # Dibujar el arco de nivel activo
        pen_activo = QPen(color_activo, grosor_linea, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_activo)
        painter.drawArc(rect_arco, angulo_inicio, angulo_activo)
        
        font_base = "Consolas"
        
        # Etiqueta Superior
        fuente_lbl = QFont(font_base, max(9, int(diametro * 0.08)), QFont.Bold)
        painter.setFont(fuente_lbl)
        painter.setPen(self.color_texto_etiqueta)
        painter.drawText(QRectF(0, y + diametro * 0.2, ancho, diametro * 0.15), 
                         Qt.AlignCenter, self.label)
        
        # Lectura Central Dinámica Animada
        fuente_val = QFont(font_base, max(11, int(diametro * 0.12)), QFont.Bold)
        painter.setFont(fuente_val)
        painter.setPen(color_activo) 
        
        texto_valor = f"{self.display_value:.1f}" if "°C" in self.suffix else f"{self.display_value:.2f}"
        if self.suffix:
            texto_valor += f" {self.suffix}"
            
        painter.drawText(QRectF(0, y + diametro * 0.4, ancho, diametro * 0.25), 
                         Qt.AlignCenter, texto_valor)
                         
        # Valores Mínimo y Máximo
        fuente_lim = QFont(font_base, max(8, int(diametro * 0.06)))
        painter.setFont(fuente_lim)
        painter.setPen(self.color_texto_etiqueta)
        
        painter.drawText(QRectF(x - 5, y + diametro * 0.8, diametro * 0.4, diametro * 0.15), 
                         Qt.AlignLeft, f"{int(self.min_value)}")
        painter.drawText(QRectF(x + diametro * 0.6 + 5, y + diametro * 0.8, diametro * 0.4, diametro * 0.15), 
                         Qt.AlignRight, f"{int(self.max_value)}")