"""gas-lab: cuánto gas va a pedir la Argentina y si alcanza en el pico del invierno.

Rutas del repo y constantes. El resto son módulos con funciones puras: `series` (el consumo
mensual del ENARGAS por la API de series del Estado), `clima` (temperatura diaria ERA5 y
grados-día), `partes` (los partes diarios del ENARGAS: consumo real por distribuidora,
inyección total y GNL), `modelos` (del ingenuo estacional al SARIMAX con temperatura),
`validacion` (pronósticos a 12 meses desde cada año), `escenarios` (inviernos fríos,
normales y cálidos) y `figuras`.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROC = REPO_ROOT / "data" / "processed"
DOCS = REPO_ROOT / "docs"
FIGURES = DOCS / "figures"

# Consumo y producción mensual, en millones de m³ (dataset "Producción y consumo de gas natural",
# ENARGAS, en la API de series de tiempo de datos.gob.ar). Mensual desde enero de 1996.
SERIES = {
    "total": "364.3_TOTALTAL__5",
    "residencial": "364.3_RESIDENCIAIAL__11",
    "comercial": "364.3_COMERCIALIAL__9",
    "entes_oficiales": "364.3_ENTES_OFICLES__15",
    "industria": "364.3_INDUSTRIARIA__9",
    "centrales": "364.3_CENTRALES_CAS__20",
    "gnc": "364.3_GNCGNC__3",
    "sdb": "364.3_SDBSDB__3",
    "produccion": "364.3_PRODUCCIoNRAL__25",
}
DISTRIBUIDORAS = {
    "metrogas": "364.3_METROGASGAS__8",
    "naturgy_ban": "364.3_GAS_NATURAOSA__18",
    "camuzzi_pampeana": "364.3_CAMUZZI_GAANA__20",
    "camuzzi_sur": "364.3_CAMUZZI_GASUR__19",
    "litoral": "364.3_LITORAL_GAGAS__11",
    "ecogas_centro": "364.3_DISTRIB._GGAS__30",
    "ecogas_cuyana": "364.3_DISTRIB._GGAS__26",
    "gasnor": "364.3_GASNORNOR__6",
    "gasnea": "364.3_GASNEANEA__6",
    "redengas": "364.3_REDENGASGAS__8",
}

# Una ciudad por área de distribución, para la temperatura (lat, lon). Donde el área es grande,
# la ciudad con más usuarios; es una aproximación y se declara.
CIUDADES = {
    "metrogas": ("Buenos Aires", -34.61, -58.44),
    "naturgy_ban": ("San Martín (GBA norte)", -34.57, -58.54),
    "camuzzi_pampeana": ("Mar del Plata", -38.00, -57.56),
    "camuzzi_sur": ("Neuquén", -38.95, -68.06),
    "litoral": ("Rosario", -32.95, -60.64),
    "ecogas_centro": ("Córdoba", -31.42, -64.18),
    "ecogas_cuyana": ("Mendoza", -32.89, -68.83),
    "gasnor": ("San Miguel de Tucumán", -26.82, -65.22),
    "gasnea": ("Resistencia", -27.45, -58.99),
    "redengas": ("Paraná", -31.73, -60.53),
}

# Temperatura base de los grados-día de calefacción: por debajo de 18 °C de media diaria se calefacciona.
T_BASE = 18.0

__all__ = ["REPO_ROOT", "DATA_RAW", "DATA_PROC", "DOCS", "FIGURES", "SERIES", "DISTRIBUIDORAS", "CIUDADES", "T_BASE"]
