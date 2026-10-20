# donde-tono-estado-local

Función HTTP para el agente de WhatsApp de **Donde Toño** (prueba técnica de Meteor). Responde una sola pregunta, con código y no con el modelo de IA:

> ¿Está abierto el local? ¿Todavía se reciben domicilios? Si está cerrado, ¿cuándo abre?

## Por qué existe

El agente de IA calculaba las horas "de cabeza" (pasar el cierre a minutos, restar 30 de corte, sumar un día si cierra de madrugada). A veces se equivocaba y mostraba el cálculo al cliente. Aquí las cuentas las hace código: siempre da el mismo resultado y se prueba con casos.

## Cómo funciona

- **Una sola fuente de verdad:** los horarios **no están escritos en el código**. El agente los lee de la tabla *Horarios* de Meteor y los envía en cada llamada. Si alguien cambia un horario en la tabla, la respuesta cambia sola.
- **Zona horaria:** `America/Bogota`.
- **Cierres de madrugada:** soporta turnos que terminan después de medianoche (viernes y sábado cierran a la 1:00 a. m.).
- **Corte de domicilios:** por defecto 30 minutos antes del cierre (`corte_minutos`).

### Petición

```
POST /
Authorization: Bearer <MET_TOKEN>
Content-Type: application/json

{
  "horarios": [
    {"dia": "Lunes", "cerrado": true},
    {"dia": "Martes", "abre": "12:00", "cierra": "22:00", "cruza_medianoche": false},
    {"dia": "Viernes", "abre": "12:00", "cierra": "01:00", "cruza_medianoche": true}
  ],
  "corte_minutos": 30,
  "ahora": "2026-10-20T21:45:00"
}
```

`corte_minutos` y `ahora` son opcionales. `ahora` permite probar a cualquier hora; si se omite, se usa la hora actual de Bogotá. `horarios` acepta una lista, un texto JSON, o filas de Meteor con la forma `{"data": {...}}`.

### Respuesta

```json
{"result": "SOLO_RECOGER: Solo para recoger: los domicilios cerraron a las 9:30 p. m.; el local cierra a las 10:00 p. m."}
```

El texto empieza por el estado: `ABIERTO_DOMICILIO`, `SOLO_RECOGER` o `CERRADO`.

| Código | Cuándo |
|---|---|
| 200 | Respuesta correcta |
| 400 | Datos inválidos (horarios vacíos, día desconocido, fecha mal escrita) |
| 401 | Falta el token o es incorrecto |

`GET /salud` responde `{"ok": true}` sin autenticación, para comprobar que el servicio está vivo o mantenerlo despierto.

## Probarlo en local

```bash
python3 -m unittest -v          # 19 pruebas (lógica y servidor)
MET_TOKEN=un-secreto python3 servidor.py
```

No tiene dependencias externas (solo la biblioteca estándar de Python 3.9 o superior; `tzdata` solo se necesita en sistemas sin base de zonas horarias).

## Desplegar en Render

El archivo `render.yaml` describe el servicio. Pasos:

1. Crear un *Blueprint* (o un *Web Service*) en Render apuntando a este repositorio.
2. Definir la variable de entorno secreta **`MET_TOKEN`** en Render. No se guarda en el repositorio.
3. Probar `https://<tu-servicio>.onrender.com/salud`.
4. En Meteor, crear una Función IA con esa URL, método `POST` y el mismo secreto como variable del workspace.

> **Plan gratis de Render:** el servicio se pausa tras 15 minutos sin tráfico y tarda alrededor de un minuto en despertar, más de lo que Meteor espera por una función (30 a 60 s). La primera llamada tras una pausa puede fallar por tiempo. El agente debe tener un plan de respaldo, o se puede mantener despierto con llamadas periódicas a `/salud`.

## Seguridad

- El token se compara en tiempo constante y nunca se imprime en los registros.
- Meteor también envía una firma `X-Met-Signature`; este servidor **todavía no la verifica** (solo valida el token). Es una mejora pendiente.
- No guarda datos ni llama a otros servicios.

## Limitaciones

- No conoce los **festivos**: depende de lo que diga la tabla de horarios.
- Solo decide la disponibilidad de domicilios; no calcula totales de pedidos.
