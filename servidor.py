"""Servidor HTTP mínimo que Meteor llama como Función IA (handler HTTP).

POST /  con  Authorization: Bearer <MET_TOKEN>
  cuerpo: {"horarios": <lista o texto JSON>, "corte_minutos": 30, "ahora": "2026-10-19T23:10:00"}
  `corte_minutos` y `ahora` son opcionales (`ahora` sirve para probar a cualquier hora).
  respuesta: {"result": "ABIERTO_DOMICILIO: Abierto. Se reciben domicilios hasta las ..."}

GET /salud  responde {"ok": true} sin autenticación (para mantener despierto el servicio).
"""
import hmac
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from estado import estado

TOKEN = os.environ.get("MET_TOKEN", "")
PUERTO = int(os.environ.get("PORT", "8080"))


class Manejador(BaseHTTPRequestHandler):
    def _responder(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _autorizado(self):
        recibido = self.headers.get("Authorization", "").encode("utf-8")
        return bool(TOKEN) and hmac.compare_digest(recibido, f"Bearer {TOKEN}".encode("utf-8"))

    def do_GET(self):
        if self.path == "/salud":
            return self._responder(200, {"ok": True})
        self._responder(404, {"error": "no encontrado"})

    def do_POST(self):
        crudo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self._autorizado():
            return self._responder(401, {"error": "no autorizado"})
        try:
            args = json.loads(crudo or b"{}")
            ahora = datetime.fromisoformat(args["ahora"]) if args.get("ahora") else None
            resultado = estado(args["horarios"], ahora, int(args.get("corte_minutos", 30)))
        except (KeyError, ValueError, TypeError) as error:
            return self._responder(400, {"error": f"datos inválidos: {error}"})
        self._responder(200, {"result": f"{resultado['estado']}: {resultado['mensaje']}"})

    def log_message(self, formato, *args):  # no registrar cuerpos ni cabeceras
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Falta la variable de entorno MET_TOKEN")
    print(f"Escuchando en el puerto {PUERTO}")
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador).serve_forever()
