"""Los partes diarios del ENARGAS: un PDF por día desde 2014, con lo que el sistema entregó y lo que entró.

- Parte "real" (gas distribuido): consumo real del día por distribuidora y por cargadores
  directos de TGN y TGS, en miles de m³ a 9.300 kcal, y el total con los gasoductos propios.
- Parte "transporte": inyección total al sistema y, en notas al pie, cuánto entró de GNL por
  Escobar y Gasandes, del Gasoducto Perito Moreno (GPM) y de Bolivia, en millones de m³ por día.

El listado se pide por POST al mismo endpoint que usa la página; cada PDF se baja por
`descarga.php`. Todo queda cacheado en data/raw/partes/<tipo>/<aaaammdd>.pdf y se lee con
pdfplumber. Los formatos cambiaron con los años: las funciones de lectura buscan las filas por
nombre y devuelven NaN cuando no encuentran algo, en lugar de adivinar.
"""

from __future__ import annotations

import io
import re
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import DATA_RAW

BASE = "https://www.enargas.gob.ar/secciones/transporte-y-distribucion/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
TIPOS = ("real", "transporte")

# nombres de fila del parte real, como aparecen en el PDF, y el nombre que usa el repo
FILAS_REAL = {
    "gasnor": r"GasNor", "cuyana": r"Cuyana", "centro": r"Centro", "litoral": r"Litoral", "naturgy_ban": r"(?:NaturgyBan|Naturgy ?Ban|GasNatural ?Ban|Gas ?Ban)",
    "metrogas": r"Metro ?Gas", "pampeana": r"Pampeana", "sur": r"Sur \(2\)", "gasnea": r"Gas ?Nea", "tgn_directo": r"TGN Directo",
    "tgs_directo": r"TGS Directo",
}
NUM = r"(-?\d[\d.,]*)"


def pdf_path(tipo: str, d: date, raw: Path = DATA_RAW) -> Path:
    return raw / "partes" / tipo / f"{d:%Y%m%d}.pdf"


def listing(desde: date, hasta: date, timeout: int = 120) -> list[date]:
    """Días con parte publicado entre dos fechas (el listado de la página)."""
    r = requests.post(BASE + "partes-diarios-listado.php", data={"fecha_desde": f"{desde:%Y%m%d}", "fecha_hasta": f"{hasta:%Y%m%d}"},
                      headers={**UA, "X-Requested-With": "XMLHttpRequest"}, timeout=timeout)
    r.raise_for_status()
    return [date(int(y), int(m), int(dd)) for dd, m, y in re.findall(r"<td class='margin-0'>(\d\d)/(\d\d)/(\d{4})</td>", r.text)]


def download(d: date, tipo: str, raw: Path = DATA_RAW, pausa: float = 0.15, timeout: int = 60) -> Path | None:
    """Baja un parte si no está en la caché. Devuelve la ruta, o None si el servidor no lo tiene."""
    p = pdf_path(tipo, d, raw)
    if p.exists() and p.stat().st_size > 1000:
        return p
    r = requests.get(BASE + "descarga.php", params={"tipo": tipo, "path": f"partes-diarios/{tipo}", "file": f"{d:%Y%m%d}.pdf"}, headers=UA, timeout=timeout)
    time.sleep(pausa)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(r.content)
    return p


def _num(s: str) -> float:
    """'136472' -> 136472.0; '1.234,5' -> 1234.5; '159.0' -> 159.0."""
    s = s.strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def pdf_text(p: Path | bytes) -> str:
    import pdfplumber

    src = io.BytesIO(p) if isinstance(p, (bytes, bytearray)) else p
    with pdfplumber.open(src) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def parse_real(text: str) -> dict:
    """Del texto del parte real: consumo real por distribuidora (última columna) y los totales, en miles de m³."""
    out = {}
    lineas = text.splitlines()
    for clave, patron in FILAS_REAL.items():
        for ln in lineas:
            if re.match(rf"^\s*(?:{patron})(?=\s)", ln):
                nums = re.findall(NUM, ln[re.match(rf"^\s*(?:{patron})", ln).end():])
                vals = [_num(n) for n in nums if not re.fullmatch(r"\(\d\)", n)]
                vals = [v for v in vals if not np.isnan(v)]
                if len(vals) >= 2:
                    out[clave] = vals[-1]
                    break
    # totales: las dos líneas de solo números (sistema y con gasoductos propios)
    solo_nums = [ln for ln in lineas if re.fullmatch(r"\s*\d[\d.,]*(?:\s+\d[\d.,]*){3}\s*", ln)]
    if solo_nums:
        out["total_sistema"] = _num(solo_nums[0].split()[-1])
        out["total_con_propios"] = _num(solo_nums[-1].split()[-1]) if len(solo_nums) > 1 else np.nan
    return out


def parse_transporte(text: str) -> dict:
    """Del texto del parte de transporte: inyección total y los aportes de GNL, GPM y Bolivia, en millones de m³/día."""
    out = {}
    m = re.search(r"Inyecci[oó]n Total\s*(?:\([a-z]\))?\s*" + NUM, text)
    if m:
        out["inyeccion_total"] = _num(m.group(1))
    # dos terminales de GNL: Escobar (con Gasandes desde Chile en la misma nota) y Bahía Blanca, que operó hasta 2018
    m = re.search(r"GNL Escobar[^()\n]*?\(\s*" + NUM + r"\s*\)", text)
    if m:
        out["gnl_escobar_gasandes"] = _num(m.group(1))
    m = re.search(r"GNL B\.? ?Blanca\s*\(\s*" + NUM + r"\s*\)", text)
    if m:
        out["gnl_bahia_blanca"] = _num(m.group(1))
    m = re.search(r"GPM\s*\(\s*" + NUM + r"\s*\)", text)
    if m:
        out["gpm"] = _num(m.group(1))
    m = re.search(r"Bolivia[^()\n]*?\(\s*" + NUM + r"\s*\)", text)
    if m:
        out["bolivia_norandino"] = _num(m.group(1))
    m = re.search(r"M[aá]xima:\s*" + NUM, text)
    if m:
        out["tmax_pronostico_caba"] = _num(m.group(1))
    m = re.search(r"M[ií]nima:\s*" + NUM, text)
    if m:
        out["tmin_pronostico_caba"] = _num(m.group(1))
    return out


def parse_day(d: date, raw: Path = DATA_RAW) -> dict:
    fila = {"fecha": d}
    for tipo, fn in (("real", parse_real), ("transporte", parse_transporte)):
        p = pdf_path(tipo, d, raw)
        if p.exists():
            try:
                fila.update(fn(pdf_text(p)))
            except Exception:       # un PDF roto no frena la serie; queda NaN
                pass
    return fila


def daily_table(desde: date, hasta: date, raw: Path = DATA_RAW, cache: Path | None = None) -> pd.DataFrame:
    """Tabla diaria con todo lo leído de los partes. Con `cache`, lee y escribe un parquet para no volver a parsear."""
    if cache is not None and Path(cache).exists():
        t = pd.read_parquet(cache)
        hechos = set(pd.to_datetime(t["fecha"]).dt.date)
    else:
        t, hechos = pd.DataFrame(), set()
    filas = []
    d = desde
    while d <= hasta:
        if d not in hechos and (pdf_path("real", d, raw).exists() or pdf_path("transporte", d, raw).exists()):
            filas.append(parse_day(d, raw))
        d += timedelta(days=1)
    if filas:
        t = pd.concat([t, pd.DataFrame(filas)], ignore_index=True)
    if len(t):
        t["fecha"] = pd.to_datetime(t["fecha"])
        t = t.sort_values("fecha").drop_duplicates("fecha").reset_index(drop=True)
        if cache is not None:
            Path(cache).parent.mkdir(parents=True, exist_ok=True)
            t.to_parquet(cache, index=False)
    return t


__all__ = ["TIPOS", "pdf_path", "listing", "download", "pdf_text", "parse_real", "parse_transporte", "parse_day", "daily_table"]
