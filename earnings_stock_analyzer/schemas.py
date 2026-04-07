from __future__ import annotations

from typing import NotRequired, TypedDict


class EarningsReaction(TypedDict):
    date: str
    close_to_open_pct: float
    close_to_close_pct: float
    open_to_close_pct: float


class MomentumEntry(TypedDict):
    date: str
    c2o: float
    c2c: float
    o2c: float


class MomentumResult(TypedDict):
    ticker: str
    total_events: int
    positive_gap_days: int
    negative_gap_days: int
    momentum_total_count: int
    momentum_positive_count: int
    momentum_negative_count: int
    pct_momentum_total: float
    pct_momentum_pos: float
    pct_momentum_neg: float
    momentum_dates_total: list[MomentumEntry]
    momentum_dates_pos: list[MomentumEntry]
    momentum_dates_neg: list[MomentumEntry]


class ReactionSummary(TypedDict):
    avg_abs_close_to_open: float
    avg_abs_close_to_close: float
    avg_abs_open_to_close: float
    positive_days: int
    negative_days: int
    total_days: int
    positive_pct: float
    negative_pct: float
    avg_pos_close_to_open: NotRequired[float]
    avg_pos_close_to_close: NotRequired[float]
    avg_pos_open_to_close: NotRequired[float]
    avg_neg_close_to_open: NotRequired[float]
    avg_neg_close_to_close: NotRequired[float]
    avg_neg_open_to_close: NotRequired[float]
