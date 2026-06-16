import asyncio
import websockets
import json
import random

async def emisor_telemetria(websocket):
    print("[+] Panel SCADA conectado.")
    try:
        while True:
            # Simulamos el movimiento del robot y calentamiento del motor
            datos = {
                "X": 2345.00 + random.uniform(-2, 2),
                "Y": 0.00,
                "Z": 2200.00,
                "J1_temp": 25.10 + random.uniform(0, 0.05)
            }
            
            # Serializamos a JSON y enviamos por el socket
            await websocket.send(json.dumps(datos))
            
            # Frecuencia de actualización: 100 ms
            await asyncio.sleep(0.1)
            
    except websockets.exceptions.ConnectionClosed:
        print("[-] Panel SCADA desconectado.")

async def main():
    # Levantamos el servidor en el puerto 8765
    async with websockets.serve(emisor_telemetria, "localhost", 8765):
        print("Servidor WebSocket del Robot iniciado en ws://localhost:8765")
        await asyncio.Future()  # Mantiene el servidor en ejecución

if __name__ == "__main__":
    asyncio.run(main())