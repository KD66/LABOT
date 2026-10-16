"""LABOT - process planner for a 3x2 SBS liquid-handling deck.

Input : customer process description (sources, targets, channels, runs/day)
Output: deck layout, tip/consumable budget, timing and a Python module that
        contains the complete run (all variables + flat command list).
"""
from .spec import ProcessSpec
from .planner import build, optimize, Plan
from .emit import emit_python

__all__ = ["ProcessSpec", "build", "optimize", "Plan", "emit_python"]
