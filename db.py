import os
import pandas as pd
from datetime import timedelta

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

#4. Si no estan llegando logs nuevos, se toma el último ts como "ahora" y se insertan logs falsos para pruebas. Esto es solo para pruebas, no se debe usar en producción.
HISTORICO = os.getenv("MODO_HISTORICO", "0") == "1"
def hora_fin(conn):
    if HISTORICO:
        return conn.execute(text("SELECT max(ts) FROM logs")).scalar()
    return conn.execute(text("SELECT now()")).scalar()

# 4. Consultar los insertados logs de prueba (tarjetas del tablero)
def resumen(svc, horas):
    consulta = """
        SELECT count(*) AS total,
               avg(duration)::float AS promedio,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY duration) AS p95,
               percentile_cont(0.99) WITHIN GROUP (ORDER BY duration) AS p99,
               count(*) FILTER (WHERE status_code BETWEEN 400 AND 499) AS errores_4xx,
               count(*) FILTER (WHERE status_code >= 500) AS errores_5xx
        FROM logs
        WHERE ts > :inicio AND ts <= :fin
    """
    if svc != "Todos":
        consulta += " AND svc = :svc"

    with engine.connect() as conn:
        fin = hora_fin(conn)
        inicio = fin - timedelta(hours=horas)
        fila = conn.execute(text(consulta), {"inicio": inicio, "fin": fin, "svc": svc}).mappings().one()

    datos = dict(fila)
    datos["rpm"] = datos["total"] / (horas * 60)
    return datos

#5. minutos que se agrupan los logs para el gráfico de series de tiempo
PASOS = {1: 1, 3: 5, 24: 30}
def series_tiempo(svc, horas):
    paso = timedelta(minutes=PASOS[horas])
    consulta = """
        SELECT date_bin(:paso, ts, :inicio) AS momento,
               count(*) AS total,
               avg(duration)::float AS promedio,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY duration) AS p95,
               percentile_cont(0.99) WITHIN GROUP (ORDER BY duration) AS p99,
               count(*) FILTER (WHERE status_code BETWEEN 400 AND 499) AS errores_4xx,
               count(*) FILTER (WHERE status_code >= 500) AS errores_5xx
        FROM logs
        WHERE ts > :inicio AND ts <= :fin
    """
    if svc != "Todos":
        consulta += " AND svc = :svc"
    consulta += " GROUP BY momento ORDER BY momento"

    with engine.connect() as conn:
        fin = hora_fin(conn)
        inicio = fin - timedelta(hours=horas)
        df = pd.read_sql(text(consulta), conn,
                         params={"paso": paso, "inicio": inicio, "fin": fin, "svc": svc})
    # los minutos sin peticiones no vienen an la consulta, se agregan con 0s
    todos = pd.date_range(inicio, fin, freq=paso)
    df = df.set_index("momento").reindex(todos)
    df[["total", "errores_4xx", "errores_5xx"]] = df[["total", "errores_4xx", "errores_5xx"]].fillna(0)
    df["rpm"] = df["total"] / PASOS[horas]
    df.index = df.index.tz_convert("America/Bogota")
    return df

#6. Prueba: el archicvo solo correra cuando se ejecute con el comando "uv run python db.py"
if __name__ == "__main__":
    print("Modo histórico:", HISTORICO)
    print(resumen("checkout", 24))
    df = series_tiempo("Todos", 1)
    print(f"\nSeries de la última hora: {len(df)} puntos")
    print(df.head(10))