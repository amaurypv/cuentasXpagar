import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

def eliminar_xml_duplicados_por_hash(directorio):
    vistos = {}
    for archivo in os.listdir(directorio):
        if archivo.endswith(".xml"):
            ruta = os.path.join(directorio, archivo)
            try:
                with open(ruta, "rb") as f:
                    contenido = f.read()
                    hash_archivo = hashlib.sha256(contenido).hexdigest()
                if hash_archivo in vistos:
                    print(f"[DEBUG] Eliminando duplicado físico: {archivo}")
                    os.remove(ruta)
                else:
                    vistos[hash_archivo] = archivo
            except Exception as e:
                print(f"[ERROR] No se pudo procesar {archivo}: {e}")

def obtener_folios_pagados_manualmente(csv_path="../datos_csv/pagadas_manual.csv"):
    if not os.path.exists(csv_path):
        print(f"[DEBUG] Archivo CSV manual no encontrado: {csv_path}")
        return set()
    try:
        df = pd.read_csv(csv_path)
        return set(df["Folio"].astype(str).str.upper())
    except Exception as e:
        print(f"Error leyendo el archivo CSV de pagos manuales: {e}")
        return set()

def obtener_uuids_pagados(carpeta_complementos):
    ns = {'pago20': 'http://www.sat.gob.mx/Pagos20'}
    uuids_pagados = set()
    print(f"[DEBUG] Carpeta complementos: {carpeta_complementos}")
    print(f"[DEBUG] Archivos en complementos: {os.listdir(carpeta_complementos)}")
    for archivo in os.listdir(carpeta_complementos):
        if archivo.endswith(".xml"):
            ruta = os.path.join(carpeta_complementos, archivo)
            try:
                tree = ET.parse(ruta)
                root = tree.getroot()
                doctos = root.findall('.//pago20:DoctoRelacionado', ns)
                for d in doctos:
                    uuid = d.attrib.get("IdDocumento")
                    if uuid:
                        uuid = uuid.upper()
                        if uuid in uuids_pagados:
                            print(f"[DEBUG] Complemento duplicado ignorado: {uuid}")
                        else:
                            uuids_pagados.add(uuid)
            except Exception as e:
                print(f"Error procesando complemento {archivo}: {e}")
    return uuids_pagados

def procesar_facturas_emitidas(carpeta_facturas, uuids_pagados, folios_pagados_manual):
    ns = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
    }
    detalles_por_cliente = defaultdict(list)
    resumen_clientes = {}

    print(f"[DEBUG] Carpeta facturas: {carpeta_facturas}")
    print(f"[DEBUG] Archivos en facturas: {os.listdir(carpeta_facturas)}")

    uuids_vistos = set()

    for archivo in os.listdir(carpeta_facturas):
        if archivo.endswith(".xml"):
            ruta = os.path.join(carpeta_facturas, archivo)
            try:
                tree = ET.parse(ruta)
                root = tree.getroot()
                comprobante = root
                receptor = comprobante.find('cfdi:Receptor', ns)
                timbre = root.find('.//tfd:TimbreFiscalDigital', ns)

                uuid = timbre.attrib.get("UUID", "SIN_UUID").upper()
                if uuid in uuids_vistos:
                    print(f"[DEBUG] Factura duplicada ignorada: {uuid}")
                    continue
                uuids_vistos.add(uuid)

                folio = comprobante.attrib.get('Folio', '').upper()
                fecha_emision = comprobante.attrib.get('Fecha', '')
                total = float(comprobante.attrib.get('Total', '0'))
                moneda = comprobante.attrib.get('Moneda', '')
                metodo_pago = comprobante.attrib.get('MetodoPago', '')
                condiciones_pago = comprobante.attrib.get('CondicionesDePago', '0 DIAS')
                cliente_nombre = receptor.attrib.get('Nombre', 'SIN NOMBRE')
                cliente_rfc = receptor.attrib.get('Rfc', 'SIN RFC')

                fecha_emision_dt = datetime.strptime(fecha_emision[:10], '%Y-%m-%d')
                try:
                    dias_credito = int(condiciones_pago.split()[0])
                except ValueError:
                    dias_credito = 0
                fecha_vencimiento = fecha_emision_dt + timedelta(days=dias_credito)
                hoy = datetime.now()
                dias_por_vencer = (fecha_vencimiento - hoy).days

                pagada = uuid in uuids_pagados or folio in folios_pagados_manual
                vencida = dias_por_vencer < 0 and not pagada
                estatus = "VENCIDA" if vencida else "POR PAGAR"

                total_mxn = total if not pagada and moneda == "MXN" else 0
                total_usd = total if not pagada and moneda == "USD" else 0
                vencidas_mxn = total if vencida and moneda == "MXN" else 0
                vencidas_usd = total if vencida and moneda == "USD" else 0

                detalles_por_cliente[(cliente_nombre, cliente_rfc)].append({
                    "UUID": uuid,
                    "Folio": folio,
                    "Fecha de Emisión": fecha_emision_dt.strftime('%d/%m/%Y'),
                    "Fecha de Vencimiento": fecha_vencimiento.strftime('%d/%m/%Y'),
                    "Moneda": moneda,
                    "Método de Pago": metodo_pago,
                    "Condiciones de Pago": condiciones_pago,
                    "Días por Vencer / Vencidos": dias_por_vencer,
                    "¿Pagada?": "Sí" if pagada else "No",
                    "Estatus": estatus,
                    "Total Factura": total,
                    "Total MXN": total_mxn,
                    "Total USD": total_usd
                })

                clave = (cliente_nombre, cliente_rfc)
                if clave not in resumen_clientes:
                    resumen_clientes[clave] = {
                        "MXN": 0, "USD": 0, "Facturas": 0,
                        "Vencidas_MXN": 0, "Vencidas_USD": 0
                    }

                if not pagada:
                    if moneda == "MXN":
                        resumen_clientes[clave]["MXN"] += total
                    elif moneda == "USD":
                        resumen_clientes[clave]["USD"] += total

                if vencida:
                    if moneda == "MXN":
                        resumen_clientes[clave]["Vencidas_MXN"] += total
                    elif moneda == "USD":
                        resumen_clientes[clave]["Vencidas_USD"] += total

                resumen_clientes[clave]["Facturas"] += 1

            except Exception as e:
                print(f"Error procesando factura {archivo}: {e}")

    return detalles_por_cliente, resumen_clientes

def generar_excel(carpeta_facturas, carpeta_complementos):
    os.makedirs(carpeta_facturas, exist_ok=True)
    os.makedirs(carpeta_complementos, exist_ok=True)

    # ✅ Eliminar duplicados físicos antes de procesar
    eliminar_xml_duplicados_por_hash(carpeta_facturas)
    eliminar_xml_duplicados_por_hash(carpeta_complementos)

    folios_pagados_manual = obtener_folios_pagados_manualmente()
    uuids_pagados = obtener_uuids_pagados(carpeta_complementos)
    detalles_por_cliente, resumen_clientes = procesar_facturas_emitidas(
        carpeta_facturas, uuids_pagados, folios_pagados_manual
    )

    resumen_data = []
    hojas_clientes = {}

    for (nombre, rfc), totales in resumen_clientes.items():
        resumen_data.append({
            "Cliente (Razón Social)": nombre,
            "RFC Cliente": rfc,
            "Total por Cobrar MXN": totales["MXN"],
            "Total por Cobrar USD": totales["USD"],
            "Nº Facturas": totales["Facturas"],
            "Vencidas MXN": totales["Vencidas_MXN"],
            "Vencidas USD": totales["Vencidas_USD"]
        })

    for (nombre, rfc), facturas in detalles_por_cliente.items():
        hoja_nombre = nombre[:31]
        df = pd.DataFrame(facturas)

        columnas_ordenadas = [
            "UUID", "Folio", "Fecha de Emisión", "Fecha de Vencimiento",
            "Moneda", "Método de Pago", "Condiciones de Pago",
            "Días por Vencer / Vencidos", "¿Pagada?", "Estatus",
            "Total Factura", "Total MXN", "Total USD"
        ]
        df = df[columnas_ordenadas]

        totales = {
            "UUID": "TOTAL",
            "Total Factura": df["Total Factura"].sum(),
            "Total MXN": df["Total MXN"].sum(),
            "Total USD": df["Total USD"].sum()
        }
        df = pd.concat([df, pd.DataFrame([totales])], ignore_index=True)

        hojas_clientes[hoja_nombre] = df

    print(f"Se procesaron {len(detalles_por_cliente)} clientes con facturas.")
    total_facturas = sum(len(f) for f in detalles_por_cliente.values())
    print(f"Número total de facturas procesadas: {total_facturas}")

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Cuentas_por_Cobrar_Emitidas.xlsx")
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name="Resumen", index=False)
        for hoja, df in hojas_clientes.items():
            df.to_excel(writer, sheet_name=hoja, index=False)

    print(f"Archivo generado: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    carpeta_facturas = os.path.join(base_dir, "..", "datos_xml", "xml_facturas")
    carpeta_complementos = os.path.join(base_dir, "..", "datos_xml", "xml_complementos")
    generar_excel(carpeta_facturas, carpeta_complementos)
