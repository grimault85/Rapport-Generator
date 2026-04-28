"""
La Carte — API Flask : génération PDF Audit Menu
Route : POST /audit-menu
"""

import json
import logging
from flask import Flask, request, jsonify, Response
from pdf_generator import generate_pdf

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "lacarte-pdf-api"})


@app.route("/audit-menu", methods=["POST", "OPTIONS"])
def audit_menu():
    # CORS preflight
    if request.method == "OPTIONS":
        return _cors_response("", 204)

    if not request.is_json:
        return _cors_response(jsonify({"error": "Content-Type doit être application/json"}), 400)

    data = request.get_json(silent=True)
    if data is None:
        return _cors_response(jsonify({"error": "JSON invalide ou vide"}), 400)

    restaurant = data.get("infos", {}).get("restaurant", "rapport")

    try:
        pdf_bytes = generate_pdf(data)
    except Exception as e:
        app.logger.error(f"Erreur génération PDF : {e}", exc_info=True)
        return _cors_response(jsonify({"error": "Erreur lors de la génération du PDF", "detail": str(e)}), 500)

    filename = f"audit_menu_{restaurant.replace(' ', '_')}.pdf"
    response = Response(
        pdf_bytes,
        status=200,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        }
    )
    app.logger.info(f"PDF généré : {filename} ({len(pdf_bytes)} bytes)")
    return response


def _cors_response(body, status=200):
    if isinstance(body, str):
        resp = Response(body, status=status)
    else:
        resp = body
        resp.status_code = status
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
