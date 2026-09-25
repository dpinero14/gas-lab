"""Baja todo lo que usa el repo: las series mensuales del ENARGAS, la temperatura diaria de las diez ciudades y los partes diarios.

    python scripts/download_data.py            # series y temperatura (un par de minutos)
    python scripts/download_partes.py          # los partes diarios desde 2014 (más de una hora la primera vez)

Todo queda en data/raw, que no se versiona.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from glab import CIUDADES  # noqa: E402
from glab.clima import fetch_city  # noqa: E402
from glab.series import fetch  # noqa: E402


def main() -> None:
    df = fetch(refresh=True)
    print(f"series del ENARGAS: {df.shape[1]} series, {df.index.min():%m/%Y} a {df.index.max():%m/%Y}")
    for k, (nombre, _, _) in CIUDADES.items():
        s = fetch_city(k)
        print(f"  temperatura {nombre}: {s.index.min():%d/%m/%Y} a {s.index.max():%d/%m/%Y}")
    print("listo; para los partes diarios: python scripts/download_partes.py")


if __name__ == "__main__":
    main()
