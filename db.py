import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

#1. leer el archivo .env
load_dotenv()

def conexion_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("La variable de entorno DATABASE_URL no está definida.")
    #2. verificar si la url contiene "postgresql://"
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url

#3 Crear la conexión a la base de datos
engine = create_engine(conexion_url(), pool_pre_ping=True)

#4. Prueba: el archicvo solo correra cuando se ejecute con el comando "uv run python db.py"
if __name__ == "__main__":
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT count(*), min(ts), max(ts), now() FROM logs;
        """)).one()
        print("Total de filas en la tabla logs:", resultado[0])
        print("Fecha mínima en la tabla logs:", resultado[1])
        print("Fecha máxima en la tabla logs:", resultado[2])
        print("Fecha actual:", resultado[3])

        servicios = conn.execute(text("SELECT DISTINCT svc FROM logs ORDER BY svc")).all()
        print("Servicios:", [servicio[0] for servicio in servicios])

        print("\nÚltimos 5 registros de la tabla logs:")
        filas = conn.execute(text("""
            SELECT ts, svc, http_method, url, status_code, duration, log" \
        " FROM logs ORDER BY ts DESC LIMIT 5""")).all()
        for fila in filas:
            print(fila)
    