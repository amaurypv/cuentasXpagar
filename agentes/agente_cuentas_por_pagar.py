
import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

def obtener_pagos_manual():
    path = os.path.join(os.path.dirname(__file__), "..", "datos_csv", "registro_pagos.csv")
    if not os.path.exists(path):
        return set()
    try:
        df = pd.read_csv(path)
        return set(df["Folio"].astype(str).str.upper())
    except Exception as e:
        print(f"Error leyendo CSV de pagos manuales: {e}")
        return set()

def obtener_uuids_pagados(carpeta_pagos):
    ns = {'pago20': 'http://www.sat.gob.mx/Pagos20'}
    uuids = set()
    for archivo in os.listdir(carpeta_pagos):
        if archivo.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(carpeta_pagos, archivo))
                root = tree.getroot()
                for relacionado in root.findall('.//pago20:DoctoRelacionado', ns):
                    uuid = relacionado.attrib.get("IdDocumento")
                    if uuid:
                        uuids.add(uuid.upper())
            except Exception as e:
                print(f"Error leyendo pago {archivo}: {e}")
    return uuids

def procesar_facturas_proveedor(carpeta, uuids_pagados, folios_pagados):
    ns = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
    }

    detalles = defaultdict(list)
    resumen = {}

    for archivo in os.listdir(carpeta):
        if archivo.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(carpeta, archivo))
                root = tree.getroot()
                emisor = root.find('cfdi:Emisor', ns)
                timbre = root.find('.//tfd:TimbreFiscalDigital', ns)

                uuid = timbre.attrib.get("UUID", "").upper()
                folio = root.attrib.get("Folio", "").upper()
                fecha = root.attrib.get("Fecha", "")[:10]
                total = float(root.attrib.get("Total", "0"))
                moneda = root.attrib.get("Moneda", "")
                condiciones = root.attrib.get("CondicionesDePago", "0 DIAS")

                nombre = emisor.attrib.get("Nombre", "SIN NOMBRE")
                rfc = emisor.attrib.get("Rfc", "SIN RFC")

                fecha_emision = datetime.strptime(fecha, "%Y-%m-%d")
                dias = int(condiciones.split()[0]) if condiciones.split() else 0
                fecha_venc = fecha_emision + timedelta(days=dias)
                dias_restantes = (fecha_venc - datetime.now()).days

                pagada = uuid in uuids_pagados or folio in folios_pagados
                estatus = "VENCIDA" if dias_restantes < 0 and not pagada else "POR PAGAR"

                total_mxn = total if moneda == "MXN" and not pagada else 0
                total_usd = total if moneda == "USD" and not pagada else 0

                detalles[(nombre, rfc)].append({
                    "UUID": uuid,
                    "Folio": folio,
                    "Fecha de Emisión": fecha_emision.strftime("%d/%m/%Y"),
                    "Fecha de Vencimiento": fecha_venc.strftime("%d/%m/%Y"),
                    "Moneda": moneda,
                    "Días por Vencer / Vencidos": dias_restantes,
                    "¿Pagada?": "Sí" if pagada else "No",
                    "Estatus": estatus,
                    "Total Factura": total,
                    "Total MXN": total_mxn,
                    "Total USD": total_usd
                })

                if (nombre, rfc) not in resumen:
                    resumen[(nombre, rfc)] = {
                        "Total por Cobrar MXN": 0,
                        "Total por Cobrar USD": 0,
                        "Vencidas MXN": 0,
                        "Vencidas USD": 0,
                    }

                if not pagada:
                    if moneda == "MXN":
                        resumen[(nombre, rfc)]["Total por Cobrar MXN"] += total
                        if dias_restantes < 0:
                            resumen[(nombre, rfc)]["Vencidas MXN"] += total
                    elif moneda == "USD":
                        resumen[(nombre, rfc)]["Total por Cobrar USD"] += total
                        if dias_restantes < 0:
                            resumen[(nombre, rfc)]["Vencidas USD"] += total

            except Exception as e:
                print(f"Error procesando {archivo}: {e}")
    return detalles, resumen

def generar_excel():
    base = os.path.dirname(__file__)
    proveedores = os.path.join(base, "..", "xml_proveedores")
    pagos = os.path.join(base, "..", "xml_pagos")

    uuids_pagados = obtener_uuids_pagados(pagos)
    folios_pagados = obtener_pagos_manual()

    detalles, resumen = procesar_facturas_proveedor(proveedores, uuids_pagados, folios_pagados)

    with pd.ExcelWriter("../Cuentas_por_Pagar.xlsx", engine="xlsxwriter") as writer:
        df_resumen = pd.DataFrame([{
            "Proveedor": k[0],
            "RFC": k[1],
            **v
        } for k, v in resumen.items()])
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)

        for (nombre, rfc), facturas in detalles.items():
            hoja = nombre[:31]
            df = pd.DataFrame(facturas)
            columnas = [
                "UUID", "Folio", "Fecha de Emisión", "Fecha de Vencimiento",
                "Moneda", "Días por Vencer / Vencidos", "¿Pagada?", "Estatus",
                "Total Factura", "Total MXN", "Total USD"
            ]
            df = df[columnas]
            totales = {
                "UUID": "TOTAL",
                "Total Factura": df["Total Factura"].sum(),
                "Total MXN": df["Total MXN"].sum(),
                "Total USD": df["Total USD"].sum()
            }
            df = pd.concat([df, pd.DataFrame([totales])], ignore_index=True)
            df.to_excel(writer, sheet_name=hoja, index=False)

if __name__ == "__main__":
    generar_excel()
