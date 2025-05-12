import streamlit as st
import os
import shutil
import subprocess
import sys

st.title("Agente de Control de Cuentas")
st.header("Cuentas por Cobrar")

# Subida de archivos
xml_facturas = st.file_uploader("📂 Sube los XML de facturas", type="xml", accept_multiple_files=True)
xml_complementos = st.file_uploader("📂 Sube los XML de complementos de pago", type="xml", accept_multiple_files=True)
csv_manual = st.file_uploader("📂 Sube el CSV de pagos manuales", type="csv")

if st.button("▶️ Generar reporte"):
    # Crear carpetas necesarias
    os.makedirs("datos_xml/xml_facturas", exist_ok=True)
    os.makedirs("datos_xml/xml_complementos", exist_ok=True)
    os.makedirs("datos_csv", exist_ok=True)

    # ✅ Copiar XML iniciales siempre (si aún no están copiados)
    iniciales_facturas = "datos_iniciales/xml_facturas"
    if os.path.exists(iniciales_facturas):
        for archivo in os.listdir(iniciales_facturas):
            destino = os.path.join("datos_xml/xml_facturas", archivo)
            if not os.path.exists(destino):
                shutil.copy(os.path.join(iniciales_facturas, archivo), destino)

    iniciales_complementos = "datos_iniciales/xml_complementos"
    if os.path.exists(iniciales_complementos):
        for archivo in os.listdir(iniciales_complementos):
            destino = os.path.join("datos_xml/xml_complementos", archivo)
            if not os.path.exists(destino):
                shutil.copy(os.path.join(iniciales_complementos, archivo), destino)

    # Agregar XML subidos (sin borrar los iniciales)
    if xml_facturas:
        for archivo in xml_facturas:
            with open(os.path.join("datos_xml/xml_facturas", archivo.name), "wb") as f:
                f.write(archivo.getbuffer())

    if xml_complementos:
        for archivo in xml_complementos:
            with open(os.path.join("datos_xml/xml_complementos", archivo.name), "wb") as f:
                f.write(archivo.getbuffer())

    # ✅ Guardar CSV manual si se subió (reemplaza)
    if csv_manual is not None:
        with open("datos_csv/pagadas_manual.csv", "wb") as f:
            f.write(csv_manual.getbuffer())

    # ✅ Copiar CSV base si no se subió uno
    elif not os.path.exists("datos_csv/pagadas_manual.csv") and os.path.exists("datos_iniciales/pagadas_manual.csv"):
        shutil.copy("datos_iniciales/pagadas_manual.csv", "datos_csv/pagadas_manual.csv")

    # Mostrar archivos detectados
    st.subheader("📂 Archivos detectados antes de procesar:")
    st.write("- Facturas:", len(os.listdir("datos_xml/xml_facturas")))
    st.write("- Complementos:", len(os.listdir("datos_xml/xml_complementos")))
    if os.path.exists("datos_csv/pagadas_manual.csv"):
        st.write("- Pagos manuales: ✅")
    else:
        st.write("- Pagos manuales: ❌")

    # Ejecutar script
    script_path = os.path.join(os.path.dirname(__file__), "agentes", "agente_cuentas_por_cobrar.py")
    resultado = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

    if resultado.returncode == 0:
        st.success("✅ Reporte generado con éxito.")

        # Mostrar resumen útil desde stdout
        resumen = []
        for linea in resultado.stdout.splitlines():
            if (
                "clientes con facturas" in linea
                or "facturas procesadas" in linea
                or "Archivo generado" in linea
            ):
                resumen.append(linea)

        if resumen:
            st.subheader("📊 Resumen del análisis:")
            for linea in resumen:
                st.success(linea.replace("Archivo generado:", "✅ Archivo listo para descargar"))
        else:
            st.info("El script se ejecutó, pero no se encontró información resumida.")

        # Mostrar botón de descarga
        archivo_generado = "Cuentas_por_Cobrar_Emitidas.xlsx"
        if os.path.exists(archivo_generado):
            with open(archivo_generado, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar reporte",
                    data=f,
                    file_name="Cuentas_por_Cobrar_Emitidas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("⚠️ El archivo no se encontró en la ruta esperada.")
    else:
        st.error("❌ Error al ejecutar el script.")
        st.text(resultado.stderr)
