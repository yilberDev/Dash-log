# Dashboard de monitoreo de servicios

Este proyecto es el trabajo final de Analítica de Datos. Es una aplicación hecha en Dash que consulta la tabla `logs` de PostgreSQL y muestra cómo se están comportando los servicios. Los datos se actualizan solos cada pocos segundos.

## Qué muestra

En la parte superior hay seis tarjetas con los indicadores de la ventana elegida:

- Tiempo de respuesta promedio, p95 y p99, calculados con la columna `duration` (en milisegundos).
- Throughput, medido en peticiones por minuto (RPM).
- Errores 4xx, que son fallos del cliente, y errores 5xx, que son fallos del servidor.

Debajo hay tres gráficas con esas mismas métricas a lo largo del tiempo: una de tiempo de respuesta, una de throughput y una de errores.

El tablero tiene tres selectores. El primero filtra por servicio (columna `svc`) y trae la opción "Todos". El segundo define la ventana de tiempo: 1 hora, 3 horas o 24 horas. El tercero indica cada cuánto se actualiza la página, cada 10 o cada 60 segundos.

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Acceso a la base de datos PostgreSQL que contiene la tabla `logs`.

## Cómo ejecutarlo

1. Clonar el repositorio y entrar a la carpeta:

   ```bash
   git clone https://github.com/yilberDev/Dash-log.git
   cd Dash-log
   ```

2. Instalar las dependencias:

   ```bash
   uv sync
   ```

3. Crear el archivo `.env` copiando el de ejemplo:

   ```bash
   cp .env.example .env
   ```

   Después se abre `.env` y se escribe la cadena de conexión real:

   ```
   DATABASE_URL=postgresql://usuario:contraseña@host:5432/base_de_datos
   MODO_HISTORICO=0
   ```

4. Correr la aplicación:

   ```bash
   uv run python app.py
   ```

5. Abrir http://127.0.0.1:8050 en el navegador.

### Sobre MODO_HISTORICO

Con `MODO_HISTORICO=0` las ventanas se cuentan hacia atrás desde la hora actual. Es el modo normal y sirve cuando los logs llegan en vivo.

Con `MODO_HISTORICO=1` las ventanas se cuentan desde el último registro que tiene la tabla. Esta opción se agregó porque durante el desarrollo hubo ratos en los que no llegaban logs nuevos y las ventanas de 1 y 3 horas quedaban vacías.

## Estructura del proyecto

```
Dash-log/
├── app.py          # la página de Dash: layout, callbacks y gráficas
├── db.py           # conexión a PostgreSQL y consultas de las métricas
├── .env.example    # plantilla de las variables de entorno
├── .gitignore      # deja por fuera .env y .venv
├── pyproject.toml  # dependencias del proyecto
└── uv.lock         # versiones exactas de las dependencias
```

## OLTP y OLAP

La tabla `logs` trabaja como un sistema OLTP. Cada petición que hace un usuario queda guardada como una fila nueva en el momento en que ocurre. El tablero necesita otra cosa: resumir miles de esas filas para entender qué está pasando, y ese tipo de trabajo corresponde a OLAP.

Por eso las métricas se calculan directamente en PostgreSQL con funciones de agregación como `count`, `avg`, `percentile_cont` y `FILTER`. A Python solo le llegan los resultados ya resumidos. Si se trajera la tabla completa en cada actualización, el tablero sería mucho más lento.

## Seguridad

La cadena de conexión tiene usuario y contraseña, así que no está escrita en el código. Se guarda en el archivo `.env`, que aparece en `.gitignore` y por lo tanto no se sube al repositorio.