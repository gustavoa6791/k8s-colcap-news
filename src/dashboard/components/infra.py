"""
Componente de Infraestructura del Dashboard.
Visualización de workers y métricas del sistema.
"""
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

from ..data import get_metrics, get_workers, get_throughput_history, record_throughput_snapshot, get_scalability_metrics, get_producer_logs, clear_scalability_history
from ..styles import COLORS, TABLE_HEADER_STYLE, TABLE_CELL_STYLE, GRAPH_CONFIG


def _build_infra_cards(metrics, workers, throughput):
    """Tarjetas métricas de infraestructura"""
    return dbc.Row([
        dbc.Col(html.Div([
            html.H2(metrics['queue'], style={'color': COLORS['primary']}),
            html.P("Tareas Pendientes")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
        dbc.Col(html.Div([
            html.H2(metrics['processed'], style={'color': COLORS['success']}),
            html.P("WARCs Procesados")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
        dbc.Col(html.Div([
            html.H2(len(workers), style={'color': COLORS['purple']}),
            html.P("Workers Activos")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
        dbc.Col(html.Div([
            html.H2(f"{throughput:.1f}", style={'color': COLORS['danger']}),
            html.P("Throughput (t/min)")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
    ], className="mb-4")


def _build_workers_chart(workers):
    """Gráfico de carga de workers"""
    if not workers:
        fig = go.Figure()
        fig.add_annotation(text="Sin workers activos", showarrow=False,
                          font=dict(size=14, color=COLORS['gray']))
        fig.update_layout(template='plotly_white', height=250)
        return fig

    wdata = [
        {
            'Worker': w.get('worker_id', '-').split('-')[-1],
            'Procesados': int(w.get('processed', 0)),
            'Errores': int(w.get('errors', 0)),
            'Tasa': f"{float(w.get('rate', 0)):.1f}/min"
        }
        for w in workers
    ]

    max_processed = max([w['Procesados'] for w in wdata]) if wdata else 1
    y_range_max = max(max_processed * 2, 10)

    fig = go.Figure(go.Bar(
        x=[w['Worker'] for w in wdata],
        y=[w['Procesados'] for w in wdata],
        orientation='v',
        marker_color=COLORS['primary'],
        text=[w['Procesados'] for w in wdata],
        textposition='outside',
        textfont=dict(size=12, color='#495057')
    ))
    fig.update_layout(
        template='plotly_white',
        height=250,
        margin=dict(l=45, r=25, t=20, b=50),
        xaxis=dict(title='Worker ID', gridcolor='#eee', title_font_size=11),
        yaxis=dict(title='Tareas Procesadas', gridcolor='#eee', title_font_size=11, range=[0, y_range_max])
    )
    return fig


def _build_throughput_chart():
    """Gráfico de rendimiento vs tiempo"""
    history = get_throughput_history(seconds=300)

    fig = go.Figure()

    if not history or len(history) < 2:
        fig.add_annotation(
            text=f"Recopilando datos... ({len(history)} muestras)",
            showarrow=False,
            font=dict(size=14, color=COLORS['gray'])
        )
        fig.update_layout(template='plotly_white', height=280)
        return fig

    # Preparar datos
    times = [datetime.fromtimestamp(h['ts']).strftime('%H:%M:%S') for h in history]
    rates = [h['rate'] for h in history]
    workers_count = [h['workers'] for h in history]

    # Línea de throughput (tareas/min)
    fig.add_trace(go.Scatter(
        x=times,
        y=rates,
        mode='lines+markers',
        name='Throughput (t/min)',
        line=dict(color=COLORS['primary'], width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.1)'
    ))

    # Línea de workers
    fig.add_trace(go.Scatter(
        x=times,
        y=workers_count,
        mode='lines+markers',
        name='Workers',
        line=dict(color=COLORS['success'], width=2, dash='dash'),
        marker=dict(size=4),
        yaxis='y2'
    ))

    # Calcular rango Y dinámico
    max_rate = max(rates) if rates else 1
    max_workers = max(workers_count) if workers_count else 1

    fig.update_layout(
        template='plotly_white',
        height=600,
        margin=dict(l=60, r=60, t=30, b=50),
        xaxis=dict(
            title='Últimos 300 segundos (5 min)',
            gridcolor='#eee',
            title_font_size=11,
            tickangle=-45
        ),
        yaxis=dict(
            title='Throughput (tareas/min)',
            gridcolor='#eee',
            title_font_size=11,
            side='left',
            range=[0, max(max_rate * 1.2, 1)]
        ),
        yaxis2=dict(
            title='Workers',
            overlaying='y',
            side='right',
            title_font_size=11,
            showgrid=False,
            range=[0, max(max_workers + 2, 4)]
        ),
        legend=dict(
            orientation='h',
            y=1.12,
            x=0.5,
            xanchor='center',
            font=dict(size=10)
        ),
        hovermode='x unified'
    )

    return fig


def _build_workers_table(workers):
    """Tabla de workers"""
    if not workers:
        return dbc.Alert("No hay workers activos actualmente", color="warning")

    wdata = [
        {
            'Worker': w.get('worker_id', '-').split('-')[-1],
            'Procesados': int(w.get('processed', 0)),
            'Errores': int(w.get('errors', 0)),
            'Tasa': f"{float(w.get('rate', 0)):.1f}/min"
        }
        for w in workers
    ]

    return dash_table.DataTable(
        data=wdata,
        columns=[{'name': c, 'id': c} for c in wdata[0].keys()],
        style_header=TABLE_HEADER_STYLE,
        style_cell=TABLE_CELL_STYLE,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
    )


def _build_scalability_chart(current_workers=None):
    """Gráfico de Speedup y Eficiencia """
    metrics = get_scalability_metrics()
    changes = metrics.get('changes', [])

    fig = go.Figure()

    if not changes:
        fig.add_annotation(
            text="Recopilando datos de escalabilidad...\n(Cambia el número de workers para ver métricas)",
            showarrow=False,
            font=dict(size=12, color=COLORS['gray'])
        )
        fig.update_layout(template='plotly_white', height=300)
        return fig

    # Eje X muestra workers + hora con segundos para ver orden cronológico
    x_labels = [f"{c['workers']} workers ({datetime.fromtimestamp(c['ts']).strftime('%H:%M:%S')})" for c in changes]
    speedups = [c['speedup'] for c in changes]
    ideal_speedups = [c['ideal_speedup'] for c in changes]
    efficiencies = [c['efficiency'] for c in changes]

    # Barras de Speedup real vs ideal
    fig.add_trace(go.Bar(
        x=x_labels,
        y=speedups,
        name='Speedup Real',
        marker_color=COLORS['primary'],
        text=[f"{s:.1f}x" for s in speedups],
        textposition='outside'
    ))

    fig.add_trace(go.Bar(
        x=x_labels,
        y=ideal_speedups,
        name='Speedup Ideal',
        marker_color=COLORS['gray'],
        opacity=0.5,
        text=[f"{s}x" for s in ideal_speedups],
        textposition='outside'
    ))

    # Línea de eficiencia
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=efficiencies,
        mode='lines+markers',
        name='Eficiencia (%)',
        line=dict(color=COLORS['success'], width=3),
        marker=dict(size=10, symbol='diamond'),
        yaxis='y2'
    ))

    max_speedup = max(max(speedups), max(ideal_speedups)) if speedups else 1
    max_efficiency = max(efficiencies) if efficiencies else 100

    fig.update_layout(
        template='plotly_white',
        height=300,
        margin=dict(l=50, r=50, t=30, b=50),
        barmode='group',
        xaxis=dict(
            title='Número de Workers',
            gridcolor='#eee',
            title_font_size=11,
            type='category'
        ),
        yaxis=dict(
            title='Speedup (veces más rápido)',
            gridcolor='#eee',
            title_font_size=11,
            side='left',
            range=[0, max_speedup * 1.3]
        ),
        yaxis2=dict(
            title='Eficiencia (%)',
            overlaying='y',
            side='right',
            title_font_size=11,
            showgrid=False,
            range=[0, max(max_efficiency * 1.2, 120)]
        ),
        legend=dict(
            orientation='h',
            y=1.15,
            x=0.5,
            xanchor='center',
            font=dict(size=10)
        ),
        hovermode='x unified'
    )

    return fig




def _build_producer_logs():
    """Logs del producer"""
    logs = get_producer_logs(limit=30)

    if not logs:
        return html.Div([
            html.P("Sin logs disponibles", style={'color': COLORS['gray'], 'fontStyle': 'italic'})
        ])

    # Colores por nivel de log
    level_colors = {
        'INFO': '#17a2b8',
        'WARN': '#ffc107',
        'ERROR': '#dc3545'
    }

    log_items = []
    for log in logs:
        ts = datetime.fromtimestamp(log['ts']).strftime('%H:%M:%S')
        level = log.get('level', 'INFO')
        msg = log.get('msg', '')
        color = level_colors.get(level, COLORS['gray'])

        log_items.append(
            html.Div([
                html.Span(f"[{ts}]", style={
                    'color': COLORS['gray'],
                    'fontSize': '0.75rem',
                    'marginRight': '8px',
                    'fontFamily': 'monospace'
                }),
                html.Span(f"[{level}]", style={
                    'color': color,
                    'fontSize': '0.75rem',
                    'fontWeight': 'bold',
                    'marginRight': '8px',
                    'fontFamily': 'monospace'
                }),
                html.Span(msg, style={
                    'fontSize': '0.8rem',
                    'fontFamily': 'monospace'
                })
            ], style={
                'padding': '4px 8px',
                'borderBottom': '1px solid #eee'
            })
        )

    return html.Div(
        log_items,
        style={
            'maxHeight': '250px',
            'overflowY': 'auto',
            'backgroundColor': '#fafafa',
            'border': '1px solid #ddd',
            'borderRadius': '4px'
        }
    )


def build_infra():
    """Vista completa de infraestructura"""
    # Registrar snapshot de throughput
    record_throughput_snapshot()

    metrics = get_metrics()
    workers = get_workers()

    # Calcular throughput y número actual de workers
    throughput = sum(float(w.get('rate', 0)) for w in workers) if workers else 0
    current_workers = len(workers)

    # Construir componentes
    cards = _build_infra_cards(metrics, workers, throughput)
    fig_workers = _build_workers_chart(workers)
    fig_throughput = _build_throughput_chart()
    fig_scalability = _build_scalability_chart(current_workers=current_workers)
    wtbl = _build_workers_table(workers)
    producer_logs = _build_producer_logs()

    return html.Div([
        cards,

        # Gráfico de Rendimiento vs Tiempo  
        html.Div([
            html.H5("Rendimiento en Tiempo Real", className="section-title"),
            html.P("Throughput y workers activos (ventana: 5 min, actualización: 1s)",
                  style={'color': COLORS['gray'], 'fontSize': '0.8rem', 'marginBottom': '10px'}),
            dcc.Graph(id='throughput-chart', figure=fig_throughput, config=GRAPH_CONFIG)
        ], className="card-section", style={'padding': '20px', 'marginBottom': '20px'}),

        # Gráfico de Escalabilidad
        html.Div([
            html.Div([
                html.H5("Métricas de Escalabilidad", className="section-title", style={'display': 'inline-block'}),
                dbc.Button("Reiniciar", id="reset-scalability-btn", size="sm", color="secondary",
                          style={'float': 'right', 'marginTop': '-5px'})
            ], style={'marginBottom': '5px'}),
            html.P("Últimos 5 cambios de workers. "
                   "Speedup = Throughput(N)/Throughput(1). Eficiencia = Speedup/N × 100%",
                  style={'color': COLORS['gray'], 'fontSize': '0.8rem', 'marginBottom': '15px'}),
            dcc.Graph(id='scalability-chart', figure=fig_scalability, config=GRAPH_CONFIG)
        ], className="card-section", style={'padding': '20px', 'marginBottom': '20px'}),

        # Distribución de Workers
        html.Div([
            html.H5("Distribución de Carga entre Workers", className="section-title"),
            html.P("Balance de tareas procesadas por worker",
                  style={'color': COLORS['gray'], 'fontSize': '0.8rem', 'marginBottom': '20px'}),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_workers, config=GRAPH_CONFIG), lg=7, className="mb-3"),
                dbc.Col(html.Div(wtbl, style={'paddingTop': '20px'}), lg=5, className="mb-3"),
            ], style={'minHeight': '300px'})
        ], className="card-section", style={'padding': '20px', 'marginBottom': '20px'}),

        # Logs del Producer
        html.Div([
            html.H5("Logs del Producer", className="section-title"),
            html.P("Actividad reciente del indexador de Common Crawl",
                  style={'color': COLORS['gray'], 'fontSize': '0.8rem', 'marginBottom': '15px'}),
            producer_logs
        ], className="card-section", style={'padding': '20px'})
    ])
