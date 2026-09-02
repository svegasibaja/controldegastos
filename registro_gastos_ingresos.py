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
from zoneinfo import ZoneInfo
import os
import json
import sys

app = Flask(__name__)

ZONA_HORARIA = ZoneInfo("America/Bogota")  # UTC-5, hora de Colombia


def log(msg):
    """Imprime inmediatamente en los logs de Render (sin buffer)."""
    print(msg, flush=True)
    sys.stdout.flush()

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
    log("[1/5] Leyendo credenciales...")
    creds_json = os.environ.get(CREDS_ENV_VAR)
    if creds_json:
        log("[2/5] Usando GOOGLE_CREDENTIALS_JSON (producción)")
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        log("[2/5] Usando archivo credentials.json (local)")
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)

    log("[3/5] Autorizando con gspread...")
    client = gspread.authorize(creds)

    log(f"[4/5] Abriendo sheet {SHEET_ID}...")
    sh = client.open_by_key(SHEET_ID)

    log("[5/5] Buscando/creando pestaña Registros...")
    try:
        worksheet = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(ENCABEZADOS))
        worksheet.append_row(ENCABEZADOS)

    log("OK: sheet listo")
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
    fecha = data.get("fecha") or datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d %H:%M")

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


@app.route("/diag", methods=["GET"])
def diag():
    """Ruta de diagnóstico: prueba la conexión con Google Sheets sin escribir nada,
    y muestra en pantalla en qué paso falla (si falla)."""
    try:
        log("=== DIAG: iniciando prueba ===")
        worksheet = get_sheet()
        log("=== DIAG: éxito ===")
        return jsonify({"status": "ok", "mensaje": "Conexión con Google Sheets exitosa ✅"}), 200
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log(f"=== DIAG: ERROR ===\n{tb}")
        return jsonify({"status": "error", "mensaje": str(e), "traceback": tb}), 500


@app.route("/", methods=["GET"])
def home():
    return "Servidor de registro de gastos e ingresos activo ✅"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
