"""El consumo y la producción mensual de gas natural del ENARGAS, por la API de series de tiempo del Estado.

Una sola llamada trae todas las series pedidas; la respuesta queda cacheada en
data/raw/series_gas.json para no depender de la red en cada corrida. Todo en millones de m³
por mes, desde enero de 1996.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

from . import DATA_RAW, DISTRIBUIDORAS, SERIES

API = "https://apis.datos.gob.ar/series/api/series/"


def fetch(keys: dict[str, str] | None = None, cache: Path | None = DATA_RAW / "series_gas.json", refresh: bool = False, timeout: int = 120) -> pd.DataFrame:
    """Series mensuales como DataFrame (índice: primer día del mes; columnas: los nombres de `keys`)."""
    keys = keys or {**SERIES, **DISTRIBUIDORAS}
    datos = json.loads(Path(cache).read_text(encoding="utf-8")) if cache and Path(cache).exists() and not refresh else {}
    faltan = {k: v for k, v in keys.items() if k not in datos}
    if faltan:
        ids = list(faltan.values())
        for i in range(0, len(ids), 20):          # la API acepta hasta 40 series por llamada; se pide de a 20
            lote = dict(list(faltan.items())[i:i + 20])
            r = requests.get(API, params={"ids": ",".join(lote.values()), "limit": 1000, "format": "json"}, timeout=timeout,
                             headers={"User-Agent": "gas-lab/0.1 (+https://github.com/dpinero14)"})
            r.raise_for_status()
            filas = r.json()["data"]
            for j, k in enumerate(lote):
                datos[k] = [[f[0], f[j + 1]] for f in filas]
        if cache:
            Path(cache).parent.mkdir(parents=True, exist_ok=True)
            Path(cache).write_text(json.dumps(datos), encoding="utf-8")
    out = {}
    for k in keys:
        s = pd.DataFrame(datos[k], columns=["fecha", k]).dropna()
        out[k] = s.set_index(pd.to_datetime(s["fecha"]))[k].astype(float)
    df = pd.DataFrame(out).sort_index()
    df.index.name = "fecha"
    return df.asfreq("MS")


def per_day(df: pd.DataFrame) -> pd.DataFrame:
    """De millones de m³ por mes a millones de m³ por día (divide por los días de cada mes)."""
    return df.div(df.index.days_in_month, axis=0)


def annual(df: pd.DataFrame, completo: bool = True) -> pd.DataFrame:
    """Suma anual; con `completo`, solo los años con los 12 meses."""
    g = df.groupby(df.index.year)
    a = g.sum(min_count=1)
    if completo:
        a = a[g.count().min(axis=1) == 12]
    return a


__all__ = ["API", "fetch", "per_day", "annual"]
