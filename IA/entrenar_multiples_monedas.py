# entrenar_multiples_monedas.py
# Entrena modelos IA de equilibrio para un conjunto de altcoins especificadas manualmente

import os
import subprocess
import re

# === CONFIGURACIÓN ===
ALTCOINS = ["1INCHUSDT", "ENAUSDT","FETUSDT","ICXUSDT","LAYERUSDT",
            "MOVEUSDT","OMUSDT","SUIUSDT","TAOUSDT","TRUMPUSDT",
            "TURBOUSDT","VIRTUALUSDT"]  # Edita libremente
TIMEFRAME = "1h"

# === FUNCIONES ===
def reemplazar_alt_symbol(content, alt):
    return re.sub(r'ALT_SYMBOL\s*=\s*".+?"', f'ALT_SYMBOL = "{alt}"', content)

def reemplazar_timeframe(content, timeframe):
    return re.sub(r'TIMEFRAME\s*=\s*".+?"', f'TIMEFRAME = "{timeframe}"', content)

def generar_dataset(alt):
    print(f"\n📘 Generando dataset para {alt}...")
    with open("IA/01_generar_dataset_equilibrio.py", "r") as file:
        content = file.read()
    content = reemplazar_alt_symbol(content, alt)
    content = reemplazar_timeframe(content, TIMEFRAME)
    with open("IA/01_generar_dataset_equilibrio_temp.py", "w") as file:
        file.write(content)
    subprocess.run(["python", "IA/01_generar_dataset_equilibrio_temp.py"])
    os.remove("IA/01_generar_dataset_equilibrio_temp.py")

def entrenar_modelo(alt):
    print(f"\n🤖 Entrenando modelo IA para {alt}...")
    with open("IA/02_entrenar_modelo_equilibrio.py", "r", encoding="utf-8") as file:
        content = file.read()
    content = reemplazar_alt_symbol(content, alt)
    content = reemplazar_timeframe(content, TIMEFRAME)
    with open("IA/02_entrenar_modelo_equilibrio_temp.py", "w", encoding="utf-8") as file:
        file.write(content)
    subprocess.run(["python", "IA/02_entrenar_modelo_equilibrio_temp.py"])
    os.remove("IA/02_entrenar_modelo_equilibrio_temp.py")

# === FLUJO PRINCIPAL ===
if __name__ == "__main__":
    for alt in ALTCOINS:
        generar_dataset(alt)
        entrenar_modelo(alt)

    print("\n✅ Modelos entrenados para todas las altcoins seleccionadas.")
