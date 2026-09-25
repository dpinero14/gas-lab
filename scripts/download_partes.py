"""Baja los partes diarios del ENARGAS (real y transporte) desde 2014 hasta hoy. Reanudable.

    python scripts/download_partes.py [desde AAAA-MM-DD] [hasta AAAA-MM-DD]

Unos 4.600 días con dos PDF cada uno, cerca de 350 MB; con una pausa corta entre pedidos
tarda más de una hora la primera vez. Lo que ya está en data/raw/partes no se vuelve a pedir.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from glab.partes import TIPOS, download, listing  # noqa: E402


def _uno(args):
    d, tipo = args
    for intento in range(3):
        try:
            return download(d, tipo, pausa=0.05) is not None
        except Exception:
            continue
    return False


def main() -> None:
    from concurrent.futures import ThreadPoolExecutor

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    desde = date.fromisoformat(args[0]) if len(args) > 0 else date(2014, 1, 1)
    hasta = date.fromisoformat(args[1]) if len(args) > 1 else date.today() - timedelta(days=1)
    # --invierno: solo mayo a septiembre, del año más reciente al más viejo (lo que pide el análisis del pico)
    invierno = "--invierno" in sys.argv
    ok = falta = 0
    # seis pedidos a la vez, sin cargar de más al servidor
    with ThreadPoolExecutor(max_workers=6) as ex:
        anios = range(hasta.year, desde.year - 1, -1) if invierno else range(desde.year, hasta.year + 1)
        for anio in anios:
            d0, d1 = max(desde, date(anio, 1, 1)), min(hasta, date(anio, 12, 31))
            if invierno:
                d0, d1 = max(d0, date(anio, 5, 1)), min(d1, date(anio, 9, 30))
                if d0 > d1:
                    continue
            try:
                dias = listing(d0, d1)
            except Exception as e:
                print(f"{anio}: no pude leer el listado ({type(e).__name__})", flush=True)
                continue
            res = list(ex.map(_uno, [(d, t) for d in dias for t in TIPOS]))
            ok += sum(res)
            falta += len(res) - sum(res)
            print(f"{anio}: {len(dias)} días listados; acumulado {ok} partes en disco, {falta} sin bajar", flush=True)
    print("listo", ok, falta)


if __name__ == "__main__":
    main()
