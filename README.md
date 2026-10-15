# Tienda Lab — Flask + MySQL + Locust (proyecto nuevo, NO SmartRoad)

## Paso 1: Instalación y Configuración (local)
```bash
cd ~/flask-locust-lab
pip install -r requirements.txt   # = pip install locust
python app.py                     # API en http://localhost:5000
```
`locustfile.py` trae los 2 usuarios:
- `UsuarioNavegador`: solo `GET /api/health`, `GET /api/products` (ligero).
- `UsuarioComprador`: `POST /api/products`, `POST /api/orders` con JSON (pesado: SELECT + INSERT en MySQL).
- Sin MySQL instalado la API hace fallback a memoria y lo deja en `logs/api.log`
  (`[DB] Sin MySQL... Fallback en memoria`). Con `docker compose up` usa MySQL real.

## Paso 2: Ejecución y Monitoreo Paralelo (2 terminales)
Terminal 1 (Ataque):
```bash
cd ~/flask-locust-lab
locust -f locustfile.py --host http://localhost:5000
# panel: http://localhost:8089
# Fase 1 Carga SLA: 50 users, spawn 2/s
# Fase 2 Estres Extremo: 500 users, spawn 20/s
```
Terminal 2 (Observabilidad = logs, no docker):
```bash
cd ~/flask-locust-lab
tail -f logs/api.log
# o en navegador: http://localhost:5000/api/logs
# veras: "GET /api/... -> 200 7ms", "POST ... -> 201", "[500]..." y "SLOW>300ms"
```
Con Docker (opcional, para pregunta 3 real MySQL vs Flask):
```bash
docker compose up --build   # levanta lab-mysql + lab-flask + dozzle :9999
```

## Paso 3: Responde con gráficas
1. RPS con 500/504: `Locust > Charts > Total Requests per Second` vs `Failures/s` + pestaña `Failures`.
2. P95 >300ms: `Charts > Response Times (percentiles)` curva p95.
3. Qué se saturó: `logs/api.log` (`[DB]...`, `[500]`, `SLOW>300ms`) + `http://localhost:5000/api/logs`.
   Sin Docker el cuello es Flask (dev server). Con Docker: si el log se llena de
   errores de pool/conexión = MySQL; si CPU 100% sin errores DB = Flask.
