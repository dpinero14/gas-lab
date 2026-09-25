"""Las figuras de gas-lab, con la paleta de la serie: fondo oscuro, tinta clara, ámbar para lo que importa."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BG, INK, MUTED, RULE = "#0e1b25", "#f2f2f2", "#8fa3b0", "#22333f"
AMBAR, AZUL, GRIS, ROJO, VERDE = "#f2b134", "#3b8ed0", "#6b8799", "#e05a4e", "#4caf50"
FUENTE = "gas-lab · ENARGAS (series mensuales y partes diarios) · temperatura ERA5 (Copernicus, vía Open-Meteo)"


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _style(ax, grid="y"):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9.5, length=0)
    if grid:
        ax.grid(axis=grid, color=RULE, linewidth=0.8, zorder=0)


def _titles(fig, titulo, subtitulo, fuente=FUENTE, x=0.06):
    fig.text(x, 0.94, titulo, color=INK, fontsize=16, fontweight="bold")
    fig.text(x, 0.895, subtitulo, color=MUTED, fontsize=10)
    fig.text(x, 0.025, fuente, color=MUTED, fontsize=8)


def _save(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=BG)
    _plt().close(fig)
    return path


def seasonality(perfil: pd.DataFrame, path) -> Path:
    """Perfil mensual promedio (millones de m³ por día) de residencial, centrales e industria: dos estacionalidades opuestas."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=180)
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.07, right=0.86, top=0.8, bottom=0.12)
    _style(ax)
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    for col, c, nombre in (("residencial", AMBAR, "hogares"), ("centrales", AZUL, "centrales eléctricas"), ("industria", GRIS, "industria"), ("gnc", VERDE, "GNC")):
        ax.plot(range(12), perfil[col].values, color=c, lw=2.8 if col == "residencial" else 2.0, marker="o", ms=4, zorder=3)
        ax.text(11.3, perfil[col].values[-1], nombre, color=c, fontsize=10, va="center")
    ax.axvspan(4.5, 7.5, color="#ffffff", alpha=0.04)
    ax.set_xticks(range(12)); ax.set_xticklabels(meses); ax.set_xlim(-0.3, 12.8)
    ax.set_ylabel("millones de m³ por día, promedio 2021-2026", color=MUTED, fontsize=9.5)
    _titles(fig, "Dos estacionalidades opuestas", "Los hogares consumen seis veces más en julio que en enero; las centrales tienen el pico en verano, por el aire acondicionado.")
    return _save(fig, path)


def redistribution(cambios: pd.DataFrame, path) -> Path:
    """Cambio interanual del consumo de invierno contra el cambio de grados-día: hogares, centrales y total."""
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), dpi=180, sharex=True)
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.06, right=0.98, top=0.76, bottom=0.15, wspace=0.12)
    x = cambios["hdd"].values
    lim = max(abs(cambios[["residencial", "centrales", "total"]].values).max(), 1) * 1.1
    for ax, col, c, nombre in zip(axes, ("residencial", "centrales", "total"), (AMBAR, AZUL, INK), ("Hogares", "Centrales eléctricas", "Total del país")):
        _style(ax, grid="both")
        y = cambios[col].values
        b = np.polyfit(x, y, 1)
        ax.scatter(x, y, s=22, color=c, alpha=0.75, zorder=3, linewidths=0)
        xs = np.linspace(x.min(), x.max(), 10)
        ax.plot(xs, np.polyval(b, xs), color=c, lw=2.2, zorder=4)
        ax.axhline(0, color=RULE, lw=1); ax.axvline(0, color=RULE, lw=1)
        ax.set_ylim(-lim, lim)
        ax.set_title(f"{nombre}: {b[0]:+.1f} por grado-día".replace(".", ","), color=c, fontsize=11.5, loc="left", pad=6)
        ax.set_xlabel("cambio de grados-día del mes contra el mismo mes del año anterior", color=MUTED, fontsize=8.5)
    axes[0].set_ylabel("cambio del consumo del mes, millones de m³", color=MUTED, fontsize=9)
    _titles(fig, "El frío no sube el consumo total: lo redistribuye", "Junio a agosto, 2010-2026. Lo que suman los hogares en un invierno frío lo pierden las centrales y la industria: el total está topeado por el transporte.")
    return _save(fig, path)


def validation(res: dict[str, pd.DataFrame], path) -> Path:
    """Error medio de cada modelo (MAPE del año y del invierno) en el total y en el residencial."""
    plt = _plt()
    fig, axes = plt.subplots(1, len(res), figsize=(12.5, 5.2), dpi=180)
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.2, right=0.97, top=0.76, bottom=0.14, wspace=0.55)
    nombres = {"ingenuo": "ingenuo (mismo mes del año pasado)", "sarima_espana": "SARIMA como el de España", "sarimax_clima_normal": "SARIMAX + clima normal",
               "sarimax_clima_observado": "SARIMAX + clima observado", "componentes_clima_normal": "por tipo de usuario + clima normal",
               "componentes_clima_observado": "por tipo de usuario + clima observado"}
    for ax, (titulo, s) in zip(np.atleast_1d(axes), res.items()):
        _style(ax, grid="x")
        s = s.sort_values("mape", ascending=False)
        y = np.arange(len(s))
        mejor = s["mape"].idxmin()
        ax.barh(y + 0.18, s["mape"], height=0.34, color=[AMBAR if m == mejor else GRIS for m in s.index], zorder=3, label="año")
        ax.barh(y - 0.18, s["mape_invierno"], height=0.34, color=AZUL, alpha=0.8, zorder=3, label="invierno")
        for yi, (a, b) in enumerate(zip(s["mape"], s["mape_invierno"])):
            ax.text(a + 0.15, yi + 0.18, f"{a:.1f} %".replace(".", ","), va="center", color=INK, fontsize=8.5)
            ax.text(b + 0.15, yi - 0.18, f"{b:.1f} %".replace(".", ","), va="center", color=MUTED, fontsize=8.5)
        ax.set_yticks(y); ax.set_yticklabels([nombres.get(m, m) for m in s.index], color=INK, fontsize=9)
        ax.set_title(titulo, color=INK, fontsize=12, loc="left", pad=6)
        ax.set_xlabel("error porcentual medio", color=MUTED, fontsize=9)
    np.atleast_1d(axes)[0].legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower right")
    _titles(fig, "Diez años de pronósticos, antes de cada invierno", "Pronóstico a 12 meses desde el fin de marzo de 2016 a 2025. En ámbar, el mejor de cada serie. Clima observado: si se supiera el tiempo que va a hacer.")
    return _save(fig, path)


def scenarios(hist: pd.Series, esc: pd.DataFrame, abanico: pd.DataFrame, path, anios_clima: dict) -> Path:
    """El residencial de los últimos años y el pronóstico del invierno siguiente con los tres escenarios y el abanico de 29 inviernos."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(12, 5.4), dpi=180)
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.07, right=0.87, top=0.8, bottom=0.12)
    _style(ax)
    h = hist[hist.index >= "2022-01-01"]
    ax.plot(h.index, h.values, color=INK, lw=2, zorder=4)
    lo, hi = abanico.quantile(0.1, axis=1), abanico.quantile(0.9, axis=1)
    ax.fill_between(abanico.index, lo, hi, color=AMBAR, alpha=0.18, zorder=2, linewidth=0)
    for col, c in (("frio", AZUL), ("normal", AMBAR), ("calido", ROJO)):
        ax.plot(esc.index, esc[col], color=c, lw=2.2, zorder=3)
        ax.text(esc.index[-1] + pd.Timedelta(days=20), esc[col].iloc[-1], f"{ {'frio': 'frío', 'normal': 'normal', 'calido': 'cálido'}[col]} (clima de {anios_clima[col]})",
                color=c, fontsize=9.5, va="center")
    ax.axvline(hist.index[-1], color=RULE, lw=1)
    ax.set_ylabel("consumo residencial, millones de m³ por día", color=MUTED, fontsize=9.5)
    _titles(fig, "El invierno que viene, con el tiempo de cada invierno desde 1997",
            "Residencial. Blanco: lo medido. Banda: 80 % de los 29 inviernos posibles. Líneas: un invierno frío (percentil 90), uno normal y uno cálido (percentil 10).")
    return _save(fig, path)


def winters(t: pd.DataFrame, path) -> Path:
    """Cómo se cubrió cada invierno: GNL e importación por el norte (barras) y el máximo de gas propio que entró al sistema (línea)."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(12, 5.4), dpi=180)
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.07, right=0.9, top=0.76, bottom=0.12)
    _style(ax)
    x = t.index.values
    ax.bar(x, t["gnl_mm3"] / 1000, color=AZUL, width=0.65, zorder=3, label="GNL por barco")
    ax.bar(x, t["norte_mm3"].fillna(0) / 1000, bottom=t["gnl_mm3"] / 1000, color=GRIS, width=0.65, zorder=3, label="por el norte: Bolivia y, desde 2025, Norandino")
    for xi, g, n, p in zip(x, t["gnl_mm3"], t["norte_mm3"], t["importado_pct"]):
        txt = "sin dato\ndel norte" if pd.isna(p) else f"{p:.0f} %"
        ax.text(xi, (g + (0 if pd.isna(n) else n)) / 1000 + 0.05, txt, ha="center", color=MUTED if pd.isna(p) else INK, fontsize=8 if pd.isna(p) else 8.5)
    ax.set_ylabel("importado de mayo a septiembre, miles de millones de m³", color=MUTED, fontsize=9.5)
    ax2 = ax.twinx(); _style(ax2, grid=None)
    ax2.plot(x, t["domestico_max"], color=AMBAR, lw=2.6, marker="o", ms=5, zorder=5, label="máximo diario de gas propio (MMm³/d)")
    ax2.set_ylim(100, max(160, t["domestico_max"].max() * 1.05))
    ax2.set_ylabel("máximo diario de gas propio, millones de m³/día", color=AMBAR, fontsize=9.5)
    ax.set_xticks(x); ax.set_xticklabels([str(v) for v in x], color=MUTED)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, labelcolor=INK, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.set_ylim(0, (t["gnl_mm3"] + t["norte_mm3"].fillna(0)).max() / 1000 * 1.12)
    _titles(fig, "Cómo se cubrió cada invierno, 2014 a 2026",
            "Sobre las barras, la parte del gas del invierno que vino de afuera. Antes de 2019 el parte no separa el gas de Bolivia.")
    return _save(fig, path)


def winter_days(w: pd.DataFrame, path, anio: int) -> Path:
    """Un invierno día por día: gas propio, GNL e importación apilados, la demanda prioritaria y el frío."""
    plt = _plt()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.5, 6.4), dpi=180, sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.07, right=0.97, top=0.83, bottom=0.1, hspace=0.08)
    _style(a1); _style(a2)
    x = w.index
    a1.stackplot(x, w["domestico"], w["bolivia"], w["gnl"], colors=[GRIS, "#4a5d6b", AZUL], alpha=0.95, zorder=2, labels=["gas propio", "importación por el norte", "GNL"])
    a1.plot(x, w["prioritaria"], color=AMBAR, lw=2, zorder=4, label="demanda prioritaria (distribuidoras)")
    a1.set_ylabel("millones de m³ por día", color=MUTED, fontsize=9.5)
    a1.legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower left", ncol=4)
    a2.bar(x, w["hdd"], color=AZUL, width=1.0, zorder=3)
    a2.set_ylabel("grados-día", color=MUTED, fontsize=9)
    _titles(fig, f"El invierno {anio}, día por día",
            "Lo que entró al sistema cada día, y de dónde vino. Abajo, el frío del día (grados-día de calefacción, promedio nacional ponderado).")
    return _save(fig, path)


def next_winter(ens: pd.DataFrame, real: dict, path) -> Path:
    """El invierno siguiente con el tiempo de cada invierno histórico: faltante físico nacional (barras) y GNL operando como 2024-2026 (puntos)."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(12, 5.6), dpi=180)
    fig.patch.set_facecolor(BG); fig.subplots_adjust(left=0.07, right=0.97, top=0.76, bottom=0.2)
    _style(ax)
    e = ens.sort_values("hdd_invierno")
    x = np.arange(len(e))
    frios = e["hdd_invierno"] >= e["hdd_invierno"].quantile(0.9)
    ax.bar(x, e["faltante_mm3"] / 1000, color=[AZUL if f else GRIS for f in frios], width=0.7, zorder=3, label="faltante físico nacional (mínimo a cubrir)")
    if "gnl_como_2024_2026" in e:
        ax.plot(x, e["gnl_como_2024_2026"] / 1000, color=AMBAR, lw=0, marker="o", ms=6, zorder=5, label="GNL si se opera como en 2024-2026")
    for k, val in real.items():
        ax.axhline(val / 1000, color=INK, lw=1.2, ls="--", zorder=4)
        ax.text(0, val / 1000, f" GNL que entró en {k}", color=INK, fontsize=9, va="bottom", ha="left")
    ax.set_xticks(x); ax.set_xticklabels([str(a) for a in e.index], rotation=90, fontsize=8, color=MUTED)
    ax.set_xlabel("año del que se toma el tiempo del invierno, del más templado al más frío (en azul, el 10 % más frío)", color=MUTED, fontsize=9)
    ax.set_ylabel("millones de m³ × 1.000, mayo a septiembre", color=MUTED, fontsize=9.5)
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    _titles(fig, "¿Cuánto falta el invierno que viene?",
            "El invierno 2027 con el tiempo de cada invierno desde 1997 y la capacidad de 2026: lo que falta por balance nacional y lo que se importaría operando como hoy.")
    return _save(fig, path)


__all__ = ["seasonality", "redistribution", "validation", "scenarios", "winters", "winter_days", "next_winter"]
