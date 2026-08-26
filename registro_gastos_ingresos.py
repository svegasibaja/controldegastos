"""
Servidor Python (Flask) para el Shortcut de registro de Ingresos/Gastos.

Flujo:
  iPhone (Shortcut) --POST JSON--> este servidor --> Google Sheets

Columnas que escribe en el sheet:
  Fecha | Tipo | Medio | Categoría | Monto | Descripción
"""

from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS_FILE = "credentials.json"  # se usa si NO hay variable de entorno (uso local)
CREDS_ENV_VAR = "GOOGLE_CREDENTIALS_JSON"  # se usa en producción (ej. Render)
SHEET_ID = os.environ.get("SHEET_ID", "1Di119pOoxU-HjcPBanHGuFS9e9xsAdiKzM1VZsfrKME")
SHEET_NAME = "Registros"
ENCABEZADOS = ["Fecha", "Tipo", "Medio", "Categoría", "Monto", "Descripción"]


def get_sheet():
    """Abre (o crea) la hoja 'Registros' dentro del spreadsheet."""
    creds_json = os.environ.get(CREDS_ENV_VAR)
    if creds_json:
        # Producción: la clave viene como texto en una variable de entorno
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        # Local: se lee del archivo credentials.json
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)

    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEET_ID)

    try:
        worksheet = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(ENCABEZADOS))
        worksheet.append_row(ENCABEZADOS)

    return worksheet


@app.route("/registro", methods=["POST"])
def registro():
    """Recibe el JSON del Shortcut y agrega una fila al sheet."""
    data = request.get_json(force=True, silent=True) or {}

    tipo = data.get("tipo", "")
    medio = data.get("medio", "")
    categoria = data.get("categoria", "")
    monto = data.get("monto", 0)
    descripcion = data.get("descripcion", "")
    fecha = data.get("fecha") or datetime.now().strftime("%Y-%m-%d %H:%M")

    if not tipo or not medio or not monto:
        return jsonify({"status": "error", "mensaje": "Faltan campos obligatorios (tipo, medio, monto)"}), 400

    try:
        worksheet = get_sheet()
        worksheet.append_row([fecha, tipo, medio, categoria, monto, descripcion])
        return jsonify({
            "status": "ok",
            "mensaje": f"✅ {tipo} de {monto} registrado correctamente"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return "Servidor de registro de gastos e ingresos activo ✅"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
