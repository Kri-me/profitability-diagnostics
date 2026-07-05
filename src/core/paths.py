from pathlib import Path

# Project root (resolved relative to this file: src/core/paths.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Core directories
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = DATA_DIR / "simulation_results"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Data contract paths
DRIVERS_PATH = DATA_DIR / "driver_importance.csv"
