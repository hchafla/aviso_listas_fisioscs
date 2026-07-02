import os
import csv
import pdfplumber

CARPETA_PDF = "pdf"
CARPETA_CSV = "nombres"

os.makedirs(CARPETA_CSV, exist_ok=True)

for archivo in sorted(os.listdir(CARPETA_PDF)):

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

                if encabezado and "Nombre" in encabezado:

                    for fila in tabla[1:]:

                        # Evitar filas incompletas
                        if len(fila) < 4:
                            continue

                        orden_gerencia = (fila[0] or "").strip()
                        orden_general = (fila[1] or "").strip()
                        nombre = (fila[2] or "").strip()
                        situacion = (fila[3] or "").strip()

                        # Saltar filas vacías
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

    print(f"✓ {os.path.basename(ruta_csv)} generado ({len(filas_csv)} registros)")

print("\n========================================")
print("Todos los CSV se han generado correctamente.")
print("========================================")
