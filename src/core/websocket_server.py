import asyncio
import json
import websockets
from PySide6.QtCore import QThread, Signal

class ServidorWebSockets(QThread):
    # Señal opcional para enviar mensajes de estado a la UI
    estado_conexion = Signal(str)

    def __init__(self, controlador):
        super().__init__()
        self.controlador = controlador
        self.corriendo = False
        self.loop = None

    async def _manejador_clientes(self, websocket):
        self.estado_conexion.emit("[WebSockets] Cliente SCADA conectado.")
        try:
            while self.corriendo:
                # 1. Le pedimos el estado real y actualizado al Cerebro (Controlador)
                datos = self.controlador.obtener_estado_diccionario()
                
                # 2. Lo serializamos y lo enviamos por el cable de red
                await websocket.send(json.dumps(datos))
                
                # === FIX DE LATENCIA WEB ===
                # Reducimos de 0.3s (3Hz) a 0.05s (20Hz) para sincronizar visualmente
                # el Dashboard de Node-RED con el simulador local.
                await asyncio.sleep(0.4)
                
        except websockets.exceptions.ConnectionClosed:
            self.estado_conexion.emit("[WebSockets] Cliente SCADA desconectado.")

    async def _iniciar_servidor(self):
        async with websockets.serve(self._manejador_clientes, "localhost", 8765):
            # Mantenemos el servidor vivo mientras el hilo esté corriendo
            while self.corriendo:
                await asyncio.sleep(0.5)

    def run(self):
        """Este método se ejecuta en un hilo separado al llamar a .start()"""
        self.corriendo = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.estado_conexion.emit("[WebSockets] Servidor encendido en ws://localhost:8765")
        self.loop.run_until_complete(self._iniciar_servidor())
        self.loop.close()

    def detener(self):
        """Detiene el bucle y cierra el hilo limpiamente"""
        self.corriendo = False
        self.estado_conexion.emit("[WebSockets] Servidor apagado.")
        self.quit()
        self.wait()