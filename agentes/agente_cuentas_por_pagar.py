
import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

def obtener_uuids_pagados(carpeta_complementos):
    ns = {'pago20': 'http://www.sat.gob.mx/Pagos20'}
    uuids_pagados = set()
    for archivo in os.listdir(carpeta_complementos):
        if archivo.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(carpeta_complementos, archivo))
                root = tree.getroot()
                relacionados = root.findall('.//pago20:DoctoRelacionado', ns)
                for d in relacionados:
                    uuid = d.attrib.get("IdDocumento")
                    if uuid:
                        uuids_pagados.add(uuid.upper())
            except Exception as e:
                print(f"Error en complemento {archivo}: {e}")
    return uuids_pagados

def obtener_folios_pagados_manualmente():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "..", "datos_csv", "registro_pagos.csv")
    if not os.path.exists(csv_path):
        return set()
    try:
        df = pd.read_csv(csv_path)
        return set(df["Folio"].astype(str).str.upper())
    except Exception as e:
        print(f"Error leyendo CSV manual: {e}")
        return set()

def procesar_facturas(carpeta_facturas, uuids_pagados, folios_pagados):
    ns = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
    }
    detalles_por_proveedor = defaultdict(list)
    resumen_proveedores = {}

    for archivo in os.listdir(carpeta_facturas):
        if archivo.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(carpeta_facturas, archivo))
                root = tree.getroot()
                comprobante = root
                emisor = comprobante.find('cfdi:Emisor', ns)
                timbre = root.find('.//tfd:TimbreFiscalDigital', ns)

                uuid = timbre.attrib.get("UUID", "SIN_UUID").upper()
                folio = comprobante.attrib.get("Folio", "").upper()
                fecha = comprobante.attrib.get("Fecha", "")[:10]
                total = float(comprobante.attrib.get("Total", "0"))
                moneda = comprobante.attrib.get("Moneda", "")
                condiciones = comprobante.attrib.get("CondicionesDePago", "0 DIAS")
                metodo_pago = comprobante.attrib.get("MetodoPago", "")

                proveedor_nombre = emisor.attrib.get("Nombre", "SIN NOMBRE")
                proveedor_rfc = emisor.attrib.get("Rfc", "SIN RFC")

                fecha_emision = datetime.strptime(fecha, "%Y-%m-%d")
                try:
                    dias_credito = int(condiciones.split()[0])
                except:
                    dias_credito = 0
                fecha_vencimiento = fecha_emision + timedelta(days=dias_credito)
                hoy = datetime.now()
                dias_por_vencer = (fecha_vencimiento - hoy).days

                pagada = uuid in uuids_pagados or folio in folios_pagados
                vencida = dias_por_vencer < 0 and not pagada
                estatus = "VENCIDA" if vencida else "POR PAGAR"

                total_mxn = total if not pagada and moneda == "MXN" else 0
                total_usd = total if not pagada and moneda == "USD" else 0

                detalles_por_proveedor[(proveedor_nombre, proveedor_rfc)].append({
                    "UUID": uuid,
                    "Folio": folio,
                    "Fecha de Emisión": fecha_emision.strftime("%d/%m/%Y"),
                    "Fecha de Vencimiento": fecha_vencimiento.strftime("%d/%m/%Y"),
                    "Moneda": moneda,
                    "Método de Pago": metodo_pago,
                    "Condiciones de Pago": condiciones,
                    "Días por Vencer / Vencidos": dias_por_vencer,
                    "¿Pagada?": "Sí" if pagada else "No",
                    "Estatus": estatus,
                    "Total Factura": total,
                    "Total MXN": total_mxn,
                    "Total USD": total_usd
                })

                clave = (proveedor_nombre, proveedor_rfc)
                if clave not in resumen_proveedores:
                    resumen_proveedores[clave] = {
                        "MXN": 0, "USD": 0, "Facturas": 0,
                        "Vencidas_MXN": 0, "Vencidas_USD": 0
                    }

                if not pagada:
                    if moneda == "MXN":
                        resumen_proveedores[clave]["MXN"] += total
                    elif moneda == "USD":
                        resumen_proveedores[clave]["USD"] += total

                if vencida:
                    if moneda == "MXN":
                        resumen_proveedores[clave]["Vencidas_MXN"] += total
                    elif moneda == "USD":
                        resumen_proveedores[clave]["Vencidas_USD"] += total

                resumen_proveedores[clave]["Facturas"] += 1

            except Exception as e:
                print(f"Error procesando factura {archivo}: {e}")
    return detalles_por_proveedor, resumen_proveedores

def generar_excel(carpeta_facturas, carpeta_complementos):
    os.makedirs(carpeta_facturas, exist_ok=True)
    os.makedirs(carpeta_complementos, exist_ok=True)

    uuids_pagados = obtener_uuids_pagados(carpeta_complementos)
    folios_pagados = obtener_folios_pagados_manualmente()

    detalles, resumen = procesar_facturas(carpeta_facturas, uuids_pagados, folios_pagados)

    resumen_data = []
    hojas = {}

    for (nombre, rfc), totales in resumen.items():
        resumen_data.append({
            "Proveedor": nombre,
            "RFC": rfc,
            "Total por Pagar MXN": totales["MXN"],
            "Total por Pagar USD": totales["USD"],
            "Nº Facturas": totales["Facturas"],
            "Vencidas MXN": totales["Vencidas_MXN"],
            "Vencidas USD": totales["Vencidas_USD"]
        })

    for (nombre, rfc), facturas in detalles.items():
        hoja = nombre[:31]
        df = pd.DataFrame(facturas)
        columnas = [
            "UUID", "Folio", "Fecha de Emisión", "Fecha de Vencimiento",
            "Moneda", "Método de Pago", "Condiciones de Pago",
            "Días por Vencer / Vencidos", "¿Pagada?", "Estatus",
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
        hojas[hoja] = df

    print(f"Se procesaron {len(detalles)} proveedores.")
    print(f"Número total de facturas procesadas: {sum(len(v) for v in detalles.values())}")

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Cuentas_por_Pagar.xlsx")
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name="Resumen", index=False)
        for hoja, df in hojas.items():
            df.to_excel(writer, sheet_name=hoja, index=False)

    print(f"Archivo generado: {output_path}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    carpeta_facturas = os.path.join(base, "..", "xml_proveedores")
    carpeta_complementos = os.path.join(base, "..", "xml_pagos")
    generar_excel(carpeta_facturas, carpeta_complementos)
