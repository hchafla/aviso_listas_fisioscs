def actualizar_mapeo_pdf(session, valor_gerencia, csv_path):
    print(f"DEBUG: Iniciando descarga para {valor_gerencia}")
    r_cat = session.get(URL_CAT)
    vs_final = extraer_view_state(r_cat.text)
    
    payload = {"j_idt13": "j_idt13", "j_idt13:j_idt15": "j_idt13:j_idt15", "javax.faces.ViewState": vs_final}
    r_pdf = session.post(URL_CAT, data=payload)
    
    print(f"DEBUG: Status code PDF: {r_pdf.status_code}")
    print(f"DEBUG: Tamaño contenido: {len(r_pdf.content)} bytes")
    
    if r_pdf.status_code == 200 and b"%PDF" in r_pdf.content[:20]:
        pdf_temp = f"temp_{valor_gerencia}.pdf"
        with open(pdf_temp, "wb") as f: f.write(r_pdf.content)
        
        mapeo = {}
        with pdfplumber.open(pdf_temp) as pdf:
            for p in pdf.pages:
                tabla = p.extract_table()
                if tabla:
                    for f in tabla:
                        # DEBUG: Imprimir la fila para ver si está extrayendo algo
                        if f and len(f) >= 3 and str(f[0]).strip().isdigit():
                            mapeo[str(f[0]).strip()] = str(f[2]).strip()
        
        print(f"DEBUG: Nombres extraídos: {len(mapeo)}")
        
        if mapeo:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for k, v in mapeo.items(): writer.writerow([k, v])
                f.flush()
                os.fsync(f.fileno())
            print(f"DEBUG: Archivo {csv_path} escrito correctamente.")
        
        if os.path.exists(pdf_temp): os.remove(pdf_temp)
        return mapeo
    else:
        print("DEBUG: ERROR - El servidor no devolvió un PDF válido.")
    return {}
