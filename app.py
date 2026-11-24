from datetime import datetime
from dash import Dash, html, dcc, callback, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import db

# fuente del diseño (si no hay internet, el navegador usa la del sistema)
FUENTE = "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap"

app = Dash(title="Monitoreo de logs", external_stylesheets=[FUENTE])

op_servicios = ["Todos"] + db.servicios()

# colores del diseño, los mismos en tarjetas y gráficas
AZUL = "#1f77b4"
NARANJA = "#f59e0b"
ROJO = "#dc2626"
VERDE = "#16a34a"


def tarjeta(titulo, valor, ayuda, color):
    return html.Div([
        html.Div([html.Span(className="punto"), html.Span(titulo)], className="titulo"),
        html.P(valor, className="valor"),
        html.P(ayuda, className="ayuda"),
    ], className=f"tarjeta {color}")


def ms(valor):
    # si no hubo peticiones no hay tiempo que mostrar
    if valor is None:
        return "-"
    return f"{valor:.0f} ms"


def errores(cantidad, total):
    # cantidad y porcentaje sobre el total de peticiones
    if total == 0:
        return "0"
    return f"{cantidad} ({cantidad / total:.0%})"


# colores de las gráficas para cada tema
TEMAS = {
    "claro": {"fondo": "#ffffff", "texto": "#475569", "titulo": "#0f172a", "rejilla": "#e2e8f0"},
    "oscuro": {"fondo": "#1e293b", "texto": "#94a3b8", "titulo": "#f1f5f9", "rejilla": "#334155"},
}


def estilo(fig, tema):
    # mismo aspecto para las tres gráficas, con los colores del tema elegido
    c = TEMAS[tema]
    fig.update_layout(
        font_family="Instrument Sans, sans-serif",
        font_color=c["texto"],
        title_font=dict(size=16, color=c["titulo"]),
        title_x=0,
        margin=dict(l=50, r=20, t=80, b=40),
        legend=dict(orientation="h", x=1, xanchor="right", y=1.15, title_text=""),
        hovermode="x unified",
        plot_bgcolor=c["fondo"],
        paper_bgcolor=c["fondo"],
    )
    fig.update_xaxes(showgrid=False, title_text="", tickformat="%H:%M")
    fig.update_yaxes(gridcolor=c["rejilla"], zeroline=False)
    return fig


def figura_vacia(titulo, tema):
    fig = go.Figure()
    fig.add_annotation(text="Sin peticiones en esta ventana", showarrow=False,
                       font=dict(size=14))
    fig.update_layout(title=titulo, xaxis_visible=False, yaxis_visible=False)
    return estilo(fig, tema)


def tema_actual(clics):
    # cada clic cambia el tema: par = claro, impar = oscuro
    return "oscuro" if clics % 2 == 1 else "claro"


app.layout = html.Div(id="raiz", className="tema-claro", children=html.Div([
    html.Div([
        html.Div([
            html.H1("Monitoreo de servicios"),
            html.P("Tiempo de respuesta, tráfico y errores a partir de la tabla logs",
                   className="subtitulo"),
        ]),
        html.Div([
            html.Div(id="ultima-actualizacion", className="estado"),
            html.Button("🌙 Modo oscuro", id="boton-tema", n_clicks=0, className="boton-tema"),
        ], className="acciones"),
    ], className="encabezado"),

    html.Div([
        html.Div([
            html.Span("Servicio", className="titulo-control"),
            dcc.Dropdown(op_servicios, value="Todos", id="servicio",
                         clearable=False, style={"width": "180px"},
                         className="selector"),
        ], className="control"),

        html.Div([
            html.Span("Ventana", className="titulo-control"),
            dcc.RadioItems(
                options=[
                    {"label": "1 hora", "value": 1},
                    {"label": "3 horas", "value": 3},
                    {"label": "24 horas", "value": 24},
                ],
                value=1, id="ventana",
                className="botones", labelClassName="boton",
            ),
        ], className="control"),

        html.Div([
            html.Span("Actualizar cada", className="titulo-control"),
            dcc.RadioItems(
                options=[
                    {"label": "10 s", "value": 10},
                    {"label": "60 s", "value": 60},
                ],
                value=10, id="refresco",
                className="botones", labelClassName="boton",
            ),
        ], className="control"),
    ], className="panel controles"),

    # reloj que dispara la actualización (el intervalo va en milisegundos)
    dcc.Interval(id="reloj", interval=10 * 1000),

    html.Div(id="tarjetas", className="tarjetas"),

    html.Div(dcc.Graph(id="grafico-tiempo", config={"displaylogo": False}),
             className="panel grafica"),

    html.Div([
        html.Div(dcc.Graph(id="grafica-rpm", config={"displaylogo": False}),
                 className="panel grafica"),
        html.Div(dcc.Graph(id="grafica-errores", config={"displaylogo": False}),
                 className="panel grafica"),
    ], className="fila-graficas"),
], className="contenedor"))


# cambia entre tema claro y oscuro
@callback(
    Output("raiz", "className"),
    Output("boton-tema", "children"),
    Input("boton-tema", "n_clicks"),
)
def cambiar_tema(clics):
    if tema_actual(clics) == "oscuro":
        return "tema-oscuro", "☀️ Modo claro"
    return "tema-claro", "🌙 Modo oscuro"


# cambia cada cuánto se actualiza el tablero
@callback(
    Output("reloj", "interval"),
    Input("refresco", "value"),
)
def cambiar_refresco(segundos):
    return segundos * 1000


# callback para tarjetas
@callback(
    Output("tarjetas", "children"),
    Output("ultima-actualizacion", "children"),
    Input("servicio", "value"),
    Input("ventana", "value"),
    Input("reloj", "n_intervals"),
)
def actualizar_tarjetas(svc, horas, n_intervals):
    r = db.resumen(svc, horas)
    total = r["total"]
    tarjetas = [
        tarjeta("Tiempo promedio", ms(r["promedio"]),
                "Promedio de todas las peticiones", "azul"),
        tarjeta("p95", ms(r["p95"]),
                "El 95 % respondió en este tiempo o menos", "naranja"),
        tarjeta("p99", ms(r["p99"]),
                "Solo el 1 % más lento tardó más", "rojo"),
        tarjeta("Throughput", f"{r['rpm']:.1f} RPM",
                f"{total} peticiones en la ventana", "verde"),
        tarjeta("Errores 4xx", errores(r["errores_4xx"], total),
                "Fallos del cliente (400 a 499)", "naranja"),
        tarjeta("Errores 5xx", errores(r["errores_5xx"], total),
                "Fallos del servidor (500 o más)", "rojo critica"),
    ]
    hora = datetime.now().strftime("%H:%M:%S")
    return tarjetas, f"Actualizado a las {hora}"


# callback para gráficas
@callback(
    Output("grafico-tiempo", "figure"),
    Output("grafica-rpm", "figure"),
    Output("grafica-errores", "figure"),
    Input("servicio", "value"),
    Input("ventana", "value"),
    Input("reloj", "n_intervals"),
    Input("boton-tema", "n_clicks"),
)
def actualizar_graficas(svc, horas, n_intervals, clics):
    tema = tema_actual(clics)
    df = db.series_tiempo(svc, horas)

    # si no hubo ninguna petición, se muestra un aviso en lugar de gráficas vacías
    if df["total"].sum() == 0:
        return (figura_vacia("Tiempo de respuesta", tema),
                figura_vacia("Throughput", tema),
                figura_vacia("Errores", tema))

    df = df.reset_index(names="hora")
    df = df.rename(columns={
        "promedio": "Promedio",
        "errores_4xx": "Cliente (4xx)",
        "errores_5xx": "Servidor (5xx)",
    })

    fig_tiempo = px.line(
        df, x="hora", y=["Promedio", "p95", "p99"],
        title="Tiempo de respuesta<br><sup>¿Qué tan rápido responden los servicios?</sup>",
        labels={"value": "Milisegundos", "variable": ""},
        color_discrete_sequence=[AZUL, NARANJA, ROJO],
    )
    fig_tiempo.update_traces(line_width=2, hovertemplate="%{y:.0f} ms")
    # línea de referencia de 1 segundo para ver de un vistazo los picos
    fig_tiempo.add_hline(y=1000, line_dash="dot", line_color="#94a3b8",
                         annotation_text="Referencia: 1 s",
                         annotation_position="top left")
    fig_tiempo.update_yaxes(rangemode="tozero")

    fig_rpm = px.area(
        df, x="hora", y="rpm",
        title="Throughput<br><sup>¿Cuántas peticiones llegan por minuto?</sup>",
        labels={"rpm": "RPM"},
        color_discrete_sequence=[VERDE],
    )
    fig_rpm.update_traces(line_width=2, hovertemplate="%{y:.1f} RPM")

    # el primero de la lista queda abajo: los 5xx, que son los más graves
    fig_errores = px.bar(
        df, x="hora", y=["Servidor (5xx)", "Cliente (4xx)"],
        title="Errores<br><sup>¿Cuántas peticiones fallaron y de quién fue la falla?</sup>",
        labels={"value": "Cantidad", "variable": ""},
        color_discrete_sequence=[ROJO, NARANJA],
    )
    fig_errores.update_traces(hovertemplate="%{y:.0f}")
    fig_errores.update_layout(bargap=0.25, barcornerradius=3)
    # con pocos errores, el eje va de 1 en 1 para no mostrar decimales
    maximo = (df["Servidor (5xx)"] + df["Cliente (4xx)"]).max()
    if maximo <= 10:
        fig_errores.update_yaxes(dtick=1)

    return estilo(fig_tiempo, tema), estilo(fig_rpm, tema), estilo(fig_errores, tema)


if __name__ == "__main__":
    app.run(debug=True)