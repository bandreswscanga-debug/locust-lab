# Informe de Rendimiento — Implantación Flask + Gunicorn + Nginx

> Plantilla base (Persona 1). Las filas se completan tras cada fase con datos de Locust + `docker stats`.

## 1. Configuración por fase

| Fase | Servidor | Réplicas | Límites por réplica | Usuarios Locust | Spawn rate | Host |
|------|----------|----------|----------------------|-----------------|------------|------|
| 1 | Flask dev (`python app.py`) | 1 | 0.20 CPU / 128M | 50 | 5 | http://localhost:5000 |
| 2 | Gunicorn `-w 4` | 1 | 0.20 CPU / 128M | 50 | 5 | http://localhost:5000 |
| 3 | Gunicorn `-w 4` + Nginx | 3 | 0.20 CPU / 128M c/u (0.60 total) | 150 | 10 | http://localhost |

## 2. Tabla comparativa de resultados

| Métrica | Fase 1: Flask uniproceso | Fase 2: Gunicorn x4 | Fase 3: Nginx + 3 réplicas + chaos |
|---------|--------------------------|---------------------|-------------------------------------|
| Seg. hasta saturar 20% CPU | _pendiente_ | _pendiente_ | N/A |
| RPS promedio | _pendiente_ | _pendiente_ | _pendiente_ |
| P95 (ms) | _pendiente_ | _pendiente_ | _pendiente_ |
| Primer error (tiempo / tipo) | _pendiente_ | _pendiente_ | _pendiente_ |
| % errores | _pendiente_ | _pendiente_ | _pendiente_ |
| 500/502 en caída réplica | N/A | N/A | _pendiente_ |
| Observaciones | _pendiente_ | _pendiente_ | _pendiente_ |

Comandos Locust usados:
```bash
# Fases 1 y 2 (mismos parámetros para comparar):
locust -f locustfile.py --host http://localhost:5000 --headless -u 50 -r 5 -t 3m --csv fase1
# Fase 3:
locust -f locustfile.py --host http://localhost --headless -u 150 -r 10 -t 5m --csv fase3
# Chaos (cuando la gráfica está estable):
docker stop <id_replica>
```

## 3. Evidencias

- `docs/implantacion/fase1-locust.png` — _pendiente Persona 1_
- `docs/implantacion/fase2-locust.png` — _pendiente Persona 2_
- `docs/implantacion/fase3-chaos.png` — _pendiente Persona 3 (caída de réplica)_

![Fase 3 chaos](fase3-chaos.png)

## 4. Análisis técnico (máx. 2 párrafos)

_pendiente — completar en Bloque 4 con: concurrencia multiproceso vs un solo proceso, round-robin de Nginx, aislamiento de fallos y suma de recursos 0.60 CPU total en Fase 3._

## 5. Archivos finales

- `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `locustfile.py` en la raíz del repo.
- Locust apunta a endpoints que existen en `app.py`: `GET /api/health`, `GET /api/products`, `POST /api/products`, `POST /api/orders`.
