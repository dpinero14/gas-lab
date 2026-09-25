"""Los modelos, de menor a mayor. Todos reciben la historia hasta el origen y devuelven 12 meses (o `h`).

- `ingenuo`: el mismo mes del año anterior. Es la vara: un modelo que no le gana no sirve.
- `sarima_espana`: SARIMA(0,1,1)(0,1,1)12 sobre el nivel, igual que el trabajo sobre España que
  inspiró el repo. Sin temperatura.
- `sarimax_clima`: el mismo SARIMA sobre el logaritmo, con los grados-día de calefacción y de
  refrigeración del mes como regresores. Necesita la temperatura de los meses a pronosticar: la
  observada (para medir el modelo) o la de un escenario (para pronosticar de verdad).
- `componentes`: cada tipo de usuario con su modelo (los que dependen del frío con grados-día, el
  resto sin clima) y la suma. Captura que las centrales tienen el pico en verano y los hogares en
  invierno.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

ORDEN, ORDEN_EST = (0, 1, 1), (0, 1, 1, 12)
# tipos de usuario que suman el total, y qué regresores de clima usa cada uno
COMPONENTES = {
    "residencial": ("hdd",), "comercial": ("hdd",), "entes_oficiales": ("hdd",), "sdb": ("hdd",),
    "industria": (), "gnc": (), "centrales": ("hdd", "cdd"),
}


def _future_index(y: pd.Series, h: int) -> pd.DatetimeIndex:
    return pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=h, freq="MS")


def ingenuo(y: pd.Series, h: int = 12, **_) -> pd.Series:
    idx = _future_index(y, h)
    return pd.Series([y.get(d - pd.DateOffset(years=1), np.nan) if d - pd.DateOffset(years=1) <= y.index[-1] else np.nan for d in idx], index=idx)


def _fit_sarimax(endog, exog=None):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = SARIMAX(endog, exog=exog, order=ORDEN, seasonal_order=ORDEN_EST, enforce_stationarity=False, enforce_invertibility=False)
        return m.fit(disp=False, maxiter=200)


def sarima_espana(y: pd.Series, h: int = 12, **_) -> pd.Series:
    res = _fit_sarimax(y.astype(float))
    f = res.get_forecast(h).predicted_mean
    f.index = _future_index(y, h)
    return f


def sarimax_clima(y: pd.Series, h: int = 12, clima: pd.DataFrame | None = None, cols: tuple[str, ...] = ("hdd", "cdd"), alpha: float | None = None, **_):
    """log(y) con los grados-día como regresores. `clima` debe cubrir la historia y los `h` meses siguientes.

    Con `alpha`, devuelve también la banda (inferior, superior) del intervalo de confianza.
    """
    idx = _future_index(y, h)
    X = clima[list(cols)].astype(float)
    res = _fit_sarimax(np.log(y.astype(float)), X.loc[y.index])
    fc = res.get_forecast(h, exog=X.loc[idx])
    f = np.exp(fc.predicted_mean); f.index = idx
    if alpha is None:
        return f
    ci = np.exp(fc.conf_int(alpha=alpha)); ci.index = idx
    return f, ci.iloc[:, 0], ci.iloc[:, 1]


def componentes(df: pd.DataFrame, h: int = 12, clima: pd.DataFrame | None = None, **_) -> pd.DataFrame:
    """Un modelo por tipo de usuario (columnas de `df` en COMPONENTES); devuelve cada pronóstico y la suma en 'total'."""
    out = {}
    for comp, cols in COMPONENTES.items():
        y = df[comp].astype(float).clip(lower=0.01)
        if cols:
            out[comp] = sarimax_clima(y, h, clima=clima, cols=cols)
        else:
            res = _fit_sarimax(np.log(y))
            f = np.exp(res.get_forecast(h).predicted_mean); f.index = _future_index(y, h)
            out[comp] = f
    r = pd.DataFrame(out)
    r["total"] = r.sum(axis=1)
    return r


MODELOS = {"ingenuo": ingenuo, "sarima_espana": sarima_espana, "sarimax_clima": sarimax_clima}

__all__ = ["ORDEN", "ORDEN_EST", "COMPONENTES", "ingenuo", "sarima_espana", "sarimax_clima", "componentes", "MODELOS"]
