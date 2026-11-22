"""Unit conversion helpers."""

from __future__ import annotations

CM_PER_INCH = 2.54
LB_PER_KG = 2.2046226218


def cm_to_inches(value: float) -> float:
    return value / CM_PER_INCH


def inches_to_cm(value: float) -> float:
    return value * CM_PER_INCH


def kg_to_lb(value: float) -> float:
    return value * LB_PER_KG


def lb_to_kg(value: float) -> float:
    return value / LB_PER_KG
