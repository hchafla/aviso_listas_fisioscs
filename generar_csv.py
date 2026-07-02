import pdfplumber

PDF = "pdf/gapgc.pdf"   # Cambia el nombre si el tuyo es otro

with pdfplumber.open(PDF) as pdf:

    print("=" * 80)
    print(f"Páginas del PDF: {len(pdf.pages)}")
    print("=" * 80)

    pagina = pdf.pages[0]

    print("\nTEXTO:\n")
    print(pagina.extract_text())

    print("\n" + "=" * 80)
    print("TABLAS")
    print("=" * 80)

    tablas = pagina.extract_tables()

    print(f"Encontradas: {len(tablas)}")

    for i, tabla in enumerate(tablas):
        print(f"\nTABLA {i+1}")

        for fila in tabla[:15]:
            print(fila)
