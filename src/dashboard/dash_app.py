"""
App y callbacks
"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from datetime import datetime

# Módulos internos
from .data import get_redis, clear_scalability_history
from .styles import INDEX_STRING
from .components import build_resultados, build_infra

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.index_string = INDEX_STRING

# Layout principal
app.layout = html.Div([
    # Header
    html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H2("Dashboard COLCAP", className="mb-1"),
                    html.P("Correlación de Noticias Colombianas con el Índice Bursátil",
                           style={'opacity': '0.9', 'marginBottom': 0})
                ], lg=8, md=12, className="mb-2 mb-lg-0"),
                dbc.Col([
                    html.Div([
                        html.Span(id="clock", style={'fontSize': '1.3rem', 'fontWeight': '500'}),
                        html.Br(),
                        dbc.Badge(id="redis-status", className="status-badge mt-2")
                    ], className="text-end")
                ], lg=4, md=6, className="d-flex align-items-center justify-content-end")
            ])
        ], fluid=True)
    ], className="main-header"),

    # Content
    dbc.Container([
        # Tabs
        dbc.Tabs([
            dbc.Tab(label="📊 Resultados", tab_id="resultados"),
            dbc.Tab(label="⚙️ Infraestructura", tab_id="infra"),
        ], id="tabs", active_tab="resultados", className="mb-4"),

        html.Div(id="content"),

        # Stores
        dcc.Interval(id="interval", interval=1000, n_intervals=0)
    ], fluid=True, style={'maxWidth': '1400px', 'margin': '0 auto'})
])


# CALLBACKS

@app.callback(
    [Output("clock", "children"), Output("redis-status", "children"), Output("redis-status", "color")],
    Input("interval", "n_intervals")
)
def update_status(n):
    """Actualiza reloj y estado de Redis"""
    t = datetime.now().strftime("%H:%M:%S")
    r = get_redis()
    if r:
        return t, "Redis Conectado", "success"
    return t, "Redis Desconectado", "danger"


@app.callback(
    Output("content", "children"),
    [Input("tabs", "active_tab"), Input("interval", "n_intervals")]
)
def render(tab, n):
    """Pestaña activa"""
    if tab == "resultados":
        return build_resultados()
    elif tab == "infra":
        return build_infra()
    return build_resultados()


@app.callback(
    Output("reset-scalability-btn", "n_clicks"),
    Input("reset-scalability-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_scalability(n_clicks):
    """Reiniciar el historial de escalabilidad"""
    if n_clicks:
        clear_scalability_history()
    return 0


def run():
    """Inicia el servidor del dashboard"""
    print("=" * 55)
    print("  Dashboard COLCAP - Infraestructuras Paralelas")
    print("  http://localhost:8050")
    print("=" * 55)
    app.run(host="0.0.0.0", port=8050, debug=False)

if __name__ == '__main__':
    run()
