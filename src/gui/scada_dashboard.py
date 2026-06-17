import os
import sys
import pyqtgraph as pg
from PySide6.QtWidgets import (QDialog, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, 
                               QFormLayout, QGroupBox, QLabel, QPushButton, 
                               QListWidget, QTextEdit, QApplication)
from PySide6.QtCore import Signal, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont

class DialogoManualSCADA(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual de Integración - SCADA Web")
        self.resize(780, 520)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QListWidget { background-color: #252526; border: none; border-right: 1px solid #333; outline: 0; padding-top: 10px; font-size: 13px;}
            QListWidget::item { padding: 12px 15px; border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #37373d; color: #569cd6; border-left: 3px solid #569cd6; font-weight: bold; }
            QLabel { font-size: 13px; line-height: 1.5; }
            QLabel#titulo { color: #569cd6; font-size: 18px; font-weight: bold; margin-bottom: 15px; }
            QLabel#comando { background-color: #111111; color: #ce9178; padding: 10px; font-family: 'Consolas'; border-radius: 4px; border: 1px solid #333; }
            QPushButton { background-color: #007acc; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #0098ff; }
            QTextEdit { background-color: #111111; color: #dcdcaa; font-family: 'Consolas'; font-size: 11px; border: 1px solid #333; }
        """)

        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- PANEL IZQUIERDO: ÍNDICE ---
        self.lista_indice = QListWidget()
        self.lista_indice.setFixedWidth(220)
        items = [
            "1. Introducción", 
            "2. Instalar Node.js", 
            "3. Instalar Node-RED", 
            "4. Ejecutar Servidor", 
            "5. Importar Dashboard",
            "6. Acceso Remoto"
        ]
        self.lista_indice.addItems(items)
        
        # --- PANEL DERECHO: CONTENIDO ---
        self.paginas = QStackedWidget()
        self.paginas.setContentsMargins(20, 20, 20, 20)

        # Configurar cada página
        self.paginas.addWidget(self.crear_pagina_introduccion())
        self.paginas.addWidget(self.crear_pagina_nodejs())
        self.paginas.addWidget(self.crear_pagina_instalacion())
        self.paginas.addWidget(self.crear_pagina_ejecucion())
        self.paginas.addWidget(self.crear_pagina_importar())
        self.paginas.addWidget(self.crear_pagina_acceso_remoto())

        self.lista_indice.currentRowChanged.connect(self.paginas.setCurrentIndex)
        
        layout_principal.addWidget(self.lista_indice)
        layout_principal.addWidget(self.paginas)
        
        self.lista_indice.setCurrentRow(0)

    # --- LÓGICA DE FEEDBACK VISUAL PARA LOS BOTONES ---
    def animar_copiado(self, texto, boton, texto_original):
        QApplication.clipboard().setText(texto)
        boton.setText("Copiado")
        # El timer regresa el texto a la normalidad después de 2 segundos
        QTimer.singleShot(2000, lambda: boton.setText(texto_original))

    # --- HERRAMIENTA: BLOQUE DE CÓDIGO CON BOTÓN DE COPIAR ---
    def crear_bloque_codigo(self, comando):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_cmd = QLabel(comando)
        lbl_cmd.setObjectName("comando")
        lbl_cmd.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        btn_copiar = QPushButton("Copiar")
        btn_copiar.setFixedWidth(70)
        btn_copiar.setStyleSheet("""
            QPushButton { background-color: #3a3d41; color: #d4d4d4; padding: 5px; border-radius: 4px; font-size: 11px; } 
            QPushButton:hover { background-color: #569cd6; color: white; }
        """)
        
        btn_copiar.clicked.connect(lambda _, t=comando, b=btn_copiar: self.animar_copiado(t, b, "Copiar"))
        
        layout.addWidget(lbl_cmd)
        layout.addWidget(btn_copiar)
        return widget

    # --- GENERADORES DE PÁGINAS ---

    def crear_pagina_introduccion(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        lbl_titulo = QLabel("Transmisión SCADA Web"); lbl_titulo.setObjectName("titulo")
        lbl_texto = QLabel(
            "Esta característica avanzada permite convertir cualquier dispositivo en tu "
            "red local (como un celular o tablet) en un panel de control HMI/SCADA.\n\n"
            "Para lograr esto, OpenTP se comunica mediante WebSockets con un entorno "
            "de desarrollo basado en flujos llamado Node-RED.\n\n"
            "Sigue los pasos en el menú de la izquierda para configurar el entorno "
            "en tu computadora. Solo necesitas realizar esta instalación una vez."
        )
        lbl_texto.setWordWrap(True)
        lbl_texto.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_texto)
        layout.addStretch()
        return widget

    def crear_pagina_nodejs(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        lbl_titulo = QLabel("Paso 1: Instalar Node.js"); lbl_titulo.setObjectName("titulo")
        lbl_texto = QLabel(
            "Node-RED está construido sobre Node.js, por lo que es el requisito principal.\n\n"
            "1. Ve a tu navegador web y busca 'Descargar Node.js'.\n"
            "2. Descarga la versión pre compilada de Node.js para Windows (recomendada para la mayoría de los usuarios), usando la arquitectura de tu computadora.\n"
            "3. Ejecuta el instalador y presiona 'Siguiente' dejando todas las "
            "opciones por defecto.\n\n"
            "Una vez finalizada la instalación, puedes continuar con el siguiente paso."
        )
        lbl_texto.setWordWrap(True)
        lbl_texto.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_texto)
        layout.addStretch()
        return widget

    def crear_pagina_instalacion(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        lbl_titulo = QLabel("Paso 2: Instalar Node-RED"); lbl_titulo.setObjectName("titulo")
        lbl_texto = QLabel(
            "La instalación se realiza a través de la terminal de Windows (PowerShell).\n\n"
            "1. Abre PowerShell como Administrador.\n"
            "2. Es probable que necesites habilitar la ejecución de scripts. Haz clic en 'Copiar', "
            "pégalo en la terminal y presiona Enter:"
        )
        lbl_texto.setWordWrap(True)
        
        bloque_cmd1 = self.crear_bloque_codigo("Set-ExecutionPolicy RemoteSigned -Scope CurrentUser")
        
        lbl_texto2 = QLabel("\n3. Ahora, instala Node-RED globalmente con este comando:")
        lbl_texto2.setWordWrap(True)
        
        bloque_cmd2 = self.crear_bloque_codigo("npm install -g --unsafe-perm node-red")

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_texto)
        layout.addWidget(bloque_cmd1)
        layout.addWidget(lbl_texto2)
        layout.addWidget(bloque_cmd2)
        layout.addStretch()
        return widget

    def crear_pagina_ejecucion(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        lbl_titulo = QLabel("Paso 3: Iniciar el Servidor"); lbl_titulo.setObjectName("titulo")
        lbl_texto = QLabel(
            "Cada vez que quieras usar el Dashboard Web, necesitas encender Node-RED.\n\n"
            "1. Abre una ventana normal de PowerShell.\n"
            "2. Copia y ejecuta el siguiente comando:"
        )
        lbl_texto.setWordWrap(True)
        
        bloque_cmd = self.crear_bloque_codigo("node-red")
        
        lbl_nota = QLabel(
            "\n⚠️ IMPORTANTE: La ventana negra de PowerShell comenzará a mostrar texto. "
            "DEBES MANTENERLA ABIERTA. Si la cierras, el servidor web se apagará.\n\n"
            "3. En tu navegador de la computadora, entra a:"
        )
        lbl_nota.setWordWrap(True)
        lbl_nota.setStyleSheet("color: #d7ba7d; font-weight: bold;")

        bloque_url = self.crear_bloque_codigo("http://localhost:1880")

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_texto)
        layout.addWidget(bloque_cmd)
        layout.addWidget(lbl_nota)
        layout.addWidget(bloque_url)
        layout.addStretch()
        return widget

    def crear_pagina_importar(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        lbl_titulo = QLabel("Paso 4: Importar Dashboard"); lbl_titulo.setObjectName("titulo")
        lbl_texto = QLabel(
            "1. En la interfaz de Node-RED, ve al menú superior derecho y selecciona 'Import'.\n"
            "2. Haz clic en el botón de abajo para copiar todo el código de nuestro sistema.\n"
            "3. Pégalo en la ventana de Node-RED y presiona Importar.\n"
            "4. Haz clic en el botón rojo 'Deploy' en la esquina superior derecha."
        )
        lbl_texto.setWordWrap(True)
        
        self.txt_json = QTextEdit()
        self.txt_json.setReadOnly(True)
        
        # --- LÓGICA DE CARGA DINÁMICA DEL ARCHIVO JSON ---
        if hasattr(sys, '_MEIPASS'):
            ruta_proyecto = sys._MEIPASS
        else:
            ruta_proyecto = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        ruta_json_raiz = os.path.join(ruta_proyecto, "OpenTP_Dashboard.json")
        
        texto_json = ""
        if os.path.exists(ruta_json_raiz):
            with open(ruta_json_raiz, "r", encoding="utf-8") as f:
                texto_json = f.read()
        else:
            texto_json = f"ERROR: No se encontró el archivo JSON.\nRuta buscada:\n{ruta_json_raiz}"
            
        self.txt_json.setText(texto_json)
        
        btn_copiar = QPushButton("Copiar al Portapapeles")
        btn_copiar.clicked.connect(self.copiar_json_completo)

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_texto)
        layout.addWidget(self.txt_json)
        layout.addWidget(btn_copiar)
        return widget

    def copiar_json_completo(self):
        QApplication.clipboard().setText(self.txt_json.toPlainText())
        boton = self.sender() # Identifica qué botón disparó esta función
        if boton:
            boton.setText("Copiado")
            QTimer.singleShot(2000, lambda: boton.setText("Copiar al Portapapeles"))

    def crear_pagina_acceso_remoto(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        lbl_titulo = QLabel("Paso 5: Acceso Remoto (Celular/Tablet)"); lbl_titulo.setObjectName("titulo")
        lbl_texto1 = QLabel(
            "Para monitorear el robot desde otro dispositivo (como tu teléfono), "
            "ambos deben estar conectados exactamente a la misma red WiFi o Local.\n\n"
            "Primero, necesitas averiguar la dirección IP de esta computadora maestra. "
            "Abre PowerShell y ejecuta este comando:"
        )
        lbl_texto1.setWordWrap(True)
        
        bloque_ipconfig = self.crear_bloque_codigo("ipconfig")
        
        lbl_texto2 = QLabel(
            "Busca la línea que dice 'Dirección IPv4' (por ejemplo: 192.168.1.75).\n\n"
            "Finalmente, abre el navegador web de tu celular y escribe esa IP junto "
            "con el puerto 1880 y la ruta del dashboard (reemplaza las letras por tus números):"
        )
        lbl_texto2.setWordWrap(True)
        
        bloque_url = self.crear_bloque_codigo("http://<TU_IP_AQUI>:1880/dashboard")
        
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_texto1)
        layout.addWidget(bloque_ipconfig)
        layout.addWidget(lbl_texto2)
        layout.addWidget(bloque_url)
        layout.addStretch()
        return widget


class DialogoInfoSistema(QDialog):
    senal_conmutar_web = Signal(bool)
    
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
        
        # === BOTÓN DE TRANSMISIÓN Y AYUDA ===
        layout_botones_web = QHBoxLayout()
        
        self.btn_web = QPushButton("TRANSMITIR A SCADA WEB")
        self.btn_web.setCheckable(True) 
        self.btn_web.setStyleSheet("""
            QPushButton { background-color: #2d2d2d; color: #858585; font-weight: bold; padding: 12px; border: 2px solid #404040; border-radius: 6px; }
            QPushButton:checked { background-color: #17a2b8; color: white; border: 2px solid #17a2b8; }
        """)
        self.btn_web.toggled.connect(self.senal_conmutar_web.emit)
        
        self.btn_ayuda_web = QPushButton("?")
        self.btn_ayuda_web.setFixedSize(40, 42)
        self.btn_ayuda_web.setStyleSheet("QPushButton { background-color: #404040; color: white; font-weight: bold; border-radius: 6px; font-size: 16px; } QPushButton:hover { background-color: #569cd6; }")
        
        # Instanciamos la ventana de ayuda y la conectamos al botón
        self.dialogo_ayuda = DialogoManualSCADA(self)
        self.btn_ayuda_web.clicked.connect(self.dialogo_ayuda.show)
        
        layout_botones_web.addWidget(self.btn_web, stretch=1)
        layout_botones_web.addWidget(self.btn_ayuda_web, stretch=0)
        
        col_izq.addLayout(layout_botones_web)
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
        
        # === FIX DE RENDIMIENTO: SOLO REPINTAR CSS SI HAY CAMBIO ===
        es_seguro = datos["seguridad"]["deadman"]
        texto_seguro = "ACTIVO" if es_seguro else "INACTIVO"
        
        # Solo aplicamos el estilo si el texto es diferente al que ya tiene
        if self.lbl_deadman.text() != texto_seguro:
            self.lbl_deadman.setText(texto_seguro)
            self.lbl_deadman.setObjectName("valor" if es_seguro else "alerta")
            self.lbl_deadman.style().unpolish(self.lbl_deadman)
            self.lbl_deadman.style().polish(self.lbl_deadman)
        # ===========================================================
        
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

        self.tiempo_x += 0.1 
        self.hist_tiempo.append(self.tiempo_x)
        
        # === FIX DE MEMORIA: VENTANA DESLIZANTE ===
        # Si excedemos los 150 puntos, borramos los más viejos
        if len(self.hist_tiempo) > self.max_historia:
            self.hist_tiempo = self.hist_tiempo[-self.max_historia:]
        
        for i in range(6):
            self.hist_temp[i].append(datos["temperaturas_c"][i])
            self.hist_curr[i].append(datos["corrientes_a"][i])
            
            # Recortamos también la memoria de las variables de motores
            if len(self.hist_temp[i]) > self.max_historia:
                self.hist_temp[i] = self.hist_temp[i][-self.max_historia:]
                self.hist_curr[i] = self.hist_curr[i][-self.max_historia:]
            
            # Actualizamos la gráfica solo con la ventana deslizante
            t_axis = list(self.hist_tiempo)
            self.curvas_temp[i].setData(t_axis, list(self.hist_temp[i]))
            self.curvas_curr[i].setData(t_axis, list(self.hist_curr[i]))