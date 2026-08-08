# OpenTP: An Open-Source Robotic Simulator with IIoT and SCADA Integration

OpenTP es un simulador robótico 3D de código abierto optimizado para infraestructuras de hardware universitario bajo entornos Windows. El sistema integra un intérprete nativo para scripts en lenguaje Teach Pendant (TP), arquitectura Modelo-Vista-Controlador (MVC) y telemetría asíncrona mediante WebSockets orientada a la Industria 4.0.

---

## Modelos del Robot

El repositorio incluye de forma nativa la descripción geométrica y cinemática del manipulador industrial (configurado para el modelo base FANUC M-900iA/350). Los archivos de configuración en formato URDF y las mallas topológicas se encuentran integrados en la estructura del proyecto para permitir el cálculo cinemático directo y la renderización acelerada por hardware.

---

## Instrucciones de Instalación

El software cuenta con un instalador ejecutable independiente para facilitar su despliegue en laboratorios y equipos de cómputo:

1. Localiza el archivo instalador con extensión `.exe` dentro de los recursos de distribución.
2. Ejecuta el archivo `.exe` y sigue los pasos del asistente de instalación en pantalla como cualquier aplicación estándar de Windows. El script de instalación configura las rutas y dependencias necesarias en el equipo de forma automatizada.

---

## Flujo de Node-RED y Dashboard SCADA

Para habilitar la supervisión y el monitoreo remoto mediante arquitecturas IIoT:

1. **Instalación de Node.js y Node-RED:**
   * Descarga e instala [Node.js](https://nodejs.org/) en el sistema operativo.
   * Abre una terminal de **PowerShell** e instala Node-RED ejecutando el siguiente comando:
     ```powershell
     npm install -g --unsafe-perm node-red
     ```

2. **Ejecución del Servidor:**
   * Mantén abierta o abre una ventana de **PowerShell** y arranca el entorno ejecutando:
     ```powershell
     node-red
     ```

3. **Carga del Dashboard SCADA:**
   * El archivo con formato JSON que contiene el flujo estructurado para el dashboard SCADA de Node-RED se incluye tanto en el código fuente del repositorio como en el paquete del software.
   * Importa dicho archivo JSON en la interfaz de Node-RED para desplegar de manera automática los indicadores de control, temperatura de motores y consumo eléctrico.

---

## Licencia

Este proyecto incluye el archivo de licencia correspondiente en la raíz del repositorio. Consulta el archivo `LICENSE` para conocer los términos de uso y distribución del software.