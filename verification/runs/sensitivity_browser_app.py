from pathlib import Path
from backend.lab.api import create_app

def create_instance():
    return create_app(Path(__file__).resolve().parents[2]/'data/sensitivity-browser-instance')
