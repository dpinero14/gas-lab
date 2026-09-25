"""Los escenarios de clima: el mismo modelo, proyectado con el tiempo que hizo cada año desde 1996.

No se inventa un invierno frío: se toma uno que existió. El modelo se ajusta una vez con toda la
historia y se proyecta los próximos 12 meses con los grados-día de 1996, después con los de 1997,
y así con cada año. Sale un abanico de 30 pronósticos; el invierno frío es el percentil 90 del
consumo de junio a agosto, el normal la mediana y el cálido el percentil 10. La incertidumbre del
clima queda separada de la del modelo.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from .modelos import _fit_sarimax, _future_index

INVIERNO = (6, 7, 8)


def weather_exog(clima: pd.DataFrame, idx: pd.DatetimeIndex, anio_clima: int) -> pd.DataFrame:
    """Los regresores de clima de los meses `idx`, tomados del mismo mes del año `anio_clima`.

    El año se alinea con el último del horizonte: el invierno pronosticado recibe el invierno de
    `anio_clima`, y los meses del año anterior, los de `anio_clima - 1`.
    """
    filas = []
    base = idx[-1].year
    for d in idx:
        src = pd.Timestamp(anio_clima + (d.year - base), d.month, 1)
        filas.append(clima.loc[src].values if src in clima.index else [np.nan] * clima.shape[1])
    return pd.DataFrame(filas, index=idx, columns=clima.columns)


def ensemble(y: pd.Series, clima: pd.DataFrame, h: int = 15, anios: range = range(1997, 2026), cols: tuple[str, ...] = ("hdd", "cdd")) -> pd.DataFrame:
    """Pronóstico de `y` para cada año de clima histórico: filas = meses futuros, columnas = año del clima."""
    X = clima[list(cols)].astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = _fit_sarimax(np.log(y.astype(float)), X.loc[y.index])
    idx = _future_index(y, h)
    out = {}
    for a in anios:
        ex = weather_exog(X, idx, a)
        if ex.isna().any().any():
            continue
        f = np.exp(res.get_forecast(h, exog=ex).predicted_mean)
        f.index = idx
        out[a] = f
    return pd.DataFrame(out)


def winter_scenarios(ens: pd.DataFrame, q_frio: float = 0.9, q_calido: float = 0.1, anio_invierno: int | None = None) -> pd.DataFrame:
    """Tres escenarios a partir del abanico: el año de clima cuyo total de invierno es el percentil frío, la mediana y el cálido.

    El invierno que decide es el de `anio_invierno` (por defecto, el último año del horizonte).
    """
    anio_invierno = anio_invierno or int(ens.index[-1].year)
    m = ens.index.month.isin(INVIERNO) & (ens.index.year == anio_invierno)
    inv = ens[m].sum()
    elegir = {}
    for nombre, q in (("frio", q_frio), ("normal", 0.5), ("calido", q_calido)):
        objetivo = inv.quantile(q)
        elegir[nombre] = int((inv - objetivo).abs().idxmin())
    t = pd.DataFrame({n: ens[a] for n, a in elegir.items()})
    t.attrs["anio_clima"] = elegir
    return t


__all__ = ["INVIERNO", "weather_exog", "ensemble", "winter_scenarios"]
