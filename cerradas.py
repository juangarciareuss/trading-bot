import json
import os

ARCHIVO_CERRADAS = "cerradas.json"

def guardar_cerradas(posicion):
    if os.path.exists(ARCHIVO_CERRADAS):
        with open(ARCHIVO_CERRADAS, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append(posicion)

    with open(ARCHIVO_CERRADAS, "w") as f:
        json.dump(data, f, indent=2, default=str)

def cargar_cerradas():
    if os.path.exists(ARCHIVO_CERRADAS):
        with open(ARCHIVO_CERRADAS, "r") as f:
            return json.load(f)
    return []


