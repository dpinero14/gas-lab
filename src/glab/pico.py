"""El pico diario: ¿alcanza el gas en los días más fríos?

Con los partes diarios del ENARGAS y la temperatura del mismo día:

- `prioritaria`: lo que entregan las distribuidoras (hogares, comercios, GNC y pymes conectadas a
  la red de distribución). Es la demanda que se cubre primero y sube con el frío.
- `directos`: los clientes directos de TGN y TGS (industrias grandes, centrales, by-pass). Es lo
  que se corta cuando no alcanza: baja en los días fríos.
- `doméstico`: la inyección total menos GNL y Bolivia, lo que el país pone con su propio gas.

El modelo del pico se ajusta con los días de invierno de un año reciente: la demanda prioritaria
como recta en los grados-día del día, y la demanda directa "sin cortes" como su nivel en los días
templados del mismo invierno. Con el tiempo diario de cada invierno desde 1997 se arma el abanico
del invierno que viene: cuántos días la demanda supera lo que el sistema pone con gas propio, y
cuánto habría que cubrir con GNL o con cortes.

Lo que no mide: en los días de corte la demanda directa observada es menor que la real (el corte
ya ocurrió). Por eso la demanda directa sin cortes se estima con los días templados, y se declara.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DISTRIB = ["gasnor", "cuyana", "centro", "litoral", "naturgy_ban", "metrogas", "pampeana", "sur", "gasnea"]
DIRECTOS = ["tgn_directo", "tgs_directo"]
# ciudad (clave de glab.CIUDADES) de cada fila del parte real
CIUDAD_DE = {"gasnor": "gasnor", "cuyana": "ecogas_cuyana", "centro": "ecogas_centro", "litoral": "litoral", "naturgy_ban": "naturgy_ban",
             "metrogas": "metrogas", "pampeana": "camuzzi_pampeana", "sur": "camuzzi_sur", "gasnea": "gasnea"}


MESES_EFECTO = (5, 6, 8, 9)     # julio es la referencia
VIDA_MEDIA = 1.5               # días: las casas tardan en enfriarse; el frío de ayer también cuenta


def thermal(hdd_diario: pd.Series, vida_media: float = VIDA_MEDIA) -> pd.Series:
    """Grados-día con inercia: promedio exponencial con vida media de un día y medio."""
    return hdd_diario.ewm(halflife=vida_media).mean()


def daily_frame(partes: pd.DataFrame, hdd_diario: pd.Series) -> pd.DataFrame:
    """Tabla diaria en millones de m³/día: prioritaria, directos, consumo, inyección, GNL, doméstico, y los grados-día (del día y con inercia)."""
    p = partes.set_index(pd.to_datetime(partes["fecha"])).sort_index()
    out = pd.DataFrame(index=p.index)
    out["prioritaria"] = p[[c for c in DISTRIB if c in p]].sum(axis=1, min_count=7) / 1000.0
    out["directos"] = p[[c for c in DIRECTOS if c in p]].sum(axis=1, min_count=2) / 1000.0
    out["consumo"] = p["total_con_propios"] / 1000.0 if "total_con_propios" in p else np.nan
    out["inyeccion"] = p.get("inyeccion_total")
    cero = pd.Series(0.0, index=p.index)
    out["gnl"] = p.get("gnl_escobar_gasandes", cero).fillna(0.0) + p.get("gnl_bahia_blanca", cero).fillna(0.0)
    # antes de 2018 el parte no separa el gas de Bolivia (va dentro de la inyección del gasoducto Norte):
    # queda NaN, no cero, y `norte_informado` dice qué días lo trae
    out["bolivia"] = p.get("bolivia_norandino", pd.Series(np.nan, index=p.index))
    out["norte_informado"] = out["bolivia"].notna()
    # desde 2019 la nota existe pero algunos días el PDF no la imprime; el caudal es estable, se interpola entre días vecinos
    desde19 = out.index >= "2019-01-01"
    out.loc[desde19, "bolivia"] = out.loc[desde19, "bolivia"].interpolate(limit_area="inside")
    out["domestico"] = out["inyeccion"] - out["gnl"] - out["bolivia"].fillna(0.0)
    out["hdd"] = hdd_diario.reindex(out.index)
    out["hdd_termico"] = thermal(hdd_diario).reindex(out.index)
    out["finde"] = out.index.dayofweek >= 5
    return out


def winter(df: pd.DataFrame, anio: int, meses: tuple[int, ...] = (5, 6, 7, 8, 9)) -> pd.DataFrame:
    return df[(df.index.year == anio) & df.index.month.isin(meses)].dropna(subset=["prioritaria", "hdd"])


def _design(hdd_t: np.ndarray, idx: pd.DatetimeIndex) -> np.ndarray:
    cols = [np.ones(len(idx)), hdd_t, (idx.dayofweek >= 5).astype(float)]
    cols += [(idx.month == m).astype(float) for m in MESES_EFECTO]
    return np.column_stack(cols)


def fit_priority(w: pd.DataFrame) -> dict:
    """Demanda prioritaria = base + por_hdd x grados-día con inercia + fin de semana + efecto del mes (julio de referencia)."""
    h = (w["hdd_termico"] if "hdd_termico" in w else w["hdd"]).values
    X = _design(h, w.index)
    b, *_ = np.linalg.lstsq(X, w["prioritaria"].values, rcond=None)
    resid = w["prioritaria"].values - X @ b
    r2 = 1 - (resid ** 2).sum() / ((w["prioritaria"] - w["prioritaria"].mean()) ** 2).sum()
    return {"coef": b, "base": float(b[0]), "por_hdd": float(b[1]), "finde": float(b[2]), "r2": float(r2), "sigma": float(resid.std()), "dias": int(len(w))}


def predict_priority(prio: dict, hdd_t: pd.Series) -> np.ndarray:
    return _design(hdd_t.values, hdd_t.index) @ prio["coef"]


def unconstrained_direct(w: pd.DataFrame, q_hdd: float = 0.25) -> float:
    """Demanda directa sin cortes: la mediana de los días de semana más templados del invierno (cuartil de menos grados-día)."""
    dias = w[~w["finde"]]
    corte = dias["hdd"].quantile(q_hdd)
    return float(dias.loc[dias["hdd"] <= corte, "directos"].median())


def overhead(w: pd.DataFrame) -> float:
    """Lo que la inyección supera al consumo (combustible de compresión, pérdidas, variación de line pack, exportación por el sistema), mediana."""
    return float((w["inyeccion"] - w["consumo"]).median())


def season_gap(hdd_t: pd.Series, prio: dict, directos: float, extra: float, techo: float) -> pd.DataFrame:
    """Para un invierno de grados-día con inercia: demanda total necesaria por día y lo que falta por encima del techo doméstico."""
    prioridad = predict_priority(prio, hdd_t)
    necesaria = prioridad + directos + extra
    falta = np.maximum(0.0, necesaria - techo)
    return pd.DataFrame({"hdd_termico": hdd_t.values, "prioritaria": prioridad, "necesaria": necesaria, "falta": falta}, index=hdd_t.index)


def winter_ensemble(hdd_diario: pd.Series, prio: dict, directos: float, extra: float, techo: float, anios: range, meses: tuple[int, ...] = (5, 6, 7, 8, 9)) -> pd.DataFrame:
    """Una fila por invierno histórico: días con faltante, faltante total (millones de m³), pico de demanda y de faltante."""
    ht = thermal(hdd_diario)
    filas = []
    for a in anios:
        h = ht[(ht.index.year == a) & ht.index.month.isin(meses)]
        if len(h) < 100:
            continue
        g = season_gap(h, prio, directos, extra, techo)
        filas.append({"anio_clima": a, "hdd_invierno": float(hdd_diario[h.index].sum()), "dias_con_faltante": int((g["falta"] > 0).sum()),
                      "faltante_mm3": float(g["falta"].sum()), "pico_necesario": float(g["necesaria"].max()), "pico_faltante": float(g["falta"].max())})
    return pd.DataFrame(filas).set_index("anio_clima")


def gnl_response(D: pd.DataFrame, anios: tuple[int, ...], bordes: tuple[float, ...] = (0, 4, 6, 8, 10, 12, 30), meses: tuple[int, ...] = (5, 6, 7, 8, 9)) -> pd.DataFrame:
    """Cómo se operó: GNL medio por día según el frío (grados-día con inercia), en los inviernos pedidos. Una fila por tramo de frío."""
    w = pd.concat([winter(D, a, meses) for a in anios])
    tramo = pd.cut(w["hdd_termico"], bins=list(bordes), right=False)
    g = w.groupby(tramo, observed=True).agg(dias=("gnl", "size"), gnl_medio=("gnl", "mean"), prob_gnl=("gnl", lambda s: float((s > 0.5).mean())))
    g.index = pd.IntervalIndex(g.index)
    return g


def apply_response(hdd_t: pd.Series, resp: pd.DataFrame) -> pd.Series:
    """GNL esperado por día para una serie de grados-día con inercia, según la tabla de `gnl_response`."""
    out = np.full(len(hdd_t), np.nan)
    for iv, fila in resp.iterrows():
        m = (hdd_t.values >= iv.left) & (hdd_t.values < iv.right)
        out[m] = fila["gnl_medio"]
    return pd.Series(np.nan_to_num(out, nan=float(resp["gnl_medio"].iloc[-1])), index=hdd_t.index)


def gnl_ensemble(hdd_diario: pd.Series, resp: pd.DataFrame, anios: range, meses: tuple[int, ...] = (5, 6, 7, 8, 9)) -> pd.Series:
    """GNL esperado del invierno (millones de m³) con el tiempo de cada invierno histórico, operando como en los años de `resp`."""
    ht = thermal(hdd_diario)
    out = {}
    for a in anios:
        h = ht[(ht.index.year == a) & ht.index.month.isin(meses)]
        if len(h) >= 100:
            out[a] = float(apply_response(h, resp).sum())
    return pd.Series(out, name="gnl_esperado_mm3")


# un buque metanero de 140.000 m³ de GNL trae unos 85 millones de m³ de gas una vez regasificado (1 m³ de GNL ≈ 600 m³ de gas)
M3_POR_BUQUE = 85.0


__all__ = ["DISTRIB", "DIRECTOS", "CIUDAD_DE", "MESES_EFECTO", "VIDA_MEDIA", "thermal", "predict_priority", "daily_frame", "winter", "fit_priority", "unconstrained_direct", "overhead", "season_gap", "winter_ensemble", "gnl_response", "apply_response", "gnl_ensemble", "M3_POR_BUQUE"]
