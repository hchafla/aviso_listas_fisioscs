def procesar_gerencia(session, nombre, valor_gerencia):
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    fichero_estado = f"estado_{valor_gerencia}.txt"

    try:
        # (Lógica de requests y extracción igual)
        # ... [omitido para brevedad, mantén el tuyo] ...

        # Procesamiento y comparación
        datos_actuales = ""
        lineas_ord, lineas_disc = [], []
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: estado_ant = f.read().strip()

        for idx, fila in enumerate(filas):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
            datos_actuales += info_linea + "|"
            
            # Formato de línea con negrita si hubo cambio
            texto_linea = f"  • {celdas[0]} ➔ Gerencia: `{celdas[1]}` | Global: `{celdas[2]}`"
            if estado_ant and info_linea not in estado_ant:
                texto_linea = f"**{texto_linea}**"
            
            if idx < 3: lineas_ord.append(texto_linea)
            else: lineas_disc.append(texto_linea)

        if datos_actuales != estado_ant:
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
            msg = (f"🔄 *SCS: {nombre}*\n"
                   f"🏥 _Fisioterapeuta_\n\n"
                   f"📋 *Ordinarios:*\n" + "\n".join(lineas_ord) + "\n\n"
                   f"♿ *Discapacidad:*\n" + "\n".join(lineas_disc) + "\n\n"
                   f"🔗 [Ver en la web]({URL_WEB})")
            enviar_telegram(msg)
            
    except Exception as e:
        print(f"Error en {nombre}: {e}")
