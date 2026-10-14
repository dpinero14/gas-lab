"""Baja lo que usa el notebook 03 (la red troncal): producción por cuenca, trazas de los gasoductos y contorno de provincias.

    python scripts/download_red.py

- Serie histórica de producción de gas natural por cuenca (Secretaría de Energía, Capítulo IV, CSV).
- Gasoductos de transporte (ENARGAS, shapefile publicado por la Secretaría de Energía), simplificados a
  líneas en `data/processed/red_gasoductos_lineas.npz` para dibujar el fondo del mapa.
- Provincias del IGN por WFS, simplificadas a polígonos en `data/processed/arg_outline.npz`.

Las capacidades por tramo (`data/capacidad_enargas_2025.csv`) y la inyección por cuenca
(`data/inyeccion_enargas_2025.csv`) están transcriptas a mano del informe anual 2025 del ENARGAS
(páginas 203 a 209) y se versionan con el repo.
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from glab import DATA_PROC, DATA_RAW  # noqa: E402

UA = {"User-Agent": "gas-lab/0.1 (+https://github.com/dpinero14)"}
ENERGIA = "http://datos.energia.gob.ar/dataset"
CUENCA = (f"{ENERGIA}/c846e79c-026c-4040-897f-1ad3543b407c/resource/a3244ddd-38bc-4800-a700-360b649d2f3a/download/"
          "serie-histrica-de-produccin-de-gas-natural-por-cuenca-y-sub-tipo-de-recurso-captulo-iv-.csv")
GASODUCTOS = (f"{ENERGIA}/8758101a-1e0d-413f-8cc5-83e21ece6391/resource/5af07e15-f356-40b9-a369-63dbf38a938a/download/"
              "gasoductos-de-transporte-enargas-.zip")
IGN = ("https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=ign:provincia"
       "&outputFormat=application/json")


def _get(url: str, timeout: int = 300) -> bytes:
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.content


def cuencas() -> Path:
    dest = DATA_RAW / "gas_por_cuenca.csv"
    if not dest.exists():
        dest.write_bytes(_get(CUENCA))
    (DATA_PROC / "gas_por_cuenca.csv").write_bytes(dest.read_bytes())
    print(f"  producción por cuenca: {dest.stat().st_size / 1e3:.0f} kB")
    return dest


def gasoductos(tolerancia: float = 0.01) -> Path:
    import geopandas as gpd

    raw = DATA_RAW / "gasoductos_transporte_enargas.zip"
    if not raw.exists():
        raw.write_bytes(_get(GASODUCTOS))
    carpeta = DATA_RAW / "gasoductos_transporte_enargas"
    if not carpeta.exists():
        zipfile.ZipFile(raw).extractall(carpeta)
    shp = next(carpeta.glob("*.shp"))
    g = gpd.read_file(shp)
    g = g[g["EMPRESA_LI"].str.contains("Transportadora|Gasandes|Pac", na=False)]
    lineas = []
    for geom in g.geometry.simplify(tolerancia):
        for p in (geom.geoms if geom.geom_type == "MultiLineString" else [geom]):
            lineas.append(np.asarray(p.coords, dtype=np.float32))
    dest = DATA_PROC / "red_gasoductos_lineas.npz"
    np.savez_compressed(dest, **{f"l{i}": l for i, l in enumerate(lineas)})
    print(f"  gasoductos: {len(g)} tramos, {len(lineas)} líneas simplificadas")
    return dest


def provincias(tolerancia: float = 0.02) -> Path:
    from shapely.geometry import shape

    raw = DATA_RAW / "ign_provincias.geojson"
    if not raw.exists():
        raw.write_bytes(_get(IGN))
    import json
    fc = json.loads(raw.read_text(encoding="utf-8"))
    polys = []
    for f in fc["features"]:
        geom = shape(f["geometry"]).simplify(tolerancia)
        for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            xy = np.asarray(p.exterior.coords, dtype=np.float32)
            if len(xy) > 4:
                polys.append(xy)
    dest = DATA_PROC / "arg_outline.npz"
    np.savez_compressed(dest, n=np.array(len(polys)), **{f"p{i}": p for i, p in enumerate(polys)})
    print(f"  provincias: {len(fc['features'])} del IGN, {len(polys)} polígonos simplificados")
    return dest


def main() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    print("Secretaría de Energía: producción por cuenca y gasoductos; IGN: provincias")
    cuencas()
    gasoductos()
    provincias()
    print("listo")


if __name__ == "__main__":
    main()
