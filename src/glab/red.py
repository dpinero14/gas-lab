"""La red troncal de gas como un problema de flujo: de dónde sale el gas, por qué caño pasa y a quién no le llega.

Un grafo simplificado del sistema de transporte: las cinco cuencas y las dos entradas de importación
como orígenes, las plantas compresoras como nodos de paso, y las áreas de las distribuidoras y los
usuarios directos como destinos. Cada arco lleva la capacidad operativa del tramo entre compresoras
que publica el ENARGAS en su informe anual (tabla "Capacidad de inyección total por gasoducto y
capacidad operativa de transporte por tramos", 2025), en millones de m³ por día de 9.300 kcal.
Donde el invierno 2026 mostró más flujo que la capacidad nominal (Centro Oeste en cabecera, Perito
Moreno), se usa lo observado y se declara.

El flujo máximo desde las cuencas hasta la demanda de un día dice cuánto gas puede llegar a cada
destino con la red de hoy. La diferencia con lo que ese día se pidió es el faltante por transporte,
y los arcos saturados del corte mínimo son el cuello. Las obras se evalúan sumando capacidad a los
arcos y volviendo a correr.

Simplificaciones que hay que tener presentes:
- Un nodo por área de distribución; los usuarios directos de cada transportista se reparten entre
  nodos con proporciones fijas (REPARTO_DIRECTOS), porque el parte diario no dice dónde están.
- Camuzzi Sur se parte en dos: lo que se abastece en la cuenca (Neuquén, Río Negro, La Pampa) y lo
  que va por el San Martín (Chubut, Santa Cruz, Tierra del Fuego).
- No hay pérdidas ni combustible de compresoras (2 a 4 % del gas transportado) ni consumos en boca
  de pozo ("propios"): se compara contra el total del sistema sin propios.
- Las exportaciones a Chile se tratan como una demanda más, con el valor que se le pase.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import pandas as pd

# Nodos: (lon, lat). Las compresoras, de la capa "Plantas compresoras de transporte" del ENARGAS.
NODOS: dict[str, tuple[float, float]] = {
    # orígenes
    "NEUQUINA": (-68.59, -38.50), "AUSTRAL": (-68.43, -52.33), "GOLFO_SJ": (-67.94, -46.66),
    "NOROESTE": (-63.82, -22.76), "BOLIVIA": (-63.70, -22.10), "ESCOBAR": (-58.75, -34.35), "BAHIA_GNL": (-62.30, -38.80),
    # TGS
    "CERRI": (-62.40, -38.69), "SATURNO": (-62.66, -36.85), "ORDOQUI": (-61.15, -35.87), "OLAVARRIA": (-60.24, -36.90),
    "INDIO_RICO": (-61.02, -38.24), "BARKER": (-59.49, -37.56), "BUCHANAN": (-58.28, -35.02), "PICO_TRUNCADO": (-67.94, -46.66),
    # TGN
    "PUELEN": (-67.74, -37.56), "LA_MORA": (-66.83, -35.10), "BEAZLEY": (-66.65, -33.80), "LA_CARLOTA": (-63.56, -33.32),
    "SAN_JERONIMO": (-61.08, -32.87), "TIO_PUJIO": (-63.29, -32.29), "FERREYRA": (-63.97, -31.48), "TUCUMAN": (-65.14, -26.85),
    "LUMBRERAS": (-64.94, -25.21),
    # destinos
    "GBA": (-58.45, -34.60), "BAHIA_BLANCA": (-62.27, -38.72), "PAMPEANA_INT": (-59.00, -36.60), "PATAGONIA": (-66.60, -44.70),
    "SUR_CUENCA": (-67.50, -39.40), "MENDOZA": (-68.80, -32.90), "CORDOBA": (-64.18, -31.42), "SANTA_FE": (-60.70, -32.90),
    "NOA": (-65.20, -26.80), "NEA": (-59.00, -27.45), "CHILE": (-70.60, -33.50),
}

# Arcos: (origen, destino, capacidad MMm³/d, gasoducto, fuente). Capacidad operativa por tramo del
# ENARGAS 2025 salvo que se indique "obs. 2026" (observado en los partes o en GRT del invierno 2026).
ARCOS: list[tuple[str, str, float, str, str]] = [
    # --- TGS: de Neuquén a Bahía Blanca y Buenos Aires
    ("NEUQUINA", "CERRI", 9.6, "Neuba I", "Gaviotas–General Cerri 9,56"),
    ("NEUQUINA", "CERRI", 28.5, "Neuba II", "Belisle–La Adela 28,45"),
    ("NEUQUINA", "ORDOQUI", 24.0, "Perito Moreno", "obs. 2026: máximo diario 24,0 (nominal 21)"),
    ("CERRI", "SATURNO", 38.8, "Neuba II finales", "General Cerri–Saturno 38,75"),
    ("SATURNO", "ORDOQUI", 37.1, "Neuba II finales", "Saturno–Ordoqui 37,14"),
    ("ORDOQUI", "GBA", 30.1, "Neuba II finales", "Ordoqui–General Las Heras 30,06"),
    ("CERRI", "OLAVARRIA", 9.4, "Neuba I finales", "Indio Rico–Olavarría 9,44"),
    ("OLAVARRIA", "GBA", 8.9, "Neuba I finales", "Olavarría–General Las Heras 8,87"),
    ("OLAVARRIA", "PAMPEANA_INT", 9.4, "Neuba I finales", "entregas en el interior bonaerense"),
    ("CERRI", "INDIO_RICO", 24.4, "San Martín finales", "General Cerri–Indio Rico 24,40"),
    ("INDIO_RICO", "BARKER", 13.6, "San Martín finales", "Indio Rico–Barker 13,61"),
    ("BARKER", "PAMPEANA_INT", 13.6, "San Martín finales", "Mar del Plata y el sudeste"),
    ("BARKER", "BUCHANAN", 8.7, "San Martín finales", "Barker–Buchanan 8,68"),
    ("BUCHANAN", "GBA", 48.9, "Anillo GBA", "Anillo Gran Buenos Aires 48,92"),
    ("CERRI", "BAHIA_BLANCA", 99.0, "local", "entregas en Bahía Blanca"),
    # --- TGS: el San Martín, del sur
    ("AUSTRAL", "PICO_TRUNCADO", 27.9, "San Martín", "San Sebastián–Magallanes 27,88"),
    ("GOLFO_SJ", "PICO_TRUNCADO", 37.2, "San Martín", "inyección en Pico Truncado"),
    ("PICO_TRUNCADO", "PATAGONIA", 99.0, "local", "entregas en Chubut, Santa Cruz y Tierra del Fuego"),
    ("PICO_TRUNCADO", "CERRI", 29.0, "San Martín", "Río Colorado–General Cerri 29,01"),
    # --- TGS: lo que se abastece en la cuenca
    ("NEUQUINA", "SUR_CUENCA", 99.0, "local", "Neuquén, Río Negro y La Pampa: Cordillerano, Huincul y regionales"),
    # --- TGN: Centro Oeste
    ("NEUQUINA", "PUELEN", 36.8, "Centro Oeste", "obs. 2026: recibido jun-ago 36,8 (nominal 34,1)"),
    ("PUELEN", "LA_MORA", 36.8, "Centro Oeste", "obs. 2026: 36,8 en cabecera (tabla ENARGAS 33,4 Cochicó–La Mora)"),
    ("LA_MORA", "MENDOZA", 99.0, "local", "entregas a Cuyana"),
    ("LA_MORA", "BEAZLEY", 27.2, "Centro Oeste", "La Mora–Beazley 27,18"),
    # La tabla del ENARGAS da 17,5 para Beazley–Chaján, pero es un flujo de diseño con 9 de exportación a
    # Chile saliendo en La Mora. En invierno Chile se corta y el 3/7/2026 pasaron al menos 25 hacia el este
    # (36,8 recibidos menos 11,9 entregados en Cuyo). Se usa lo observado.
    ("BEAZLEY", "LA_CARLOTA", 25.0, "Centro Oeste", "obs. 2026: ≥ 25 (tabla ENARGAS 17,5 con exportación a Chile)"),
    ("LA_CARLOTA", "CORDOBA", 99.0, "local", "entregas a Ecogas Centro por La Carlota y Baldissera"),
    ("LA_CARLOTA", "SAN_JERONIMO", 16.6, "Centro Oeste", "Baldissera–San Jerónimo 16,55"),
    ("SAN_JERONIMO", "SANTA_FE", 99.0, "local", "entregas a Litoral"),
    ("SAN_JERONIMO", "NEA", 7.9, "Centro Oeste", "San Jerónimo–Aldea Brasilera 7,91 (GNEA)"),
    ("SAN_JERONIMO", "GBA", 18.5, "TGN finales", "Nodo San Jerónimo–Buenos Aires 18,53"),
    # --- TGN: Norte, de Salta hacia el sur
    ("NOROESTE", "LUMBRERAS", 24.7, "Norte", "Miraflores–Lumbreras 24,69"),
    ("LUMBRERAS", "TUCUMAN", 21.0, "Norte", "Lumbreras–Tucumán 21,00"),
    ("TUCUMAN", "NOA", 99.0, "local", "entregas a Gasnor"),
    ("TUCUMAN", "FERREYRA", 14.8, "Norte", "Deán Funes–Ferreyra 14,76"),
    ("FERREYRA", "CORDOBA", 99.0, "local", "entregas a Ecogas Centro por Deán Funes y Ferreyra"),
    ("FERREYRA", "TIO_PUJIO", 13.4, "Norte", "Ferreyra–Tío Pujio 13,42"),
    ("TIO_PUJIO", "SAN_JERONIMO", 9.3, "Norte", "Leones–San Jerónimo 9,27"),
    # --- la reversión del Norte (2024): gas de Neuquén hacia el NOA
    ("LA_CARLOTA", "TIO_PUJIO", 15.0, "Reversión Norte", "ducto La Carlota–Tío Pujio, 15 sin las 4 compresoras (19 con ellas)"),
    ("TIO_PUJIO", "FERREYRA", 15.0, "Reversión Norte", "sentido norte"),
    ("FERREYRA", "TUCUMAN", 15.0, "Reversión Norte", "sentido norte"),
    # --- importación
    ("ESCOBAR", "GBA", 22.0, "GNL Escobar", "buque regasificador; obs. 2026 máximo 21,0"),
    ("BAHIA_GNL", "CERRI", 0.0, "GNL Bahía Blanca", "sin buque en 2026"),
    ("BOLIVIA", "NOROESTE", 5.6, "Bolivia", "obs. 2026 máximo 5,6; sin contrato firme"),
    # --- exportación
    ("LA_MORA", "CHILE", 9.0, "GasAndes", "Papagayos; interrumpible en invierno"),
    ("NEUQUINA", "CHILE", 3.5, "Gas Pacífico", "interrumpible en invierno"),
]

DESTINOS = ["GBA", "BAHIA_BLANCA", "PAMPEANA_INT", "PATAGONIA", "SUR_CUENCA", "MENDOZA", "CORDOBA", "SANTA_FE", "NOA", "NEA", "CHILE"]
ORIGENES = ["NEUQUINA", "AUSTRAL", "GOLFO_SJ", "NOROESTE", "BOLIVIA", "ESCOBAR", "BAHIA_GNL"]

# Cómo se reparten los usuarios directos de cada transportista entre nodos (supuesto declarado).
REPARTO_DIRECTOS = {
    "tgs_directo": {"GBA": 0.45, "BAHIA_BLANCA": 0.35, "PAMPEANA_INT": 0.10, "PATAGONIA": 0.10},
    "tgn_directo": {"GBA": 0.45, "CORDOBA": 0.20, "SANTA_FE": 0.25, "MENDOZA": 0.10},
}
REPARTO_SUR = {"SUR_CUENCA": 0.55, "PATAGONIA": 0.45}
REPARTO_PAMPEANA = {"BAHIA_BLANCA": 0.40, "PAMPEANA_INT": 0.60}


def demanda_del_dia(parte: dict, exportacion: float = 0.0, escala_distribuidoras: float = 1.0) -> pd.Series:
    """Demanda por nodo (MMm³/d) a partir de un parte "real" parseado (miles de m³)."""
    k = escala_distribuidoras / 1000.0
    d = {n: 0.0 for n in DESTINOS}
    d["GBA"] += (parte["metrogas"] + parte["naturgy_ban"]) * k
    for n, f in REPARTO_PAMPEANA.items():
        d[n] += parte["pampeana"] * k * f
    for n, f in REPARTO_SUR.items():
        d[n] += parte["sur"] * k * f
    d["MENDOZA"] += parte["cuyana"] * k
    d["CORDOBA"] += parte["centro"] * k
    d["SANTA_FE"] += parte["litoral"] * k
    d["NOA"] += parte["gasnor"] * k
    d["NEA"] += parte["gasnea"] * k
    for campo, rep in REPARTO_DIRECTOS.items():
        for n, f in rep.items():
            d[n] += parte[campo] / 1000.0 * f
    d["CHILE"] = exportacion
    return pd.Series(d, name="demanda")


def oferta_del_dia(produccion: dict[str, float], gnl: float, bolivia: float) -> pd.Series:
    """Oferta por origen (MMm³/d): producción por cuenca del mes, GNL y Bolivia del día."""
    return pd.Series({"NEUQUINA": produccion["neuquina"], "AUSTRAL": produccion["austral"], "GOLFO_SJ": produccion["gsj"],
                      "NOROESTE": produccion["noroeste"], "BOLIVIA": bolivia, "ESCOBAR": gnl, "BAHIA_GNL": 0.0}, name="oferta")


@dataclass
class Obra:
    nombre: str
    arcos_mas: dict[tuple[str, str], float] = field(default_factory=dict)   # capacidad que suma a arcos existentes
    arcos_nuevos: list[tuple[str, str, float, str, str]] = field(default_factory=list)
    costo_musd: float | None = None
    anio: int | None = None
    fuente: str = ""


OBRAS: dict[str, Obra] = {
    "gpm35": Obra("Perito Moreno 21 → 35 y su salida a Buenos Aires", {("NEUQUINA", "ORDOQUI"): 14.0, ("ORDOQUI", "GBA"): 12.0}, costo_musd=780, anio=2027,
                  fuente="TGS, RIGI Res. 676/2026: 3 compresoras en La Pampa, +14 (1/4/2027); concurso TGS 01/2026: +12 de Salliqueló al GBA"),
    "norte19": Obra("Compresoras del Norte, 15 → 19", {("LA_CARLOTA", "TIO_PUJIO"): 4.0, ("TIO_PUJIO", "FERREYRA"): 4.0, ("FERREYRA", "TUCUMAN"): 4.0},
                    costo_musd=None, anio=None, fuente="Enarsa: Lavalle, Lumbreras, Deán Funes y Ferreyra; paralizada (Esuco)"),
    "tlc": Obra("Tratayén–La Carlota, 13", arcos_nuevos=[("NEUQUINA", "LA_CARLOTA", 13.0, "Manuel Belgrano", "TGN: 753 km, 13 MMm³/d, abril 2029")],
                costo_musd=1500, anio=2029, fuente="TGN 17/9/2026"),
    "tgn14": Obra("Loops y compresión TGN, +14", {("LA_CARLOTA", "SAN_JERONIMO"): 8.0, ("SAN_JERONIMO", "GBA"): 6.0, ("TIO_PUJIO", "FERREYRA"): 6.0, ("FERREYRA", "TUCUMAN"): 6.0},
                  costo_musd=700, anio=2029, fuente="TGN: 147 km de loops y 71.000 HP; el reparto entre tramos es un supuesto"),
    "gnk2": Obra("Kirchner etapa 2, Salliqueló–San Jerónimo", arcos_nuevos=[("ORDOQUI", "SAN_JERONIMO", 21.0, "GPM etapa 2", "proyectado, sin fecha; capacidad igual a la etapa 1")],
                 costo_musd=None, anio=None, fuente="capa 'ductos proyectados' de la Secretaría de Energía"),
    "escobar2": Obra("Segundo buque regasificador", {("ESCOBAR", "GBA"): 15.0}, costo_musd=None, anio=None, fuente="alternativa sin caños"),
}


def grafo(obras: list[str] = (), capacidades: dict[tuple[str, str], float] | None = None) -> nx.DiGraph:
    """La red con las obras aplicadas. Arcos paralelos se suman en uno solo."""
    g = nx.DiGraph()
    for n, (lon, lat) in NODOS.items():
        g.add_node(n, lon=lon, lat=lat)
    arcos = list(ARCOS)
    for o in obras:
        arcos += OBRAS[o].arcos_nuevos
    for u, v, cap, gto, fuente in arcos:
        if g.has_edge(u, v):
            g[u][v]["cap"] += cap
            g[u][v]["gasoducto"] += " + " + gto
        else:
            g.add_edge(u, v, cap=cap, gasoducto=gto, fuente=fuente)
    for o in obras:
        for (u, v), mas in OBRAS[o].arcos_mas.items():
            g[u][v]["cap"] += mas
    for (u, v), cap in (capacidades or {}).items():
        g[u][v]["cap"] = cap
    return g


def flujo_maximo(g: nx.DiGraph, oferta: pd.Series, demanda: pd.Series) -> dict:
    """Cuánto gas llega a cada destino con esta red, y qué arcos saturan."""
    h = g.copy()
    for n, q in oferta.items():
        h.add_edge("_S", n, cap=float(q))
    for n, q in demanda.items():
        h.add_edge(n, "_T", cap=float(q))
    for u, v, d in h.edges(data=True):
        d["capacity"] = max(d["cap"], 0.0)
    valor, flujos = nx.maximum_flow(h, "_S", "_T")
    entregado = pd.Series({n: flujos[n]["_T"] for n in demanda.index}, name="entregado")
    faltante = (demanda - entregado).clip(lower=0).rename("faltante")
    usado = pd.Series({n: flujos["_S"][n] for n in oferta.index}, name="usado")
    filas = []
    for u, v, d in g.edges(data=True):
        f = flujos[u][v]
        filas.append({"origen": u, "destino": v, "gasoducto": d["gasoducto"], "capacidad": d["cap"], "flujo": f,
                      "uso": f / d["cap"] if d["cap"] > 0 else float("nan")})
    arcos = pd.DataFrame(filas)
    _, (lado_s, _) = nx.minimum_cut(h, "_S", "_T")
    cuello = arcos[(arcos["origen"].isin(lado_s)) & (~arcos["destino"].isin(lado_s)) & (arcos["capacidad"] < 99)]
    return {"total": valor, "entregado": entregado, "faltante": faltante, "usado": usado, "arcos": arcos, "cuello": cuello}


def comparar_obras(oferta: pd.Series, demanda: pd.Series, combinaciones: dict[str, list[str]]) -> pd.DataFrame:
    """El faltante total y por nodo para cada combinación de obras."""
    filas = {}
    for nombre, obras in combinaciones.items():
        r = flujo_maximo(grafo(obras), oferta, demanda)
        fila = r["faltante"].to_dict()
        fila["faltante_total"] = r["faltante"].sum()
        fila["gnl_usado"] = r["usado"].get("ESCOBAR", 0.0) + r["usado"].get("BAHIA_GNL", 0.0)
        filas[nombre] = fila
    return pd.DataFrame(filas).T
