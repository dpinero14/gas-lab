import numpy as np
import pandas as pd

from glab.clima import climatology, hdd, monthly, national
from glab.escenarios import ensemble, weather_exog, winter_scenarios
from glab.modelos import ingenuo, sarimax_clima
from glab.partes import parse_real, parse_transporte
from glab.pico import fit_priority, season_gap, thermal, unconstrained_direct, winter_ensemble
from glab.series import annual, per_day
from glab.validacion import climate_normal, metrics

REAL = """REPUBLICA ARGENTINA: GAS NATURAL DISTRIBUIDO
GasNor 3220 5683 4844 4600
Cuyana 7290 10227 9614 10299
Centro 8180 8976 8580 9138
Litoral 7560 7581 7581 7900
NaturgyBan 15860 20026 19894 16150
MetroGas 17100 25895 23590 16322
Pampeana 16630 19361 19195 21049
Sur (2) 16720 19110 17873 18658
GasNea 1490 1460 1457 1331
TGN Directo (3) 11210 22668 14274 14419
TGS Directo (4) 16850 16860 16560 16606
122110 157847 143462 136472
SUR(6) 3530 3478 3478 6996
125640 161325 146940 143468
"""
TRANS = """Inyección Total (e) 159.0 (b)Incluye GPM (22.7) 351.9 -11.5
(a)Incluye inyección de Bolivia y Norandino (1.9) Line Pack
(d)Incluye inyección de GNL Escobar y Gasandes (19.7) (3) Pe
Máxima: 10.3
Mínima: 1.8
"""


def _mensual(n=120, seed=0, clima=True):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2010-01-01", periods=n, freq="MS")
    h = 200 + 180 * np.cos(2 * np.pi * (idx.month - 7) / 12) + rng.normal(0, 15, n)
    h = np.clip(h, 0, None)
    y = pd.Series(300 + 3.0 * h + rng.normal(0, 10, n), index=idx)
    c = pd.DataFrame({"hdd": h, "cdd": np.clip(50 - h / 5, 0, None)}, index=idx)
    return y, c


def test_parte_real_suma_el_total():
    r = parse_real(REAL)
    filas = ["gasnor", "cuyana", "centro", "litoral", "naturgy_ban", "metrogas", "pampeana", "sur", "gasnea", "tgn_directo", "tgs_directo"]
    assert all(k in r for k in filas)
    assert sum(r[k] for k in filas) == r["total_sistema"] == 136472
    assert r["total_con_propios"] == 143468 and r["sur"] == 18658


def test_parte_transporte():
    t = parse_transporte(TRANS)
    assert t["inyeccion_total"] == 159.0 and t["gnl_escobar_gasandes"] == 19.7 and t["gpm"] == 22.7 and t["bolivia_norandino"] == 1.9
    assert t["tmax_pronostico_caba"] == 10.3 and t["tmin_pronostico_caba"] == 1.8


def test_grados_dia_y_nacional():
    t = pd.DataFrame({"a": [10.0, 20.0, 18.0], "b": [0.0, 18.0, 30.0]}, index=pd.date_range("2020-01-01", periods=3))
    assert list(hdd(t["a"])) == [8.0, 0.0, 0.0]
    n = national(t, pd.Series({"a": 3.0, "b": 1.0}))
    assert np.allclose(n.values, [0.75 * 8 + 0.25 * 18, 0.0, 0.0])
    m = monthly(pd.Series(1.0, index=pd.date_range("2020-01-01", "2020-02-29")))
    assert list(m.values) == [31.0, 29.0]
    cl = climatology(pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2020-01-01", "2021-01-01", "2021-02-01"])), 2020, 2021)
    assert cl.loc[1, 2021] == 2.0 and np.isnan(cl.loc[2, 2020])


def test_series_por_dia_y_anual():
    idx = pd.date_range("2020-01-01", periods=14, freq="MS")
    df = pd.DataFrame({"x": 31.0}, index=idx)
    assert per_day(df).loc["2020-01-01", "x"] == 1.0 and per_day(df).loc["2020-02-01", "x"] == 31 / 29
    a = annual(df)
    assert list(a.index) == [2020] and a.loc[2020, "x"] == 31 * 12


def test_ingenuo_y_metricas():
    y, _ = _mensual()
    f = ingenuo(y, 12)
    assert f.index[0] == y.index[-1] + pd.offsets.MonthBegin(1) and f.iloc[0] == y.iloc[-12]
    real = pd.Series(100.0, index=pd.date_range("2021-01-01", periods=12, freq="MS"))
    m = metrics(real, real * 1.1)
    assert abs(m["mape"] - 10) < 1e-9 and abs(m["error_total_invierno"] - 10) < 1e-9


def test_clima_normal_no_mira_el_futuro():
    _, c = _mensual()
    idx = pd.date_range("2018-01-01", periods=12, freq="MS")
    n = climate_normal(c, idx[0], idx, anios=5)
    esperado = c[(c.index < "2018-01-01") & (c.index >= "2013-01-01")].groupby(lambda d: d.month)["hdd"].mean()
    assert np.allclose(n.loc[idx, "hdd"].values, esperado.loc[idx.month].values)


def test_sarimax_aprende_el_frio():
    y, c = _mensual(160)
    hist = y.iloc[:-12]
    frio = c.copy(); frio.loc[y.index[-12:], "hdd"] += 60     # un año más frío
    f_normal = sarimax_clima(hist, 12, clima=c)
    f_frio = sarimax_clima(hist, 12, clima=frio)
    assert (f_frio > f_normal).all()


def test_escenarios_ordenados():
    y, c = _mensual(200)
    c = c.reindex(pd.date_range(c.index[0], periods=260, freq="MS"))
    c = c.fillna(c.groupby(c.index.month).transform("mean"))
    e = ensemble(y.iloc[:150], c, h=15, anios=range(2014, 2028))
    s = winter_scenarios(e)
    inv = s[s.index.month.isin([6, 7, 8]) & (s.index.year == s.index[-1].year)].sum()
    assert inv["frio"] >= inv["normal"] >= inv["calido"]
    ex = weather_exog(c, pd.date_range("2023-07-01", periods=15, freq="MS"), 2015)
    assert ex.index[-1].year == 2024 and np.isclose(ex.iloc[-1]["hdd"], c.loc["2015-09-01", "hdd"])


def test_pico_diario():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2025-05-01", "2025-09-30")
    h = np.clip(8 + 6 * np.sin(np.linspace(0, np.pi, len(idx))) + rng.normal(0, 2, len(idx)), 0, None)
    w = pd.DataFrame({"hdd": h, "finde": idx.dayofweek >= 5}, index=idx)
    w["prioritaria"] = 40 + 5 * w["hdd"] - 3 * w["finde"] + rng.normal(0, 1, len(idx))
    w["directos"] = 35 - 0.8 * np.clip(w["hdd"] - 10, 0, None)          # se corta en los días fríos
    p = fit_priority(w)
    assert abs(p["por_hdd"] - 5) < 0.2 and p["r2"] > 0.95
    assert unconstrained_direct(w) > w["directos"].min()
    g = season_gap(pd.Series(h, index=idx), p, 35.0, 5.0, techo=120.0)          # sin columna de inercia, usa el grado-día del día
    assert (g["falta"] >= 0).all() and np.isclose(g["falta"].sum(), np.maximum(0, g["necesaria"] - 120).sum())
    e = winter_ensemble(pd.Series(h, index=idx), p, 35.0, 5.0, 120.0, range(2025, 2026))
    g2 = season_gap(thermal(pd.Series(h, index=idx)), p, 35.0, 5.0, techo=120.0)
    assert e.loc[2025, "dias_con_faltante"] == int((g2["falta"] > 0).sum())


def test_red_demanda_suma_el_parte():
    from glab import red
    parte = {"gasnor": 4836.0, "cuyana": 10632.0, "centro": 9813.0, "litoral": 8320.0, "naturgy_ban": 18024.0, "metrogas": 22866.0,
             "pampeana": 22135.0, "sur": 18637.0, "gasnea": 1441.0, "tgn_directo": 13035.0, "tgs_directo": 17525.0, "total_sistema": 147264.0}
    d = red.demanda_del_dia(parte, exportacion=0.0)
    assert abs(d.sum() - parte["total_sistema"] / 1000) < 0.01
    assert d["GBA"] > d["CORDOBA"] > d["NOA"] > d["NEA"]


def test_red_flujo_maximo_reproduce_el_cuello():
    from glab import red
    parte = {"gasnor": 4836.0, "cuyana": 10632.0, "centro": 9813.0, "litoral": 8320.0, "naturgy_ban": 18024.0, "metrogas": 22866.0,
             "pampeana": 22135.0, "sur": 18637.0, "gasnea": 1441.0, "tgn_directo": 13035.0, "tgs_directo": 17525.0}
    dem = red.demanda_del_dia(parte, exportacion=1.0)
    prod = {"neuquina": 122.2, "austral": 25.2, "gsj": 7.9, "noroeste": 2.65}
    con = red.flujo_maximo(red.grafo(), red.oferta_del_dia(prod, gnl=20.3, bolivia=1.9), dem)
    sin = red.flujo_maximo(red.grafo(), red.oferta_del_dia(prod, gnl=0.0, bolivia=0.0), dem)
    # con el GNL de ese día el sistema entrega casi todo; sin él, el faltante es del orden del GNL que entró
    assert con["faltante"].sum() < 3.0
    assert 15.0 < sin["faltante"].sum() < 25.0
    assert sin["faltante"]["GBA"] > 10.0
    # el gas de Neuquén que no sale es por caño, no por producción
    assert sin["usado"]["NEUQUINA"] < prod["neuquina"] - 15
    # un caño infinito desde Neuquén hace desaparecer el faltante
    libre = red.flujo_maximo(red.grafo(capacidades={("NEUQUINA", "ORDOQUI"): 99.0, ("ORDOQUI", "GBA"): 99.0, ("NEUQUINA", "PUELEN"): 99.0,
                                                    ("PUELEN", "LA_MORA"): 99.0, ("LA_MORA", "BEAZLEY"): 99.0, ("BEAZLEY", "LA_CARLOTA"): 99.0, ("LA_CARLOTA", "SAN_JERONIMO"): 99.0,
                                                    ("LA_CARLOTA", "TIO_PUJIO"): 99.0, ("TIO_PUJIO", "FERREYRA"): 99.0, ("FERREYRA", "TUCUMAN"): 99.0}),
                             red.oferta_del_dia(prod, gnl=0.0, bolivia=0.0), dem)
    assert libre["faltante"].sum() < 1.0
    # las obras suman capacidad, nunca la restan
    for o in red.OBRAS:
        r = red.flujo_maximo(red.grafo([o]), red.oferta_del_dia(prod, gnl=0.0, bolivia=0.0), dem)
        assert r["faltante"].sum() <= sin["faltante"].sum() + 1e-6


def test_red_invierno_y_balance():
    import pandas as pd
    from glab import red
    base = {"gasnor": 4836.0, "cuyana": 10632.0, "centro": 9813.0, "litoral": 8320.0, "naturgy_ban": 18024.0, "metrogas": 22866.0,
            "pampeana": 22135.0, "sur": 18637.0, "gasnea": 1441.0, "tgn_directo": 13035.0, "tgs_directo": 17525.0, "gnl_escobar_gasandes": 20.0}
    partes = [{**base, "fecha": f"2026-07-{d:02d}"} for d in (1, 2, 3)] + [{**{k: v * 0.7 for k, v in base.items()}, "fecha": "2026-07-04"}]
    prod = pd.DataFrame({"neuquina": [122.0], "austral": [25.0], "gsj": [8.0], "noroeste": [2.6]}, index=pd.to_datetime(["2026-07-01"]))
    t = red.faltante_invierno(partes, prod, [])
    assert len(t) == 4 and t["faltante"].iloc[:3].gt(10).all() and t["faltante"].iloc[3] < 1.0
    b = red.balance_obras(partes, prod, {"hoy": [], "gpm35": ["gpm35"]}, {"gpm35": 780})
    assert b.loc["gpm35", "gnl_minimo_mmm3"] < b.loc["hoy", "gnl_minimo_mmm3"]
    assert b.loc["gpm35", "inviernos_para_pagarse"] > 0
