from __future__ import annotations
from flask import Blueprint, render_template, request
import base

signals_bp = Blueprint("signals", __name__)

@signals_bp.route("/signals")
def signals_home():
    signal_type = request.args.get("type")
    signals = base.get_signals_by_type(signal_type=signal_type, limit=50)
    costly = [s for s in signals if s.get("signal_type") == "costly signal"]
    cheap = [s for s in signals if s.get("signal_type") == "cheap talk"]
    noise = [s for s in signals if s.get("signal_type") in ("noise", "mixed")]
    other = [s for s in signals if s not in costly and s not in cheap and s not in noise]
    return render_template("signals.html",
        signals=signals, costly=costly, cheap=cheap, noise=noise, other=other,
        signal_type=signal_type, total=len(signals))
