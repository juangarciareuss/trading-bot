import json
import os

ARCHIVO_ABIERTAS = "abiertas.json"

def cargar_abiertas():
    if os.path.exists(ARCHIVO_ABIERTAS):
        with open(ARCHIVO_ABIERTAS, "r") as f:
            return json.load(f)
    return []

def filtrar_abiertas(tf):
    data = cargar_abiertas()
    return [s for s in data if s.get("timeframe") == tf]

def guardar_abiertas(lista):
    with open("abiertas.json", "w") as f:
        json.dump(lista, f, indent=2, default=str)
