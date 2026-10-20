"""Decide si Donde Toño está abierto y si todavía recibe domicilios.

Toda la lógica de horas vive aquí, en código, y no en el modelo de IA.
Los horarios no están escritos en este archivo: llegan en cada llamada,
tal como están en la tabla de Meteor (una sola fuente de verdad).
"""
import json
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Bogota")
DIA = 1440  # minutos en un día
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _sin_tildes(texto):
    descompuesto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").strip()


def _a_minutos(hhmm):
    horas, minutos = str(hhmm).strip().split(":")[:2]
    return int(horas) * 60 + int(minutos)


def _a_bool(valor):
    return str(valor).strip().lower() in ("true", "1", "si", "sí", "yes")


def hora_texto(minutos):
    """Minutos desde las 00:00 -> '11:29 p. m.' (el mediodía se escribe '12:00 m.')."""
    horas, mins = divmod(minutos % DIA, 60)
    if horas == 12 and mins == 0:
        return "12:00 m."
    sufijo = "a. m." if horas < 12 else "p. m."
    return f"{horas % 12 or 12}:{mins:02d} {sufijo}"


def leer_horarios(horarios):
    """Convierte la tabla de Horarios en {día(0=lunes): (abre, cierra) | None}.

    `cierra` pasa de 1440 cuando el local cierra después de medianoche.
    """
    filas = json.loads(horarios) if isinstance(horarios, str) else horarios
    if not isinstance(filas, list) or not filas:
        raise ValueError("horarios debe ser una lista con una fila por día")
    semana = {}
    for fila in filas:
        datos = fila.get("data", fila)
        nombre = _sin_tildes(datos["dia"])
        indice = next((i for i, d in enumerate(DIAS) if nombre.startswith(d)), None)
        if indice is None:
            raise ValueError(f"día no reconocido: {datos['dia']}")
        if _a_bool(datos.get("cerrado")):
            semana[indice] = None
            continue
        abre, cierra = _a_minutos(datos["abre"]), _a_minutos(datos["cierra"])
        if _a_bool(datos.get("cruza_medianoche")) or cierra <= abre:
            cierra += DIA
        semana[indice] = (abre, cierra)
    return semana


def estado(horarios, ahora=None, corte_minutos=30):
    """Devuelve {'estado': ..., 'mensaje': ...}.

    estado: ABIERTO_DOMICILIO | SOLO_RECOGER | CERRADO
    """
    ahora = ahora or datetime.now(ZONA)
    ahora = ahora.replace(tzinfo=ZONA) if ahora.tzinfo is None else ahora.astimezone(ZONA)
    semana = leer_horarios(horarios)
    dia, minuto = ahora.weekday(), ahora.hour * 60 + ahora.minute

    # Hoy, y la madrugada del turno de ayer si cerró después de medianoche.
    for d, t in ((dia, minuto), ((dia - 1) % 7, minuto + DIA)):
        turno = semana.get(d)
        if turno and turno[0] <= t < turno[1]:
            cierre = turno[1]
            corte = cierre - corte_minutos
            if t < corte:
                return {
                    "estado": "ABIERTO_DOMICILIO",
                    "mensaje": f"Abierto. Se reciben domicilios hasta las {hora_texto(corte)}; "
                               f"el local cierra a las {hora_texto(cierre)}.",
                }
            return {
                "estado": "SOLO_RECOGER",
                "mensaje": f"Solo para recoger: los domicilios cerraron a las {hora_texto(corte)}; "
                           f"el local cierra a las {hora_texto(cierre)}.",
            }

    # Cerrado: buscar la próxima apertura.
    for k in range(8):
        d = (dia + k) % 7
        turno = semana.get(d)
        if not turno or (k == 0 and turno[0] <= minuto):
            continue
        cuando = "Hoy" if k == 0 else "Mañana" if k == 1 else f"El {NOMBRES[d]}"
        return {"estado": "CERRADO", "mensaje": f"Cerrado. {cuando} abrimos a las {hora_texto(turno[0])}."}
    return {"estado": "CERRADO", "mensaje": "Cerrado. No hay un horario de apertura configurado."}
