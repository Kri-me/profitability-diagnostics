import sys
import subprocess
import json
from src.core.paths import PROJECT_ROOT, RESULTS_DIR

def run_simulation_cli(params: dict) -> dict:
    """
    Calls simulate.py as a subprocess and returns structured output.
    This avoids coupling dashboard directly to simulation internals.
    """

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "src" / "simulations" / "simulate.py"),
    ]

    if params.get("discount_cap") is not None:
        cmd += ["--discount-cap", str(params["discount_cap"])]

    if params.get("reclassify_band") is not None:
        cmd += ["--reclassify-band", str(params["reclassify_band"])]

    if params.get("reclassify_target") is not None:
        cmd += ["--reclassify-target", str(params["reclassify_target"])]

    # Support both naming conventions
    marketing_shift = params.get("marketing_shift") if params.get("marketing_shift") is not None else params.get("shift_pct")
    if marketing_shift is not None:
        cmd += ["--marketing-shift", str(marketing_shift)]

    shipping_opt = params.get("shipping_opt") if params.get("shipping_opt") is not None else params.get("shipping_cost_reduction_pct")
    if shipping_opt is not None:
        cmd += ["--shipping-opt", str(shipping_opt)]

    if params.get("name"):
        cmd += ["--name", str(params["name"])]

    # Run simulation
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)

    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime)

    if not files:
        raise FileNotFoundError("No simulation output found")

    latest = files[-1]

    with open(latest, "r") as f:
        data = json.load(f)

    return {
        "file": str(latest),
        "data": data
    }