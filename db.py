import os
import pandas as pd
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Leer el archivo .env
load_dotenv()


def conexion_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("La variable de entorno DATABASE_URL no está definida.")
    # 2. Cambiar el prefijo para que SQLAlchemy use el driver psycopg
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


# 3. Crear la conexión a la base de datos
engine = create_engine(conexion_url(), pool_pre_ping=True)

# 4. Si no están llegando logs nuevos, se toma el último ts como "ahora"
HISTORICO = os.getenv("MODO_HISTORICO", "0") == "1"


def hora_fin(conn):
    if HISTORICO:
        return conn.execute(text("SELECT max(ts) FROM logs")).scalar()
    return conn.execute(text("SELECT now()")).scalar()


# 5. Indicadores de las tarjetas del tablero
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


# 6. Lista de servicios para el selector
def servicios():
    with engine.connect() as conn:
        filas = conn.execute(text("SELECT DISTINCT svc FROM logs ORDER BY svc")).all()
    return [fila[0] for fila in filas]


# 7. Minutos que agrupa cada punto de las gráficas según la ventana
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

    # los minutos sin peticiones no vienen en la consulta, se agregan en cero
    todos = pd.date_range(inicio, fin, freq=paso)
    df = df.set_index("momento").reindex(todos)
    df[["total", "errores_4xx", "errores_5xx"]] = df[["total", "errores_4xx", "errores_5xx"]].fillna(0)
    df["rpm"] = df["total"] / PASOS[horas]
    df.index = df.index.tz_convert("America/Bogota")
    return df


# 8. Prueba: este bloque solo corre con "uv run python db.py"
if __name__ == "__main__":
    print("Modo histórico:", HISTORICO)
    print(resumen("checkout", 24))
    df = series_tiempo("Todos", 1)
    print(f"\nSeries de la última hora: {len(df)} puntos")
    print(df.head(10))