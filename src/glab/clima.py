"""La temperatura y los grados-día de calefacción.

La temperatura media diaria sale del reanálisis ERA5 por el archivo abierto de Open-Meteo, sin
clave, desde 1996, en una ciudad por área de distribución (ver `glab.CIUDADES`). Un grado-día
de calefacción (HDD) es cuánto le falta a la media del día para llegar a 18 °C: un día de 8 °C
suma 10. El consumo residencial sigue a esa suma casi en línea recta. El índice nacional pondera
cada ciudad por lo que consume su distribuidora.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import CIUDADES, DATA_RAW, T_BASE

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def fetch_city(clave: str, desde: str = "1996-01-01", hasta: str | None = None, raw: Path = DATA_RAW, timeout: int = 180) -> pd.Series:
    """Temperatura media diaria (°C) de la ciudad de una distribuidora, con caché en data/raw/clima/<clave>.csv."""
    hasta = hasta or (date.today() - timedelta(days=6)).isoformat()      # ERA5 llega con unos 5 días de atraso
    p = raw / "clima" / f"{clave}.csv"
    if p.exists():
        s = pd.read_csv(p, parse_dates=["fecha"]).set_index("fecha")["tmedia"]
        if str(s.index.max().date()) >= hasta and str(s.index.min().date()) <= desde:
            return s.loc[desde:hasta]
    nombre, lat, lon = CIUDADES[clave]
    r = requests.get(ARCHIVE, params={"latitude": lat, "longitude": lon, "start_date": desde, "end_date": hasta, "daily": "temperature_2m_mean",
                                      "timezone": "America/Argentina/Buenos_Aires"}, timeout=timeout)
    r.raise_for_status()
    d = r.json()["daily"]
    s = pd.Series(d["temperature_2m_mean"], index=pd.to_datetime(d["time"]), name="tmedia", dtype=float)
    s.index.name = "fecha"
    p.parent.mkdir(parents=True, exist_ok=True)
    s.to_frame().to_csv(p)
    return s


def hdd(t: pd.Series | np.ndarray, base: float = T_BASE):
    """Grados-día de calefacción de cada día."""
    return np.maximum(0.0, base - t)


def cdd(t: pd.Series | np.ndarray, base: float = 24.0):
    """Grados-día de refrigeración (aire acondicionado): lo que la media supera los 24 °C."""
    return np.maximum(0.0, t - base)


def daily_table(claves: tuple[str, ...] | None = None, **kw) -> pd.DataFrame:
    """Temperatura media diaria de todas las ciudades, una columna por distribuidora."""
    claves = claves or tuple(CIUDADES)
    return pd.DataFrame({k: fetch_city(k, **kw) for k in claves})


def weights(consumo_distribuidoras: pd.DataFrame, desde: int = 2015, hasta: int = 2025) -> pd.Series:
    """Peso de cada distribuidora en el consumo, promedio de los años pedidos; suma 1."""
    c = consumo_distribuidoras[(consumo_distribuidoras.index.year >= desde) & (consumo_distribuidoras.index.year <= hasta)].sum()
    return c / c.sum()


def national(temps: pd.DataFrame, w: pd.Series, fn=hdd) -> pd.Series:
    """Índice nacional diario: el grado-día de cada ciudad ponderado por el peso de su distribuidora."""
    comunes = [k for k in temps.columns if k in w.index]
    ww = w[comunes] / w[comunes].sum()
    return (fn(temps[comunes]) * ww).sum(axis=1)


def monthly(daily: pd.Series) -> pd.Series:
    """Suma mensual de un índice diario, con índice en el primer día del mes."""
    m = daily.resample("MS").sum(min_count=20)
    m.index.name = "fecha"
    return m


def climatology(monthly_hdd: pd.Series, desde: int = 1996, hasta: int = 2025) -> pd.DataFrame:
    """Por mes del año, los grados-día de cada año del período: filas = mes (1-12), columnas = año. Base de los escenarios."""
    m = monthly_hdd[(monthly_hdd.index.year >= desde) & (monthly_hdd.index.year <= hasta)]
    return m.groupby([m.index.month, m.index.year]).sum().unstack()


__all__ = ["ARCHIVE", "fetch_city", "hdd", "cdd", "daily_table", "weights", "national", "monthly", "climatology"]
