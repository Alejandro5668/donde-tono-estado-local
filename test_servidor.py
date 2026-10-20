import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

os.environ["MET_TOKEN"] = "token-de-prueba"

import servidor  # noqa: E402  (necesita MET_TOKEN antes de importarse)
from test_estado import HORARIOS  # noqa: E402


class PruebasServidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
        cls.base = f"http://127.0.0.1:{cls.http.server_address[1]}"
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()

    def llamar(self, ruta="/", cuerpo=None, token="token-de-prueba", metodo="POST"):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        peticion = urllib.request.Request(self.base + ruta, data=datos, method=metodo)
        if token:
            peticion.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(peticion) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_respuesta_correcta(self):
        codigo, cuerpo = self.llamar(cuerpo={"horarios": HORARIOS, "ahora": "2026-10-20T21:45:00"})
        self.assertEqual(codigo, 200)
        self.assertTrue(cuerpo["result"].startswith("SOLO_RECOGER:"), cuerpo)

    def test_sin_token_o_token_malo_es_401(self):
        self.assertEqual(self.llamar(cuerpo={"horarios": HORARIOS}, token=None)[0], 401)
        self.assertEqual(self.llamar(cuerpo={"horarios": HORARIOS}, token="otro")[0], 401)

    def test_datos_invalidos_es_400(self):
        self.assertEqual(self.llamar(cuerpo={})[0], 400)
        self.assertEqual(self.llamar(cuerpo={"horarios": []})[0], 400)
        self.assertEqual(self.llamar(cuerpo={"horarios": HORARIOS, "ahora": "no-es-fecha"})[0], 400)

    def test_salud_no_pide_token(self):
        self.assertEqual(self.llamar("/salud", token=None, metodo="GET"), (200, {"ok": True}))

    def test_ruta_desconocida_es_404(self):
        self.assertEqual(self.llamar("/otra", token=None, metodo="GET")[0], 404)


if __name__ == "__main__":
    unittest.main()
