"""
Componente de Resultados del Dashboard.
Visualización de noticias analizadas y correlación con COLCAP.
"""
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from ..data import get_results, load_colcap
from ..styles import (
    COLORS, TABLE_HEADER_STYLE, TABLE_CELL_STYLE,
    TABLE_CONDITIONAL_STYLES, GRAPH_CONFIG
)


def _build_metric_cards(results, pos, neg, neu):
    """Tarjetas de métricas"""
    return dbc.Row([
        dbc.Col(html.Div([
            html.H2(len(results), style={'color': COLORS['primary']}),
            html.P("Noticias Analizadas")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
        dbc.Col(html.Div([
            html.H2(pos, style={'color': COLORS['success']}),
            html.P("Sentimiento Positivo")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
        dbc.Col(html.Div([
            html.H2(neu, style={'color': COLORS['warning']}),
            html.P("Sentimiento Neutral")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
        dbc.Col(html.Div([
            html.H2(neg, style={'color': COLORS['danger']}),
            html.P("Sentimiento Negativo")
        ], className="metric-card"), lg=3, md=6, className="mb-3"),
    ], className="mb-4")


def _process_news_by_date(results):
    """Agrupa noticias por fecha"""
    news_by_date = {}
    for r in results:
        fecha = r.get('fecha')
        if fecha:
            try:
                fecha_dt = pd.to_datetime(fecha).date()
                if fecha_dt not in news_by_date:
                    news_by_date[fecha_dt] = {'pos': 0, 'neg': 0, 'neu': 0, 'polarities': [], 'titles': []}
                sent = r.get('sentiment', {}).get('classification', 'neutral')
                polarity = r.get('sentiment', {}).get('polarity', 0)
                news_by_date[fecha_dt]['polarities'].append(polarity)
                news_by_date[fecha_dt]['titles'].append(r.get('title', '')[:30])
                if sent == 'positivo':
                    news_by_date[fecha_dt]['pos'] += 1
                elif sent == 'negativo':
                    news_by_date[fecha_dt]['neg'] += 1
                else:
                    news_by_date[fecha_dt]['neu'] += 1
            except:
                pass
    return news_by_date


def _get_colcap_variations():
    """Obtiene valor COLCAP por fecha"""
    colcap_var = {}
    colcap_data = load_colcap()
    if not colcap_data.empty:
        df_sorted = colcap_data.sort_values('Fecha')
        for _, row in df_sorted.iterrows():
            colcap_var[row['Fecha'].date()] = {'valor': row['Ultimo']}
    return colcap_var


def _build_correlation_chart(news_by_date, colcap_var):
    """Gráfico de correlación Sentimiento vs COLCAP"""
    fig = go.Figure()
    scatter_data = {'x': [], 'y': [], 'color': [], 'text': [], 'size': []}

    for fecha, data in news_by_date.items():
        if fecha in colcap_var:
            avg_polarity = sum(data['polarities']) / len(data['polarities']) if data['polarities'] else 0
            valor = colcap_var[fecha]['valor']
            total_news = data['pos'] + data['neg'] + data['neu']

            scatter_data['x'].append(avg_polarity)
            scatter_data['y'].append(valor)
            scatter_data['size'].append(max(10, min(30, total_news * 5)))
            scatter_data['text'].append(f"{fecha}<br>{total_news} noticias<br>Polaridad: {avg_polarity:.2f}<br>COLCAP: {valor:,.0f}")

            if avg_polarity > 0.1:
                scatter_data['color'].append(COLORS['success'])
            elif avg_polarity < -0.1:
                scatter_data['color'].append(COLORS['danger'])
            else:
                scatter_data['color'].append(COLORS['warning'])

    if scatter_data['x']:
        fig.add_trace(go.Scatter(
            x=scatter_data['x'], y=scatter_data['y'],
            mode='markers',
            marker=dict(size=scatter_data['size'], color=scatter_data['color'],
                       line=dict(width=1, color='white'), opacity=0.8),
            text=scatter_data['text'],
            hovertemplate='%{text}<extra></extra>',
            showlegend=False
        ))

        if len(scatter_data['x']) > 2:
            z = np.polyfit(scatter_data['x'], scatter_data['y'], 1)
            p = np.poly1d(z)
            x_line = [min(scatter_data['x']), max(scatter_data['x'])]
            fig.add_trace(go.Scatter(
                x=x_line, y=[p(x) for x in x_line],
                mode='lines', name='Tendencia',
                line=dict(color=COLORS['primary'], width=2, dash='dash'),
                hoverinfo='skip'
            ))

        fig.add_vline(x=0, line_dash="dot", line_color="#aaa", line_width=1)
    else:
        fig.add_annotation(text="Esperando datos para correlación...", showarrow=False,
                          font=dict(size=14, color=COLORS['gray']))

    fig.update_layout(
        template='plotly_white',
        height=280,
        margin=dict(l=50, r=25, t=20, b=45),
        xaxis=dict(title='Polaridad Promedio de Noticias', gridcolor='#eee', title_font_size=11, zeroline=False),
        yaxis=dict(title='COLCAP', gridcolor='#eee', title_font_size=11, zeroline=False),
        hovermode='closest'
    )
    return fig


def _build_timeline_chart(news_by_date, colcap_var):
    """Gráfico de timeline  últimos 6 meses"""
    fig = go.Figure()

    # Usar fechas de COLCAP como base (últimos 6 meses ~180 días)
    if colcap_var:
        all_dates = sorted(colcap_var.keys())[-180:]  # Últimos 6 meses
    elif news_by_date:
        all_dates = sorted(news_by_date.keys())[-180:]
    else:
        all_dates = []

    if all_dates:
        # Construir arrays para cada día (0 si no hay noticias ese día)
        pos_counts = []
        neu_counts = []
        neg_counts = []
        colcap_vars = []

        for d in all_dates:
            if d in news_by_date:
                pos_counts.append(news_by_date[d]['pos'])
                neu_counts.append(news_by_date[d]['neu'])
                neg_counts.append(-news_by_date[d]['neg'])
            else:
                pos_counts.append(0)
                neu_counts.append(0)
                neg_counts.append(0)

            if d in colcap_var:
                colcap_vars.append(colcap_var[d]['valor'])
            else:
                colcap_vars.append(None)

        # Barras de noticias
        fig.add_trace(go.Bar(
            x=all_dates, y=pos_counts, name='Positivas',
            marker_color=COLORS['success'], opacity=0.85
        ))
        fig.add_trace(go.Bar(
            x=all_dates, y=neu_counts, name='Neutrales',
            marker_color=COLORS['warning'], opacity=0.85
        ))
        fig.add_trace(go.Bar(
            x=all_dates, y=neg_counts, name='Negativas',
            marker_color=COLORS['danger'], opacity=0.85
        ))

        # Línea COLCAP
        fig.add_trace(go.Scatter(
            x=all_dates, y=colcap_vars, name='COLCAP %',
            mode='lines', yaxis='y2',
            line=dict(color=COLORS['primary'], width=1.5),
            connectgaps=True
        ))

        num_dates = len(all_dates)
    else:
        fig.add_annotation(text="Sin datos disponibles", showarrow=False,
                          font=dict(size=14, color=COLORS['gray']))
        num_dates = 0

    fig.update_layout(
        template='plotly_white',
        height=600,
        margin=dict(l=45, r=45, t=25, b=60),
        barmode='relative',
        xaxis=dict(
            title='',
            gridcolor='#eee',
            tickfont_size=8,
            tickangle=-45,
            tickformat='%b %d',
            dtick='M1',  # Una etiqueta por mes
            type='date'
        ),
        yaxis=dict(title='Noticias', gridcolor='#eee', title_font_size=10, side='left'),
        yaxis2=dict(title='COLCAP', overlaying='y', side='right', title_font_size=10,
                   showgrid=False),
        legend=dict(orientation='h', y=1.12, x=0.5, xanchor='center', font=dict(size=8)),
        hovermode='x unified',
        bargap=0.1
    )
    return fig


def _build_sentiment_pie(pos, neg, neu):
    """Gráfico de pie de sentimientos"""
    fig = go.Figure(go.Pie(
        labels=['Positivo', 'Negativo', 'Neutral'],
        values=[pos, neg, neu],
        hole=0.5,
        marker_colors=[COLORS['success'], COLORS['danger'], COLORS['warning']],
        textinfo='percent+label',
        textfont_size=11,
        pull=[0.02, 0.02, 0.02]
    ))
    fig.update_layout(
        template='plotly_white',
        height=220,
        margin=dict(l=15, r=15, t=20, b=15),
        showlegend=False,
        annotations=[dict(text='Sentimientos', x=0.5, y=0.5, font_size=10, showarrow=False)]
    )
    return fig


def _build_domain_bar(results):
    """Gráfico de barras por dominio"""
    domains = {}
    for r in results:
        d = r.get('domain', 'Desconocido')
        domains[d] = domains.get(d, 0) + 1

    sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
    fig = go.Figure(go.Bar(
        x=[d[0] for d in sorted_domains],
        y=[d[1] for d in sorted_domains],
        marker_color=COLORS['primary'],
        marker_line_width=0,
        text=[d[1] for d in sorted_domains],
        textposition='outside'
    ))

    max_count = max([d[1] for d in sorted_domains]) if sorted_domains else 1
    y_max = max(max_count * 2, 10)

    fig.update_layout(
        template='plotly_white',
        height=280,
        margin=dict(l=25, r=25, t=35, b=80),
        xaxis=dict(title='', tickfont=dict(size=9), tickangle=-45),
        yaxis=dict(title='Noticias', gridcolor='#eee', title_font_size=11, range=[0, y_max])
    )
    return fig


def _build_results_table(results):
    """Tabla de resultados"""
    rows = []
    for r in results:
        s = r.get('sentiment', {})
        rows.append({
            'Fuente': r.get('domain', '-'),
            'Título': (r.get('title', '-')[:50] + '..') if len(r.get('title', '')) > 50 else r.get('title', '-'),
            'Sentimiento': s.get('classification', '-').capitalize(),
            'Polaridad': f"{s.get('polarity', 0):.2f}",
            'COLCAP': f"{r.get('colcap_value', 0):,.0f}" if r.get('colcap_value') else '-',
            'Fecha': r.get('fecha', '-')
        })

    if rows:
        return dash_table.DataTable(
            data=rows,
            columns=[{'name': c, 'id': c} for c in rows[0].keys()],
            style_header=TABLE_HEADER_STYLE,
            style_cell=TABLE_CELL_STYLE,
            style_data_conditional=TABLE_CONDITIONAL_STYLES,
            page_size=10,
            page_action='native',
            style_table={'borderRadius': '8px', 'overflow': 'hidden'}
        )
    return dbc.Alert("Esperando resultados del procesamiento...", color="info")


def build_resultados():
    """Vista completa de resultados"""
    results = get_results()

    pos = sum(1 for r in results if r.get('sentiment', {}).get('classification') == 'positivo')
    neg = sum(1 for r in results if r.get('sentiment', {}).get('classification') == 'negativo')
    neu = len(results) - pos - neg

    # Procesar datos
    news_by_date = _process_news_by_date(results)
    colcap_var = _get_colcap_variations()

    # Construir componentes
    cards = _build_metric_cards(results, pos, neg, neu)
    fig_correlation = _build_correlation_chart(news_by_date, colcap_var)
    fig_timeline = _build_timeline_chart(news_by_date, colcap_var)
    fig_pie = _build_sentiment_pie(pos, neg, neu)
    fig_domains = _build_domain_bar(results)
    table = _build_results_table(results)

    return html.Div([
        cards,

        # Timeline
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Timeline: Noticias y Variación COLCAP", className="section-title"),
                    html.P("Barras = noticias por sentimiento. Línea = valor COLCAP",
                          style={'color': COLORS['gray'], 'fontSize': '0.75rem', 'marginBottom': '8px'}),
                    dcc.Graph(figure=fig_timeline, config=GRAPH_CONFIG)
                ], className="card-section")
            ], width=12, className="mb-3"),
        ]),

        # Correlación Sentimiento vs COLCAP
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Correlación Sentimiento vs COLCAP", className="section-title"),
                    html.P("Cada punto = 1 día. Tamaño = cantidad de noticias",
                          style={'color': COLORS['gray'], 'fontSize': '0.75rem', 'marginBottom': '8px'}),
                    dcc.Graph(figure=fig_correlation, config=GRAPH_CONFIG)
                ], className="card-section")
            ], width=12, className="mb-3"),
        ]),

        # Gráficos secundarios
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Distribución de Sentimientos", className="section-title"),
                    dcc.Graph(figure=fig_pie, config=GRAPH_CONFIG)
                ], className="card-section")
            ], lg=5, md=12, className="mb-3"),
            dbc.Col([
                html.Div([
                    html.H5("Noticias por Fuente", className="section-title"),
                    dcc.Graph(figure=fig_domains, config=GRAPH_CONFIG)
                ], className="card-section")
            ], lg=7, md=12, className="mb-3"),
        ]),

        # Tabla
        html.Div([
            html.H5("Resultados Recientes", className="section-title"),
            table
        ], className="card-section")
    ])
