"""Production wrapper for the stock dashboard.

Adds a lightweight real-time quote endpoint backed by TWSE MIS and injects the
front-end auto-refresh script without modifying the large legacy index.html.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from main import app

TWSE_MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
QUOTE_TTL_SECONDS = 8
MAX_QUOTE_IDS = 20

_quote_cache: dict[tuple[str, ...], tuple[float, dict[str, Any]]] = {}
_quote_lock = asyncio.Lock()


def _number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "--", "---"}:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _clean_ids(raw: str) -> list[str]:
    ids: list[str] = []
    for token in raw.split(","):
        stock_id = token.strip().upper()
        if not stock_id or len(stock_id) > 10:
            continue
        if not all(ch.isalnum() for ch in stock_id):
            continue
        if stock_id not in ids:
            ids.append(stock_id)
        if len(ids) >= MAX_QUOTE_IDS:
            break
    return ids


def _normalise_quote(item: dict[str, Any]) -> dict[str, Any] | None:
    stock_id = str(item.get("c") or "").strip().upper()
    if not stock_id:
        return None

    previous_close = _number(item.get("y"))
    last_price = _number(item.get("z"))
    if last_price is None:
        last_price = _number(item.get("pz"))
    if last_price is None:
        last_price = _number(item.get("o"))
    if last_price is None:
        last_price = previous_close
    if last_price is None:
        return None

    change = last_price - previous_close if previous_close is not None else 0.0
    change_pct = (
        change / previous_close * 100
        if previous_close not in (None, 0)
        else 0.0
    )
    volume_lots = _number(item.get("v")) or 0.0

    date_raw = str(item.get("d") or "")
    date = (
        f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        if len(date_raw) == 8
        else date_raw
    )
    quote_time = str(item.get("t") or item.get("%") or "")

    return {
        "id": stock_id,
        "name": item.get("n") or "",
        "exchange": item.get("ex") or "",
        "price": last_price,
        "previous_close": previous_close,
        "change": change,
        "change_pct": change_pct,
        "open": _number(item.get("o")),
        "high": _number(item.get("h")),
        "low": _number(item.get("l")),
        "volume_lots": volume_lots,
        "volume_shares": int(volume_lots * 1000),
        "date": date,
        "time": quote_time,
        "timestamp_ms": int(_number(item.get("tlong")) or 0),
    }


async def _fetch_twse_quotes(ids: list[str]) -> dict[str, Any]:
    # Request both markets. TWSE MIS only returns the matching channel, so this
    # avoids maintaining a fragile listed/OTC mapping in the app.
    channels: list[str] = []
    for stock_id in ids:
        channels.extend((f"tse_{stock_id}.tw", f"otc_{stock_id}.tw"))

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://mis.twse.com.tw/stock/fibest.jsp",
    }
    params = {
        "ex_ch": "|".join(channels),
        "json": "1",
        "delay": "0",
        "_": str(int(time.time() * 1000)),
    }

    timeout = httpx.Timeout(12.0, connect=6.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        response = await client.get(TWSE_MIS_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    quotes_by_id: dict[str, dict[str, Any]] = {}
    for item in payload.get("msgArray", []):
        quote = _normalise_quote(item)
        if quote and quote["id"] in ids:
            quotes_by_id[quote["id"]] = quote

    quotes = [quotes_by_id[stock_id] for stock_id in ids if stock_id in quotes_by_id]
    query_time = payload.get("queryTime") or {}
    return {
        "source": "TWSE MIS",
        "quotes": quotes,
        "requested": ids,
        "missing": [stock_id for stock_id in ids if stock_id not in quotes_by_id],
        "query_date": query_time.get("sysDate"),
        "query_time": query_time.get("sysTime"),
        "fetched_at_ms": int(time.time() * 1000),
    }


async def _get_quotes(ids: list[str]) -> dict[str, Any]:
    key = tuple(ids)
    now = time.monotonic()
    cached = _quote_cache.get(key)
    if cached and now - cached[0] < QUOTE_TTL_SECONDS:
        return cached[1]

    async with _quote_lock:
        now = time.monotonic()
        cached = _quote_cache.get(key)
        if cached and now - cached[0] < QUOTE_TTL_SECONDS:
            return cached[1]
        result = await _fetch_twse_quotes(ids)
        _quote_cache[key] = (now, result)
        if len(_quote_cache) > 100:
            oldest = min(_quote_cache, key=lambda cache_key: _quote_cache[cache_key][0])
            _quote_cache.pop(oldest, None)
        return result


@app.middleware("http")
async def live_quote_and_script_middleware(request: Request, call_next):
    path = request.url.path

    if path == "/api/live/quotes":
        ids = _clean_ids(request.query_params.get("ids", ""))
        if not ids:
            return JSONResponse(
                {"detail": "ids query parameter is required"}, status_code=400
            )
        try:
            result = await _get_quotes(ids)
            return JSONResponse(
                result,
                headers={"Cache-Control": "no-store, max-age=0"},
            )
        except (httpx.HTTPError, ValueError) as exc:
            return JSONResponse(
                {
                    "detail": "即時報價來源暫時無法連線",
                    "error": str(exc),
                    "quotes": [],
                },
                status_code=503,
                headers={"Cache-Control": "no-store, max-age=0"},
            )

    response = await call_next(request)

    content_type = response.headers.get("content-type", "")
    if path not in {"/", "/index.html"} or "text/html" not in content_type:
        return response

    body = b"".join([chunk async for chunk in response.body_iterator])
    marker = b"/live-refresh.js"
    if marker not in body and b"</body>" in body:
        script = b'<script src="/live-refresh.js?v=20260831"></script>\n'
        body = body.replace(b"</body>", script + b"</body>", 1)

    headers = dict(response.headers)
    headers.pop("content-length", None)
    headers["Cache-Control"] = "no-cache"
    return Response(
        content=body,
        status_code=response.status_code,
        headers=headers,
        media_type=None,
        background=response.background,
    )
