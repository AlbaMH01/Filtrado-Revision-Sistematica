import os
import pandas as pd

def guardar_en_carpeta_proyecto(df, nombre_archivo="avances_revision.csv"):
    # 1. Localiza la carpeta donde está este script (.py)
    directorio_proyecto = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Crea la ruta completa al archivo
    ruta_destino = os.path.join(directorio_proyecto, nombre_archivo)
    
    # 3. Guarda el CSV (sobrescribe automáticamente el anterior)
    df.to_csv(ruta_destino, index=False)
    
    return ruta_destino