import os
import csv
import pdfplumber

CARPETA_PDF = "pdf"
CARPETA_CSV = "nombres"

# Crear carpeta de salida si no existe
os.makedirs(CARPETA_CSV, exist_ok=True)

for archivo in os.listdir(CARPETA_PDF):

    if not archivo.lower().endswith(".pdf"):
        continue

    ruta_pdf = os.path.join(CARPETA_PDF, archivo)
    ruta_csv = os.path.join(
        CARPETA_CSV,
        archivo.replace(".pdf", ".csv")
    )

    print(f"\nProcesando {archivo}...")

    filas_csv = []

    with pdfplumber.open(ruta_pdf) as pdf:

        for pagina in pdf.pages:

            tablas = pagina.extract_tables()

            for tabla in tablas:

                if not tabla:
                    continue

                encabezado = tabla[0]

                # Solo nos interesa la tabla que contiene los nombres
                if encabezado and "Nombre" in encabezado:

                    for fila in tabla[1:]:

                        if len(fila) < 4:
                            continue

                        orden_gerencia = fila[0]
                        orden_general = fila[1]
                        nombre = fila[2]
                        situacion = fila[3]

                        if not orden_gerencia or not nombre:
                            continue

                        filas_csv.append([
                            orden_gerencia,
                            orden_general,
                            nombre,
                            situacion
                        ])

    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow([
            "orden_gerencia",
            "orden_general",
            "nombre",
            "situacion"
        ])

        writer.writerows(filas_csv)

    print(f" -> {len(filas_csv)} registros guardados.")

print("\n========================")
print("CSV generado correctamente.")
print("========================")

# Mostrar un ejemplo para comprobar que todo está bien
csv_prueba = os.path.join(CARPETA_CSV, "gapgc.csv")

if os.path.exists(csv_prueba):
    print("\nPrimeras 20 líneas de gapgc.csv:\n")

    with open(csv_prueba, encoding="utf-8-sig") as f:
        for i, linea in enumerate(f):
            print(linea.strip())

            if i >= 19:
                break
