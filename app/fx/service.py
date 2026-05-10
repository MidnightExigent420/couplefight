"""FX rate fetching and caching.

Uses frankfurter.app (no API key) by default. Rates cached daily in FXRate table.
All conversion goes through `convert(amount, src, dst, on_date)`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import logging

import requests
from flask import current_app

from ..extensions import db
from ..models import FXRate

log = logging.getLogger(__name__)


def _cached_rate(src: str, dst: str, on: date) -> Decimal | None:
    row = (
        FXRate.query.filter_by(from_currency=src, to_currency=dst, date=on)
        .order_by(FXRate.id.desc())
        .first()
    )
    return Decimal(row.rate) if row else None


def _store_rate(src: str, dst: str, rate: Decimal, on: date):
    existing = FXRate.query.filter_by(from_currency=src, to_currency=dst, date=on).first()
    if existing:
        existing.rate = rate
    else:
        db.session.add(FXRate(from_currency=src, to_currency=dst, rate=rate, date=on))
    db.session.commit()


def _fetch_rate(src: str, dst: str) -> Decimal:
    base = current_app.config["FX_API_BASE"].rstrip("/")
    # frankfurter.app: https://api.frankfurter.app/latest?from=USD&to=EUR
    url = f"{base}/latest"
    try:
        resp = requests.get(url, params={"from": src, "to": dst}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        rate = data.get("rates", {}).get(dst)
        if rate is None:
            raise ValueError(f"FX response missing rate for {dst}: {data}")
        return Decimal(str(rate))
    except (requests.RequestException, ValueError) as e:
        log.warning("FX fetch failed for %s->%s: %s", src, dst, e)
        # Fall back to 1.0 — better than crashing; logged for ops to investigate.
        return Decimal("1")


def get_rate(src: str, dst: str, on: date | None = None) -> Decimal:
    src = (src or "USD").upper()
    dst = (dst or "USD").upper()
    if src == dst:
        return Decimal("1")
    on = on or date.today()
    cached = _cached_rate(src, dst, on)
    if cached is not None:
        return cached
    rate = _fetch_rate(src, dst)
    try:
        _store_rate(src, dst, rate, on)
    except Exception:
        db.session.rollback()
        log.exception("Failed to cache FX rate")
    return rate


def convert(amount, src: str, dst: str, on: date | None = None) -> Decimal:
    if amount is None:
        return Decimal("0")
    rate = get_rate(src, dst, on)
    return (Decimal(amount) * rate).quantize(Decimal("0.01"))
