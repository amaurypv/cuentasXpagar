
import streamlit as st
import os
import shutil
import subprocess
import sys

st.title("Agente de Control de Cuentas")

# Menú principal
opcion = st.selectbox("¿Qué deseas hacer?", ["Selecciona una opción", "Cuentas por Cobrar", "Cuentas por Pagar"])

if opcion == "Cuentas por Cobrar":
    st.header("Cuentas por Cobrar")

    xml_facturas = st.file_uploader("📂 Sube los XML de facturas", type="xml", accept_multiple_files=True)
    xml_complementos = st.file_uploader("📂 Sube los XML de complementos de pago", type="xml", accept_multiple_files=True)
    csv_manual = st.file_uploader("📂 Sube el CSV de pagos manuales", type="csv")

    if st.button("▶️ Generar reporte"):
        os.makedirs("datos_xml/xml_facturas", exist_ok=True)
        os.makedirs("datos_xml/xml_complementos", exist_ok=True)
        os.makedirs("datos_csv", exist_ok=True)

        # Precarga XML base si no existen
        for tipo, carpeta in [("xml_facturas", "datos_iniciales/xml_facturas"), ("xml_complementos", "datos_iniciales/xml_complementos")]:
            if os.path.exists(carpeta):
                for archivo in os.listdir(carpeta):
                    destino = os.path.join("datos_xml", tipo, archivo)
                    if not os.path.exists(destino):
                        shutil.copy(os.path.join(carpeta, archivo), destino)

        # Guardar archivos subidos
        if xml_facturas:
            for archivo in xml_facturas:
                with open(os.path.join("datos_xml/xml_facturas", archivo.name), "wb") as f:
                    f.write(archivo.getbuffer())

        if xml_complementos:
            for archivo in xml_complementos:
                with open(os.path.join("datos_xml/xml_complementos", archivo.name), "wb") as f:
                    f.write(archivo.getbuffer())

        if csv_manual is not None:
            with open("datos_csv/pagadas_manual.csv", "wb") as f:
                f.write(csv_manual.getbuffer())
        elif not os.path.exists("datos_csv/pagadas_manual.csv") and os.path.exists("datos_iniciales/pagadas_manual.csv"):
            shutil.copy("datos_iniciales/pagadas_manual.csv", "datos_csv/pagadas_manual.csv")

        st.subheader("📂 Archivos detectados antes de procesar:")
        st.write("- Facturas:", len(os.listdir("datos_xml/xml_facturas")))
        st.write("- Complementos:", len(os.listdir("datos_xml/xml_complementos")))
        st.write("- Pagos manuales:", "✅" if os.path.exists("datos_csv/pagadas_manual.csv") else "❌")

        script_path = os.path.join("agentes", "agente_cuentas_por_cobrar.py")
        resultado = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

        if resultado.returncode == 0:
            st.success("✅ Reporte generado con éxito.")
            resumen = [line for line in resultado.stdout.splitlines() if "clientes" in line or "procesadas" in line or "Archivo generado" in line]
            for linea in resumen:
                st.success(linea.replace("Archivo generado:", "✅ Archivo listo para descargar"))
            if os.path.exists("Cuentas_por_Cobrar_Emitidas.xlsx"):
                with open("Cuentas_por_Cobrar_Emitidas.xlsx", "rb") as f:
                    st.download_button("⬇️ Descargar reporte", f, file_name="Cuentas_por_Cobrar_Emitidas.xlsx")
        else:
            st.error("❌ Error al ejecutar el script.")
            st.text(resultado.stderr)

elif opcion == "Cuentas por Pagar":
    st.header("Cuentas por Pagar")

    xml_proveedores = st.file_uploader("📂 Sube los XML de facturas de proveedores", type="xml", accept_multiple_files=True)
    xml_pagos = st.file_uploader("📂 Sube los XML de complementos de pago", type="xml", accept_multiple_files=True)
    csv_registro = st.file_uploader("📂 Sube el CSV de pagos manuales", type="csv")

    if st.button("▶️ Generar reporte"):
        os.makedirs("xml_proveedores", exist_ok=True)
        os.makedirs("xml_pagos", exist_ok=True)
        os.makedirs("datos_csv", exist_ok=True)

        # Precargar XML base si no están copiados aún
        for tipo, carpeta in [("xml_proveedores", "datos_iniciales/xml_proveedores"), ("xml_pagos", "datos_iniciales/xml_pagos")]:
            if os.path.exists(carpeta):
                for archivo in os.listdir(carpeta):
                    destino = os.path.join(tipo, archivo)
                    if not os.path.exists(destino):
                        shutil.copy(os.path.join(carpeta, archivo), destino)

        # Guardar archivos subidos
        if xml_proveedores:
            for archivo in xml_proveedores:
                with open(os.path.join("xml_proveedores", archivo.name), "wb") as f:
                    f.write(archivo.getbuffer())

        if xml_pagos:
            for archivo in xml_pagos:
                with open(os.path.join("xml_pagos", archivo.name), "wb") as f:
                    f.write(archivo.getbuffer())

        if csv_registro is not None:
            with open("datos_csv/registro_pagos.csv", "wb") as f:
                f.write(csv_registro.getbuffer())
        elif not os.path.exists("datos_csv/registro_pagos.csv") and os.path.exists("datos_iniciales/registro_pagos.csv"):
            shutil.copy("datos_iniciales/registro_pagos.csv", "datos_csv/registro_pagos.csv")

        st.subheader("📂 Archivos detectados antes de procesar:")
        st.write("- Facturas proveedor:", len(os.listdir("xml_proveedores")))
        st.write("- Complementos proveedor:", len(os.listdir("xml_pagos")))
        st.write("- Pagos manuales:", "✅" if os.path.exists("datos_csv/registro_pagos.csv") else "❌")

        script_path = os.path.join("agentes", "agente_cuentas_por_pagar.py")
        resultado = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

        if resultado.returncode == 0:
            st.success("✅ Reporte generado con éxito.")
            resumen = [line for line in resultado.stdout.splitlines() if "proveedores" in line or "procesadas" in line or "Archivo generado" in line]
            for linea in resumen:
                st.success(linea.replace("Archivo generado:", "✅ Archivo listo para descargar"))
            if os.path.exists("Cuentas_por_Pagar.xlsx"):
                with open("Cuentas_por_Pagar.xlsx", "rb") as f:
                    st.download_button("⬇️ Descargar reporte", f, file_name="Cuentas_por_Pagar.xlsx")
        else:
            st.error("❌ Error al ejecutar el script.")
            st.text(resultado.stderr)
