from datetime import datetime
from dash import Dash, html, dcc, callback, Input, Output
import plotly.express as px
import db

app = Dash(title="Monitoreo de logs")

op_servicios = ["Todos"] + db.servicios()


def tarjeta(titulo, valor):
    return html.Div([
        html.P(titulo, style={"margin": "0px", "color": "gray"}),
        html.H2(valor, style={"margin": 0})

    ], style={"border": "1px solid #ddd", "border-radius": "8px",
              "padding": "10px", "flex": 1, "text-align": "center"})


def ms(valor):
    # si no hubo peticiones, el promedio es None, se muestra 0
    if valor is None:
        return "0 ms"
    return f"{valor:.0f} ms"

app.layout = html.Div([
    html.H1("Monitoreo de servicios"),

    html.Div([
        html.Div([
            html.Label("Servicio:"),
            dcc.Dropdown(op_servicios, value="Todos", id="servicio", clearable=False),
        ], style={"width": "200px"}),

        html.Div([
            html.Label("Ventana de tiempo:"),
            dcc.RadioItems(
                options=[
                    {"label": "1 hora", "value": 1},
                    {"label": "3 horas", "value": 3},
                    {"label": "24 horas", "value": 24},
                ],
                value=1, id="ventana", inline=True,
            ),
        ]),

        html.Div([
            html.Label("Actualizar cada:"),
            dcc.RadioItems(
                options=[
                    {"label": "10 segundos", "value": 10},
                    {"label": "60 segundos", "value": 60},
                ],
                value=10, id="refresco", inline=True,
            ),
        ]),

        html.Div(id="ultima-actualizacion", style={"color": "gray", "align-self": "flex-end"}),
    ], style={"display": "flex", "gap": "40px"}),

    # reloj que dispara la actualización (el intervalo va en milisegundos)
    dcc.Interval(id="reloj", interval=10 * 1000),

    html.Hr(),

    html.Div(id="tarjetas", style={"display": "flex", "gap": "10px"}),

    dcc.Graph(id="grafico-tiempo"),

    html.Div([
        dcc.Graph(id="grafica-rpm", style={"flex": 1}),
        dcc.Graph(id="grafica-errores", style={"flex": 1}),
    ], style={"display": "flex", "gap": "10px", "margin-top": "20px"}),
], style={"padding": "20px", "font-family": "Arial"})


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
    Input("servicio", "value"),
    Input("ventana", "value"),
)
def actualizar_tarjetas(svc, horas):
    r = db.resumen(svc, horas)
    return [
        tarjeta("Tiempo de respuesta promedio", ms(r["promedio"])),
        tarjeta("p95", ms(r["p95"])),
        tarjeta("p99", ms(r["p99"])),
        tarjeta("Throughput", f"{r['rpm']:.1f} RPM"),
        tarjeta("Errores 4xx", r["errores_4xx"]),
        tarjeta("Errores 5xx", r["errores_5xx"]),
    ]


# callback para gráficas
@callback(
    Output("grafico-tiempo", "figure"),
    Output("grafica-rpm", "figure"),
    Output("grafica-errores", "figure"),
    Input("servicio", "value"),
    Input("ventana", "value"),
)
def actualizar_graficas(svc, horas):
    df = db.series_tiempo(svc, horas)
    df = df.reset_index(names="hora")
    df = df.rename(columns={
        "promedio": "Promedio",
        "errores_4xx": "Errores 4xx",
        "errores_5xx": "Errores 5xx",
    })

    fig_tiempo = px.line(
        df, x="hora", y=["Promedio", "p95", "p99"],
        title="Tiempo de respuesta",
        labels={"hora": "Hora", "value": "Milisegundos", "variable": ""},
        color_discrete_sequence=["#1f77b4", "orange", "red"],
        template="plotly_white",
    )

    fig_rpm = px.line(
        df, x="hora", y="rpm",
        title="Throughput (peticiones por minuto)",
        labels={"hora": "Hora", "rpm": "RPM"},
        color_discrete_sequence=["green"],
        template="plotly_white",
    )

    fig_errores = px.bar(
        df, x="hora", y=["Errores 4xx", "Errores 5xx"],
        title="Errores 4xx y 5xx",
        labels={"hora": "Hora", "value": "Cantidad", "variable": ""},
        color_discrete_sequence=["orange", "red"],
        template="plotly_white",
    )

    return fig_tiempo, fig_rpm, fig_errores


if __name__ == "__main__":
    app.run(debug=True)