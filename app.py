"""Tienda Lab - API Flask + MySQL (con fallback en memoria para correr sin Docker).
Paso 1: GET ligero (Navegador) vs POST pesado (Comprador que consulta y escribe).
Paso 2: observabilidad por LOGS (ver logs/api.log).
"""
import logging
import os
import time
from flask import Flask, jsonify, request, g

app = Flask(__name__)

# ---------- Logs (Paso 2: Terminal 2) ----------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/api.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("tienda-lab")

# ---------- Estado en memoria (fallback si no hay MySQL) ----------
MEM = {
    "motor": "memory",
    "products": [
        {"id": 1, "nombre": "mouse", "precio": 25.00},
        {"id": 2, "nombre": "teclado", "precio": 45.00},
        {"id": 3, "nombre": "monitor", "precio": 150.00},
    ],
    "orders": [],
    "seq_p": 3,
    "seq_o": 0,
}

# ---------- MySQL (perezoso: si no hay servidor, se usa memoria y se LOGUEA) ----------
_pool = None
_pool_error = None

def get_pool():
    global _pool, _pool_error
    if _pool is not None:
        return _pool
    if _pool_error is not None:
        raise _pool_error
    try:
        import mysql.connector
        from mysql.connector import pooling
        _pool = pooling.MySQLConnectionPool(
            pool_name="lab_pool",
            pool_size=int(os.getenv("MYSQL_POOL_SIZE", "10")),  # cuello de botella Fase 2
            pool_reset_session=True,
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "lab1234"),
            database=os.getenv("MYSQL_DATABASE", "tienda"),
            connection_timeout=5,
        )
        # prueba real de conexión
        c = _pool.get_connection()
        c.close()
        MEM["motor"] = "mysql"
        log.info("[DB] Conectado a MySQL. Modo persistente.")
        return _pool
    except Exception as e:  # noqa: BLE001 - queremos loguear cualquier fallo y seguir en memoria
        _pool_error = e
        MEM["motor"] = "memory"
        log.warning("[DB] Sin MySQL (%s). Fallback en memoria para la actividad.", str(e)[:200])
        raise


def use_mysql():
    try:
        get_pool()
        return MEM["motor"] == "mysql"
    except Exception:
        return False


# ---------- Middleware de tiempos + log por request ----------
@app.before_request
def _t0():
    g.t0 = time.time()


@app.after_request
def _t1(resp):
    dt_ms = int((time.time() - g.get("t0", time.time())) * 1000)
    slow = " SLOW>300ms" if dt_ms > 300 else ""
    log.info("%s %s -> %s %dms%s", request.method, request.path, resp.status_code, dt_ms, slow)
    return resp


# ---------- Endpoints ----------
@app.get("/api/health")
def health():
    motor = "mysql" if use_mysql() else "memory"
    return jsonify({"ok": True, "servicio": "tienda-lab", "motor": motor}), 200


@app.get("/api/products")
def list_products():
    """GET ligero: 1 SELECT (o lectura en memoria)."""
    if use_mysql():
        conn = get_pool().get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, nombre, precio FROM products ORDER BY id DESC LIMIT 50")
            rows = cur.fetchall()
            # mysql decimal -> float para JSON
            for r in rows:
                r["precio"] = float(r["precio"])
            return jsonify(rows), 200
        finally:
            conn.close()
    return jsonify(sorted(MEM["products"], key=lambda x: x["id"], reverse=True)[:50]), 200


@app.post("/api/products")
def create_product():
    """POST pesado: INSERT (escritura)."""
    data = request.get_json(force=True, silent=True) or {}
    nombre = str(data.get("nombre", "prod-locust"))[:100]
    try:
        precio = float(data.get("precio", 9.99))
    except (TypeError, ValueError):
        return jsonify({"error": "precio invalido"}), 400
    if use_mysql():
        conn = get_pool().get_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO products (nombre, precio) VALUES (%s, %s)", (nombre, precio))
            conn.commit()
            log.info("[DB] INSERT product id=%s", cur.lastrowid)
            return jsonify({"ok": True, "id": cur.lastrowid}), 201
        finally:
            conn.close()
    MEM["seq_p"] += 1
    MEM["products"].append({"id": MEM["seq_p"], "nombre": nombre, "precio": precio})
    return jsonify({"ok": True, "id": MEM["seq_p"]}), 201


@app.post("/api/orders")
def create_order():
    """POST mas pesado: SELECT + INSERT (consulta y escribe)."""
    data = request.get_json(force=True, silent=True) or {}
    try:
        product_id = int(data.get("product_id", 1))
        cantidad = int(data.get("cantidad", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "payload invalido"}), 400
    if use_mysql():
        conn = get_pool().get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, precio FROM products WHERE id = %s", (product_id,))
            prod = cur.fetchone()
            if not prod:
                cur2 = conn.cursor()
                cur2.execute("INSERT INTO products (nombre, precio) VALUES (%s, %s)", ("auto-locust", 10.0))
                product_id = cur2.lastrowid
                total = 10.0 * cantidad
            else:
                total = float(prod["precio"]) * cantidad
            cur3 = conn.cursor()
            cur3.execute(
                "INSERT INTO orders (product_id, cantidad, total) VALUES (%s, %s, %s)",
                (product_id, cantidad, total),
            )
            conn.commit()
            return jsonify({"ok": True, "order_id": cur3.lastrowid, "total": total}), 201
        finally:
            conn.close()
    prod = next((p for p in MEM["products"] if p["id"] == product_id), None)
    if prod is None:
        MEM["seq_p"] += 1
        prod = {"id": MEM["seq_p"], "nombre": "auto-locust", "precio": 10.0}
        MEM["products"].append(prod)
        product_id = prod["id"]
    total = float(prod["precio"]) * cantidad
    MEM["seq_o"] += 1
    MEM["orders"].append({"id": MEM["seq_o"], "product_id": product_id, "cantidad": cantidad, "total": total})
    return jsonify({"ok": True, "order_id": MEM["seq_o"], "total": total}), 201


@app.get("/api/logs")
def ver_logs():
    """Para la captura de observabilidad sin abrir archivos."""
    try:
        with open("logs/api.log", encoding="utf-8") as f:
            lineas = f.readlines()[-100:]
        return jsonify({"total": len(lineas), "logs": lineas}), 200
    except FileNotFoundError:
        return jsonify({"total": 0, "logs": []}), 200


@app.errorhandler(Exception)
def handle_500(e):  # noqa: ANN001
    log.exception("[500] %s %s fallo: %s", request.method, request.path, str(e)[:300])
    return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    log.info("[API] Tienda Lab lista en http://localhost:5000 (logs/api.log)")
    app.run(host="0.0.0.0", port=5000, threaded=True)
