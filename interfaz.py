
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account
import subprocess
import sys
import os

credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp"])
client = storage.Client(credentials=credentials)
bucket = client.bucket("cuentas_pagar")

st.title("Agente de Control de Cuentas")
opcion = st.selectbox("¿Qué deseas hacer?", ["Selecciona una opción", "Cuentas por Cobrar", "Cuentas por Pagar"])

def guardar_archivos(files, prefix):
    for file in files:
        blob = bucket.blob(f"{prefix}/{file.name}")
        blob.upload_from_string(file.getvalue())

def descargar_archivos(prefix, destino_local):
    os.makedirs(destino_local, exist_ok=True)
    for blob in bucket.list_blobs(prefix=prefix):
        local_path = os.path.join(destino_local, os.path.basename(blob.name))
        blob.download_to_filename(local_path)

if opcion == "Cuentas por Cobrar":
    st.header("Cuentas por Cobrar")
    xml_facturas = st.file_uploader("📂 XML de facturas emitidas", type="xml", accept_multiple_files=True)
    xml_complementos = st.file_uploader("📂 XML de complementos de pago", type="xml", accept_multiple_files=True)
    csv_manual = st.file_uploader("📂 CSV de pagos manuales", type="csv")

    if st.button("▶️ Generar reporte"):
        if xml_facturas:
            guardar_archivos(xml_facturas, "xml_facturas")
        if xml_complementos:
            guardar_archivos(xml_complementos, "xml_complementos")
        if csv_manual:
            blob = bucket.blob("pagadas_manual.csv")
            blob.upload_from_string(csv_manual.getvalue())

        descargar_archivos("xml_facturas", "datos_xml/xml_facturas")
        descargar_archivos("xml_complementos", "datos_xml/xml_complementos")
        try:
            blob = bucket.blob("pagadas_manual.csv")
            blob.download_to_filename("datos_csv/pagadas_manual.csv")
        except:
            pass

        resultado = subprocess.run([sys.executable, "agentes/agente_cuentas_por_cobrar.py"], capture_output=True, text=True)
        if resultado.returncode == 0 and os.path.exists("Cuentas_por_Cobrar_Emitidas.xlsx"):
            with open("Cuentas_por_Cobrar_Emitidas.xlsx", "rb") as f:
                st.download_button("⬇️ Descargar reporte", f, file_name="Cuentas_por_Cobrar_Emitidas.xlsx")
        else:
            st.error("Error al generar el reporte")

elif opcion == "Cuentas por Pagar":
    st.header("Cuentas por Pagar")
    xml_proveedores = st.file_uploader("📂 XML de facturas de proveedores", type="xml", accept_multiple_files=True)
    xml_pagos = st.file_uploader("📂 XML de complementos de pago", type="xml", accept_multiple_files=True)
    csv_registro = st.file_uploader("📂 CSV de pagos manuales", type="csv")

    if st.button("▶️ Generar reporte"):
        if xml_proveedores:
            guardar_archivos(xml_proveedores, "xml_proveedores")
        if xml_pagos:
            guardar_archivos(xml_pagos, "xml_pagos")
        if csv_registro:
            blob = bucket.blob("registro_pagos.csv")
            blob.upload_from_string(csv_registro.getvalue())

        descargar_archivos("xml_proveedores", "xml_proveedores")
        descargar_archivos("xml_pagos", "xml_pagos")
        try:
            blob = bucket.blob("registro_pagos.csv")
            blob.download_to_filename("datos_csv/registro_pagos.csv")
        except:
            pass

        resultado = subprocess.run([sys.executable, "agentes/agente_cuentas_por_pagar.py"], capture_output=True, text=True)
        if resultado.returncode == 0 and os.path.exists("Cuentas_por_Pagar.xlsx"):
            with open("Cuentas_por_Pagar.xlsx", "rb") as f:
                st.download_button("⬇️ Descargar reporte", f, file_name="Cuentas_por_Pagar.xlsx")
        else:
            st.error("Error al generar el reporte")
