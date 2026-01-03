#!/usr/bin/env python3
"""
Ejecucion principal
    python main.py producer   # Productor
    python main.py worker     # Worker
    python main.py dashboard  # Dashboard (Dash)
"""
import sys
import os

# Directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_producer():
    """Componente Producer"""
    from src.producer.main import main
    main()


def run_worker():
    """Componente Worker"""
    from src.worker.main import main
    main()


def run_dashboard():
    """Componente Dashboard"""
    from src.dashboard.dash_app import run
    run()


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    component = sys.argv[1].lower()

    components = {
        'producer': run_producer,
        'worker': run_worker,
        'dashboard': run_dashboard,
    }

    if component in components:
        components[component]()
    else:
        print(f"Error: Componente '{component}' no reconocido.")
        sys.exit(1)


if __name__ == "__main__":
    main()
