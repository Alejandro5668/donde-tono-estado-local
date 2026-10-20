import unittest
from datetime import datetime

from estado import ZONA, estado, hora_texto

# Tabla de Horarios de Donde Toño, tal como la entrega Meteor (la cruda del reto).
HORARIOS = [
    {"dia": "Lunes", "cerrado": True},
    {"dia": "Martes", "abre": "12:00", "cierra": "22:00", "cruza_medianoche": False},
    {"dia": "Miércoles", "abre": "12:00", "cierra": "22:00", "cruza_medianoche": False},
    {"dia": "Jueves", "abre": "12:00", "cierra": "22:00", "cruza_medianoche": False},
    {"dia": "Viernes", "abre": "12:00", "cierra": "01:00", "cruza_medianoche": True},
    {"dia": "Sábado", "abre": "12:00", "cierra": "01:00", "cruza_medianoche": True},
    {"dia": "Domingo y festivos", "abre": "12:00", "cierra": "20:00", "cruza_medianoche": False},
]
# Igual, pero con el lunes abierto hasta las 23:59 (como en las pruebas del 19 de octubre).
LUNES_ABIERTO = [{"dia": "Lunes", "abre": "12:00", "cierra": "23:59", "cruza_medianoche": False}] + HORARIOS[1:]


def a(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=ZONA)


class PruebasEstado(unittest.TestCase):
    def comprobar(self, horarios, cuando, esperado, contiene=""):
        r = estado(horarios, a(cuando))
        self.assertEqual(r["estado"], esperado, r)
        self.assertIn(contiene, r["mensaje"])

    # 2026-10-19 es lunes; 20 martes; 23 viernes; 24 sábado; 25 domingo.
    def test_lunes_2310_con_lunes_abierto_recibe_domicilios(self):
        self.comprobar(LUNES_ABIERTO, "2026-10-19T23:10", "ABIERTO_DOMICILIO", "hasta las 11:29 p. m.")

    def test_lunes_2340_solo_recoger(self):
        self.comprobar(LUNES_ABIERTO, "2026-10-19T23:40", "SOLO_RECOGER", "11:29 p. m.")

    def test_lunes_cerrado_abre_manana(self):
        self.comprobar(HORARIOS, "2026-10-19T23:10", "CERRADO", "Mañana abrimos a las 12:00 m.")

    def test_martes_0017_cerrado_abre_hoy(self):
        self.comprobar(HORARIOS, "2026-10-20T00:17", "CERRADO", "Hoy abrimos a las 12:00 m.")

    def test_martes_1159_cerrado_y_1200_abierto(self):
        self.comprobar(HORARIOS, "2026-10-20T11:59", "CERRADO", "Hoy abrimos")
        self.comprobar(HORARIOS, "2026-10-20T12:00", "ABIERTO_DOMICILIO")

    def test_martes_2129_domicilio_y_2130_solo_recoger(self):
        self.comprobar(HORARIOS, "2026-10-20T21:29", "ABIERTO_DOMICILIO", "9:30 p. m.")
        self.comprobar(HORARIOS, "2026-10-20T21:30", "SOLO_RECOGER")

    def test_martes_2200_cerrado_abre_el_miercoles(self):
        self.comprobar(HORARIOS, "2026-10-20T22:00", "CERRADO", "Mañana abrimos")

    def test_sabado_madrugada_cierre_a_la_1am(self):
        # Madrugada del sábado = turno del viernes (cierra 01:00, corte 00:30).
        self.comprobar(HORARIOS, "2026-10-24T00:29", "ABIERTO_DOMICILIO", "12:30 a. m.")
        self.comprobar(HORARIOS, "2026-10-24T00:30", "SOLO_RECOGER", "1:00 a. m.")
        self.comprobar(HORARIOS, "2026-10-24T01:00", "CERRADO", "Hoy abrimos")

    def test_domingo_madrugada_usa_el_turno_del_sabado(self):
        self.comprobar(HORARIOS, "2026-10-25T00:40", "SOLO_RECOGER")

    def test_domingo_cierre_y_proxima_apertura_el_martes(self):
        self.comprobar(HORARIOS, "2026-10-25T20:00", "CERRADO", "El martes abrimos a las 12:00 m.")

    def test_corte_configurable(self):
        r = estado(HORARIOS, a("2026-10-20T21:10"), corte_minutos=60)
        self.assertEqual(r["estado"], "SOLO_RECOGER")

    def test_acepta_filas_con_data_y_texto_json(self):
        import json
        filas = [{"data": f} for f in HORARIOS]
        self.assertEqual(estado(json.dumps(filas), a("2026-10-20T13:00"))["estado"], "ABIERTO_DOMICILIO")

    def test_formato_de_horas(self):
        self.assertEqual(hora_texto(720), "12:00 m.")
        self.assertEqual(hora_texto(1409), "11:29 p. m.")
        self.assertEqual(hora_texto(1500), "1:00 a. m.")
        self.assertEqual(hora_texto(1470), "12:30 a. m.")

    def test_datos_invalidos(self):
        with self.assertRaises(ValueError):
            estado([], a("2026-10-20T13:00"))
        with self.assertRaises(ValueError):
            estado([{"dia": "Octubre", "cerrado": True}], a("2026-10-20T13:00"))


if __name__ == "__main__":
    unittest.main()
