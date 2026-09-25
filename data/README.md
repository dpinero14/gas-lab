# Datos

Nada de esta carpeta se versiona. `python scripts/download_data.py` baja las series y la
temperatura; `python scripts/download_partes.py` baja los partes diarios (unos 9.000 PDF, cerca
de 350 MB, más de una hora la primera vez). Los notebooks dejan intermedios en `data/processed/`.

| Archivo | Fuente | Licencia | Qué es |
|---|---|---|---|
| `series_gas.json` | ENARGAS, dataset "Producción y consumo de gas natural", vía la API de series de tiempo de datos.gob.ar | datos.gob.ar | Consumo mensual por tipo de usuario (residencial, comercial, entes oficiales, industria, centrales, GNC, subdistribuidoras) y por distribuidora, y producción, en millones de m³, desde enero de 1996 |
| `clima/<distribuidora>.csv` | ERA5 (Copernicus/ECMWF) vía el archivo histórico de Open-Meteo | CC BY 4.0 | Temperatura media diaria desde 1996 en una ciudad por área de distribución |
| `partes/real/<aaaammdd>.pdf` | ENARGAS, partes diarios operativos, "Gas natural distribuido" | publicación oficial | Consumo real del día por distribuidora y por clientes directos de TGN y TGS, en miles de m³ a 9.300 kcal, desde 2014 |
| `partes/transporte/<aaaammdd>.pdf` | ENARGAS, partes diarios operativos, "Gas natural transportado" | publicación oficial | Inyección total al sistema y, en notas al pie, GNL por Escobar y Gasandes, GNL por Bahía Blanca (hasta 2018), Gasoducto Perito Moreno e importación por el norte, en millones de m³ por día |

Descarga verificada el 25 de septiembre de 2026. El listado de partes se pide por POST a
`partes-diarios-listado.php` y cada PDF a `descarga.php`, los mismos pedidos que hace la página
del ENARGAS.
