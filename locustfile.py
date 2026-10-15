"""Paso 1: 2 usuarios simulados (proyecto tienda-lab, NO SmartRoad).
Usuario Navegador: solo GET (trafico ligero).
Usuario Comprador: POST con payload (trafico pesado que consulta y escribe en MySQL).

Uso: locust -f locustfile.py --host http://localhost:5000  -> http://localhost:8089
Fase 1 (SLA): 50 usuarios, subida 2/s
Fase 2 (Estres): 500 usuarios, subida 20/s
"""
import random
from locust import HttpUser, between, task


class UsuarioNavegador(HttpUser):
    """Trafico ligero: solo peticiones GET."""

    weight = 1
    wait_time = between(1, 3)

    @task(3)
    def salud(self):
        self.client.get("/api/health", name="Consultar salud")

    @task(1)
    def productos(self):
        self.client.get("/api/products", name="Listar productos")


class UsuarioComprador(HttpUser):
    """Trafico pesado: POST que consultan y escriben en MySQL."""

    weight = 1
    wait_time = between(0.5, 1.5)

    @task(2)
    def crear_producto(self):
        self.client.post(
            "/api/products",
            name="Crear producto",
            json={"nombre": f"prod-{random.randint(1, 99999)}", "precio": round(random.uniform(5, 200), 2)},
        )

    @task(3)
    def crear_orden(self):
        self.client.post(
            "/api/orders",
            name="Crear pedido",
            json={"product_id": random.randint(1, 100), "cantidad": random.randint(1, 5)},
        )
