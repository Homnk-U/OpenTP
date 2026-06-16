import pyqtgraph as pg
from PySide6.QtWidgets import (QDialog, QWidget, QHBoxLayout, QVBoxLayout, 
                               QFormLayout, QGroupBox, QLabel, QPushButton)

class DialogoInfoSistema(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SCADA Dashboard - OpenTP")
        self.resize(1000, 700) 
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; font-size: 13px; font-weight: bold; }
            QLabel#valor { color: #4ec9b0; font-family: Consolas; font-size: 14px; }
            QLabel#alerta { color: #f14c4c; font-family: Consolas; font-weight: bold;}
            QLabel#titulo { color: #569cd6; font-size: 16px; margin-bottom: 5px;}
            QGroupBox { border: 1px solid #404040; border-radius: 4px; margin-top: 15px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #c586c0; font-size: 13px;}
        """)

        layout_principal = QHBoxLayout(self)
        
        contenedor_izq = QWidget()
        contenedor_izq.setFixedWidth(300) 
        col_izq = QVBoxLayout(contenedor_izq) 
        col_izq.setContentsMargins(0, 0, 10, 0)
        
        # 1. Estado del Sistema
        grupo_estado = QGroupBox("Estado del Sistema")
        form_estado = QFormLayout(grupo_estado)
        self.lbl_modo = QLabel("-"); self.lbl_modo.setObjectName("valor")
        self.lbl_deadman = QLabel("-"); self.lbl_deadman.setObjectName("alerta")
        self.lbl_estop = QLabel("-"); self.lbl_estop.setObjectName("valor")
        form_estado.addRow("Modo Operación:", self.lbl_modo)
        form_estado.addRow("Deadman Switch:", self.lbl_deadman)
        form_estado.addRow("E-Stop:", self.lbl_estop)
        col_izq.addWidget(grupo_estado)
        
        # 2. Carga y Producción
        grupo_produccion = QGroupBox("Carga y Producción")
        form_prod = QFormLayout(grupo_produccion)
        self.lbl_vacio = QLabel("-"); self.lbl_vacio.setObjectName("valor")
        self.lbl_payload = QLabel("-"); self.lbl_payload.setObjectName("valor")
        self.lbl_ciclos = QLabel("-"); self.lbl_ciclos.setObjectName("valor")
        self.lbl_tiempo = QLabel("-"); self.lbl_tiempo.setObjectName("valor")
        form_prod.addRow("Estado Ventosa:", self.lbl_vacio)
        form_prod.addRow("Payload Actual:", self.lbl_payload)
        form_prod.addRow("Ciclos Totales:", self.lbl_ciclos)
        form_prod.addRow("Último Ciclo:", self.lbl_tiempo)
        col_izq.addWidget(grupo_produccion)
        
        # 3. Cinemática TCP
        grupo_cine = QGroupBox("Cinemática TCP (mm)")
        form_cine = QFormLayout(grupo_cine)
        self.lbl_x = QLabel("-"); self.lbl_x.setObjectName("valor")
        self.lbl_y = QLabel("-"); self.lbl_y.setObjectName("valor")
        self.lbl_z = QLabel("-"); self.lbl_z.setObjectName("valor")
        form_cine.addRow("X:", self.lbl_x)
        form_cine.addRow("Y:", self.lbl_y)
        form_cine.addRow("Z:", self.lbl_z)
        col_izq.addWidget(grupo_cine)
        
        # 4. Articulaciones (J1-J6)
        grupo_joints = QGroupBox("Articulaciones (Grados)")
        form_joints = QFormLayout(grupo_joints)
        self.lbl_j1 = QLabel("-"); self.lbl_j1.setObjectName("valor")
        self.lbl_j2 = QLabel("-"); self.lbl_j2.setObjectName("valor")
        self.lbl_j3 = QLabel("-"); self.lbl_j3.setObjectName("valor")
        self.lbl_j4 = QLabel("-"); self.lbl_j4.setObjectName("valor")
        self.lbl_j5 = QLabel("-"); self.lbl_j5.setObjectName("valor")
        self.lbl_j6 = QLabel("-"); self.lbl_j6.setObjectName("valor")
        form_joints.addRow("J1:", self.lbl_j1)
        form_joints.addRow("J2:", self.lbl_j2)
        form_joints.addRow("J3:", self.lbl_j3)
        form_joints.addRow("J4:", self.lbl_j4)
        form_joints.addRow("J5:", self.lbl_j5)
        form_joints.addRow("J6:", self.lbl_j6)
        col_izq.addWidget(grupo_joints)
        
        # === NUEVO: BOTÓN DE TRANSMISIÓN WEB ===
        self.btn_web = QPushButton("TRANSMITIR A SCADA WEB")
        self.btn_web.setCheckable(True) 
        self.btn_web.setStyleSheet("""
            QPushButton { 
                background-color: #2d2d2d; color: #858585; font-weight: bold; 
                padding: 12px; border: 2px solid #404040; border-radius: 6px; 
                margin-top: 15px;
            }
            QPushButton:checked { 
                background-color: #17a2b8; color: white; border: 2px solid #17a2b8;
            }
            QPushButton:hover { border: 2px solid #569cd6; }
        """)
        # self.btn_web.toggled.connect(self.conmutar_servidor_web)
        col_izq.addWidget(self.btn_web)
        # =======================================
        
        col_izq.addStretch()
        layout_principal.addWidget(contenedor_izq)

        # Configuración de Gráficas (Columna Derecha)
        col_der = QVBoxLayout()
        self.max_historia = 150
        self.hist_tiempo = []
        self.hist_temp = [[] for _ in range(6)]
        self.hist_curr = [[] for _ in range(6)]
        self.tiempo_x = 0.0

        self.colores = [(255,100,100), (100,255,100), (100,100,255), (255,255,100), (255,100,255), (100,255,255)]
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#d4d4d4')

        self.plot_temp = pg.PlotWidget(title="Temperatura de Motores (°C)")
        self.plot_temp.showGrid(x=True, y=True, alpha=0.3)
        self.plot_temp.addLegend(offset=(10, 10))
        self.plot_temp.setLimits(xMin=0)
        self.curvas_temp = []
        for i in range(6):
            curva = self.plot_temp.plot(pen=pg.mkPen(color=self.colores[i], width=2), name=f"J{i+1}")
            self.curvas_temp.append(curva)
        col_der.addWidget(self.plot_temp)

        self.plot_curr = pg.PlotWidget(title="Consumo Eléctrico (A)")
        self.plot_curr.showGrid(x=True, y=True, alpha=0.3)
        self.plot_curr.addLegend(offset=(10, 10))
        self.plot_curr.setLimits(xMin=0)
        self.curvas_curr = []
        for i in range(6):
            curva = self.plot_curr.plot(pen=pg.mkPen(color=self.colores[i], width=2), name=f"J{i+1}")
            self.curvas_curr.append(curva)
        col_der.addWidget(self.plot_curr)

        layout_principal.addLayout(col_der)

    def actualizar_datos(self, datos):
        self.lbl_modo.setText(datos["modo_operacion"])
        self.lbl_modo.setStyleSheet("color: #ce9178;" if "MANUAL" in datos["modo_operacion"] else "color: #4ec9b0;")
        
        es_seguro = datos["seguridad"]["deadman"]
        self.lbl_deadman.setText("ACTIVO" if es_seguro else "INACTIVO")
        self.lbl_deadman.setObjectName("valor" if es_seguro else "alerta")
        self.lbl_estop.setText("EMERGENCIA" if datos["seguridad"]["e_stop"] else "OK")
        
        self.lbl_vacio.setText("SUCCIONANDO" if datos["vacio_activo"] else "APAGADO")
        self.lbl_payload.setText(f"{datos['payload_kg']:.1f} kg")
        self.lbl_ciclos.setText(str(datos["ciclos_total"]))
        self.lbl_tiempo.setText(f"{datos['tiempo_ciclo_s']} s")
        
        self.lbl_x.setText(f"{datos['x']:.2f}")
        self.lbl_y.setText(f"{datos['y']:.2f}")
        self.lbl_z.setText(f"{datos['z']:.2f}")
        
        self.lbl_j1.setText(f"{datos['j1']:.2f}°")
        self.lbl_j2.setText(f"{datos['j2']:.2f}°")
        self.lbl_j3.setText(f"{datos['j3']:.2f}°")
        self.lbl_j4.setText(f"{datos['j4']:.2f}°")
        self.lbl_j5.setText(f"{datos['j5']:.2f}°")
        self.lbl_j6.setText(f"{datos['j6']:.2f}°")

        self.lbl_deadman.style().unpolish(self.lbl_deadman)
        self.lbl_deadman.style().polish(self.lbl_deadman)

        self.tiempo_x += 0.1 
        self.hist_tiempo.append(self.tiempo_x)
        
        for i in range(6):
            self.hist_temp[i].append(datos["temperaturas_c"][i])
            self.hist_curr[i].append(datos["corrientes_a"][i])
            
            t_axis = list(self.hist_tiempo)
            self.curvas_temp[i].setData(t_axis, list(self.hist_temp[i]))
            self.curvas_curr[i].setData(t_axis, list(self.hist_curr[i]))