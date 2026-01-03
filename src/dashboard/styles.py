"""
Módulo de estilos del Dashboard.
CSS y configuración visual.
"""

INDEX_STRING = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Dashboard COLCAP - Infraestructuras Paralelas</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .main-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 20px;
                border-radius: 0 0 12px 12px;
                margin-bottom: 15px;
                box-shadow: 0 3px 10px rgba(102, 126, 234, 0.25);
            }
            .main-header h2 {
                font-size: 1.4rem;
                margin-bottom: 2px;
            }
            .main-header p {
                font-size: 0.8rem;
            }
            .metric-card {
                background: white;
                border-radius: 10px;
                padding: 12px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                border: none;
                transition: transform 0.2s;
            }
            .metric-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .metric-card h2 {
                font-size: 1.8rem;
                font-weight: 700;
                margin: 0;
            }
            .metric-card p {
                color: #6c757d;
                margin: 4px 0 0 0;
                font-size: 0.75rem;
            }
            .card-section {
                background: white;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            .section-title {
                color: #495057;
                font-weight: 600;
                font-size: 0.95rem;
                margin-bottom: 12px;
                padding-bottom: 6px;
                border-bottom: 2px solid #667eea;
                display: inline-block;
            }
            .nav-tabs {
                border: none;
                background: white;
                border-radius: 8px;
                padding: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                display: flex;
                width: 100%;
            }
            .nav-tabs .nav-item {
                flex: 1;
            }
            .nav-tabs .nav-link {
                border: none;
                color: #6c757d;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 0.95rem;
                margin: 0 2px;
                width: 100%;
                text-align: center;
            }
            .nav-tabs .nav-link.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .nav-tabs .nav-link:hover:not(.active) {
                background: #f1f3f4;
            }
            .config-item {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 12px 15px;
                margin-bottom: 10px;
            }
            .config-item label {
                color: #495057;
                font-weight: 600;
                margin-bottom: 6px;
                font-size: 0.85rem;
                display: block;
            }
            .info-card {
                background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
                border-radius: 8px;
                padding: 10px 14px;
                border-left: 3px solid #667eea;
            }
            .info-card h6 {
                color: #667eea;
                font-weight: 600;
                font-size: 0.85rem;
                margin-bottom: 6px;
            }
            .info-card p {
                margin: 3px 0;
                color: #495057;
                font-size: 0.8rem;
            }
            .status-badge {
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.75rem;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Colores del tema
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'purple': '#6f42c1',
    'gray': '#6c757d',
    'light_gray': '#f8f9fa',
    'border': '#eee'
}

# Estilos de tabla
TABLE_HEADER_STYLE = {
    'backgroundColor': COLORS['primary'],
    'color': 'white',
    'fontWeight': '600',
    'border': 'none',
    'padding': '8px',
    'fontSize': '11px'
}

TABLE_CELL_STYLE = {
    'backgroundColor': 'white',
    'color': '#495057',
    'border': '1px solid #eee',
    'padding': '8px',
    'fontSize': '11px',
    'textAlign': 'left'
}

TABLE_CONDITIONAL_STYLES = [
    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
    {'if': {'filter_query': '{Sentimiento} = Positivo', 'column_id': 'Sentimiento'}, 'color': COLORS['success'], 'fontWeight': '600'},
    {'if': {'filter_query': '{Sentimiento} = Negativo', 'column_id': 'Sentimiento'}, 'color': COLORS['danger'], 'fontWeight': '600'},
    {'if': {'filter_query': '{Sentimiento} = Neutral', 'column_id': 'Sentimiento'}, 'color': COLORS['warning'], 'fontWeight': '600'},
]

# Configuración de gráficos
GRAPH_CONFIG = {'displayModeBar': False}

GRAPH_LAYOUT_BASE = {
    'template': 'plotly_white',
    'margin': dict(l=50, r=25, t=20, b=45)
}
