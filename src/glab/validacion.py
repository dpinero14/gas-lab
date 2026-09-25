"""La validación: pronóstico a 12 meses desde el fin de marzo de cada año, antes de cada invierno.

Para cada año de origen se entrena con todo lo anterior y se pronostica de abril a marzo. Los
modelos con temperatura se miden de dos maneras, porque son dos preguntas distintas:

- con el clima observado: cuánto se equivoca el modelo si supiera el tiempo que va a hacer
  (mide el modelo);
- con el clima normal: los grados-día de cada mes reemplazados por el promedio de los 20 años
  anteriores al origen (mide el pronóstico real, que no sabe si el invierno va a ser frío).

Las métricas: error porcentual medio del año (MAPE), el del invierno (junio a agosto) y el error
del total del invierno, que es lo que importa para saber cuánto gas hace falta.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .modelos import componentes, ingenuo, sarima_espana, sarimax_clima

INVIERNO = (6, 7, 8)


def climate_normal(clima: pd.DataFrame, origen: pd.Timestamp, idx: pd.DatetimeIndex, anios: int = 20) -> pd.DataFrame:
    """Clima de los meses `idx` reemplazado por el promedio del mismo mes en los `anios` años anteriores al origen."""
    hist = clima[(clima.index < origen) & (clima.index >= origen - pd.DateOffset(years=anios))]
    prom = hist.groupby(hist.index.month).mean()
    out = clima.copy()
    for d in idx:
        out.loc[d] = prom.loc[d.month].values
    return out


def metrics(real: pd.Series, pred: pd.Series) -> dict:
    e = (pred - real) / real
    inv = real.index.month.isin(INVIERNO)
    return {"mape": float(100 * e.abs().mean()), "mape_invierno": float(100 * e[inv].abs().mean()),
            "error_total_invierno": float(100 * (pred[inv].sum() / real[inv].sum() - 1)), "error_total_anio": float(100 * (pred.sum() / real.sum() - 1))}


def backtest(df: pd.DataFrame, clima: pd.DataFrame, origenes: range = range(2016, 2026), mes_origen: int = 3, h: int = 12, col: str = "total") -> pd.DataFrame:
    """Una fila por año de origen y modelo, con las métricas. `df` son las series mensuales; `clima` tiene hdd y cdd por mes."""
    filas = []
    for anio in origenes:
        origen = pd.Timestamp(anio, mes_origen, 1)
        hist = df[df.index <= origen]
        idx = pd.date_range(origen + pd.offsets.MonthBegin(1), periods=h, freq="MS")
        if idx[-1] > df.index[-1]:
            continue
        real = df.loc[idx, col]
        normal = climate_normal(clima, idx[0], idx)
        preds = {"ingenuo": ingenuo(hist[col], h), "sarima_espana": sarima_espana(hist[col], h),
                 "sarimax_clima_observado": sarimax_clima(hist[col], h, clima=clima), "sarimax_clima_normal": sarimax_clima(hist[col], h, clima=normal)}
        if col == "total":
            preds["componentes_clima_observado"] = componentes(hist, h, clima=clima)["total"]
            preds["componentes_clima_normal"] = componentes(hist, h, clima=normal)["total"]
        for nombre, p in preds.items():
            filas.append({"origen": anio, "modelo": nombre, **metrics(real, p.reindex(idx))})
    return pd.DataFrame(filas)


def summary(bt: pd.DataFrame) -> pd.DataFrame:
    """Promedio por modelo del error absoluto de cada métrica, ordenado por el MAPE de invierno."""
    g = bt.groupby("modelo").agg(mape=("mape", "mean"), mape_invierno=("mape_invierno", "mean"),
                                 error_invierno_abs=("error_total_invierno", lambda s: s.abs().mean()),
                                 error_invierno_max=("error_total_invierno", lambda s: s.abs().max()), anios=("origen", "nunique"))
    return g.sort_values("mape_invierno")


__all__ = ["INVIERNO", "climate_normal", "metrics", "backtest", "summary"]
