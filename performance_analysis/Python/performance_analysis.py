import os
import glob
import pandas as pd

def procesar_telemetria_masiva():
    archivos_csv = glob.glob("*.csv")
    resultados = []

    if not archivos_csv:
        print("No se encontraron archivos CSV en el directorio.")
        return

    for archivo in archivos_csv:
        try:
            # Extraer metadatos del nombre del archivo (ej. manual_bajo_opentp.csv)
            partes = archivo.replace('.csv', '').split('_')
            if len(partes) < 3:
                continue
                
            modo = partes[0].capitalize()
            nivel = partes[1].capitalize()
            software = "OpenTP" if "opentp" in partes[2].lower() else "ROBOGUIDE"
            
            df = pd.read_csv(archivo)
            
            # Identificar las columnas de los hilos lógicos
            columnas_cores = [col for col in df.columns if 'Core_' in col]
            
            # 1. Métricas Globales
            media_cpu_total = df['CPU_Total_Pct'].mean()
            media_ram_total = df['RAM_Total_MB'].mean()
            
            # 2. Análisis de Cuello de Botella Mononúcleo
            # Promedio de la carga en el núcleo más estresado de cada segundo
            estres_maximo_mononucleo = df[columnas_cores].max(axis=1).mean()
            
            # 3. Dispersión del Multihilo (Desviación estándar entre núcleos)
            # A mayor desviación, peor es el balanceo de carga
            medias_por_core = df[columnas_cores].mean()
            desviacion_multihilo = medias_por_core.std()
            
            # 4. Hilos Lógicos Activos (Carga promedio superior al 10%)
            hilos_activos = (medias_por_core > 10.0).sum()

            resultados.append({
                'Software': software,
                'Hardware': nivel,
                'Modo': modo,
                'CPU Total Promedio (%)': round(media_cpu_total, 2),
                'RAM Promedio (MB)': round(media_ram_total, 2),
                'Estrés Máx. Mononúcleo (%)': round(estres_maximo_mononucleo, 2),
                'Desviación Carga Multihilo': round(desviacion_multihilo, 2),
                'Hilos Activos (>10%)': hilos_activos
            })
            
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")

    # Consolidar y ordenar el DataFrame
    df_final = pd.DataFrame(resultados)
    # Ordenar lógicamente: Primero por hardware (Bajo, Medio, Alto), luego Modo, luego Software
    orden_hardware = {'Bajo': 1, 'Medio': 2, 'Alto': 3}
    df_final['Orden_HW'] = df_final['Hardware'].map(orden_hardware)
    df_final.sort_values(by=['Orden_HW', 'Modo', 'Software'], inplace=True)
    df_final.drop('Orden_HW', axis=1, inplace=True)
    
    # Exportar resultados
    print("\n=== MATRIZ DE RESULTADOS CONSOLIDADOS ===")
    print(df_final.to_string(index=False))
    
    df_final.to_csv("analisis_arquitectonico_consolidado.csv", index=False)
    print("\n[+] Análisis completado. Datos exportados a 'analisis_arquitectonico_consolidado.csv'")

if __name__ == "__main__":
    procesar_telemetria_masiva()