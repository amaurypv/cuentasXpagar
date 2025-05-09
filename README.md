# 🧾 Agente de Control de Cuentas por Cobrar

Esta aplicación en Streamlit permite generar un reporte automático de **cuentas por cobrar** a partir de facturas electrónicas en formato XML (CFDI 4.0) y sus complementos de pago. También permite registrar pagos manuales en CSV.

---

## 🛠 ¿Qué hace esta app?

- 📂 Carga y procesa archivos XML de facturas y complementos.
- ✅ Detecta automáticamente si las facturas ya han sido pagadas (por complemento o por CSV).
- ❌ Elimina duplicados (tanto por nombre como por contenido).
- 📊 Genera un archivo Excel con:
  - Hoja de **resumen por cliente**
  - Una hoja por cliente con desglose detallado
  - Totales separados por moneda (MXN y USD)
- 🧠 Incluye facturas **precargadas** del año en curso si no se suben nuevos XML.

---

## 📁 Estructura de carpetas

\`\`\`
agente_web/
├── interfaz.py                     # App principal de Streamlit
├── agentes/
│   └── agente_cuentas_por_cobrar.py
├── datos_iniciales/
│   ├── xml_facturas/              # XML base del año
│   └── xml_complementos/
├── datos_xml/
│   ├── xml_facturas/              # Se llena dinámicamente
│   └── xml_complementos/
├── datos_csv/
│   └── pagadas_manual.csv         # (opcional)
├── requirements.txt
\`\`\`

---

## 🚀 Cómo usar esta app

1. Sube los archivos XML de facturas y complementos (o deja que cargue los precargados).
2. Sube un CSV con folios de facturas ya pagadas (opcional).
3. Haz clic en **"Generar reporte"**.
4. Descarga el archivo Excel generado.

---

## 🧪 Tecnologías utilizadas

- Python
- Streamlit
- pandas
- openpyxl
- lxml

---

## ☁️ Despliegue en Streamlit Cloud

Si deseas desplegar esta app tú mismo:

1. Haz un fork o clona este repositorio.
2. Entra a [https://streamlit.io/cloud](https://streamlit.io/cloud).
3. Conecta tu cuenta de GitHub.
4. Selecciona este repositorio.
5. Define como archivo principal: `interfaz.py`
6. ¡Listo! Tu app estará publicada en la nube.

---

## 📬 Contacto

Para sugerencias, mejoras o soporte:  
**Amaury Pérez** | Chihuahua, México  
