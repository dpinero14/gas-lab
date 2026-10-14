# Material para el post

Hallazgos de gas-lab, en el orden en que salieron. Son materia prima: el texto del post lo
escribe Diego.

1. **El frío no sube el consumo total de gas: lo redistribuye.** En invierno, cada grado-día
   extra suma 3,3 millones de m³ al mes en los hogares y resta 2,6 en las centrales eléctricas.
   El total casi no se mueve (correlación 0,07). Cuando hace frío se prioriza a los hogares y se
   corta a industrias, GNC y centrales: el total de invierno mide lo que el sistema entrega, no lo
   que se pide.
2. **En el total, gana el más simple.** Repetir el mismo mes del año anterior se equivoca 5,2 % en
   promedio en diez años de pronósticos; el SARIMA del trabajo sobre España, 6,5 %; con
   temperatura, lo mismo. En los hogares, en cambio, la temperatura baja el error de 10,8 % a
   6,1 %.
3. **Dos estacionalidades opuestas.** Los hogares consumen cinco veces más en julio que en enero;
   las centrales tienen el pico en verano, por el aire acondicionado.
4. **La parte importada del invierno bajó de 27 % a 7 %.** Récord de GNL en 2021 (3.200 millones
   de m³ de mayo a septiembre); en 2026, 1.017. Bolivia se fue en 2024. El máximo diario de gas
   propio pasó de 113 a 146 millones de m³ con el gasoducto Perito Moreno.
5. **El GNL no sigue al frío.** Entre 2021 y 2026, la correlación entre el GNL de cada invierno y
   su frío es de -0,19: se compra antes, por contrato.
6. **El día más frío de 2026 (3 de julio):** 117 millones de m³ a las distribuidoras, 163 de
   inyección, 141 de gas propio, 20 de GNL. El techo de gas propio, 141, no se superó en todo el
   invierno.
7. **El invierno 2027.** Con el tiempo de cada invierno desde 1997 y la capacidad de 2026: un
   invierno normal deja faltante físico en 57 días (395 millones de m³, unos 5 buques como mínimo);
   operando como en 2024-2026 se usarían unos 1.230 millones de m³ de GNL (unos 14 buques); uno
   frío, 1.420 (17 buques).
8. **El faltante nacional no alcanza para explicar el GNL.** En 2026 el balance nacional dio 371
   millones de m³ de faltante y entraron 1.017: el GNL entra por Escobar, al lado del AMBA, y
   cubre un cuello regional, no solo nacional.

9. **El gas está en un solo lugar y los caños que salen de ahí están llenos.** Toda la suba de
   producción de doce años (+42 millones de m³ por día) es de Neuquén; Austral, Golfo San Jorge y
   Noroeste caen. En el invierno 2026 Neuquén produjo 121 por día y los caños que salen de la
   cuenca suman 99. La cuenca produce lo que el caño deja sacar: por eso agosto dio la primera
   caída interanual.
10. **El sistema tiene 42 millones de capacidad libre, en los caños equivocados.** Gasoducto Norte
    3 de 28 (sin Bolivia), San Martín 24 de 41 (la Austral cae). Los de Neuquén: Neuba y Perito
    Moreno 74 de 72, Centro Oeste 37 de 34. TGN no suma un metro cúbico desde 2015.
11. **El día más frío sin barcos, calculado con flujo máximo sobre la red: faltan 19, 16 de
    ellos en el AMBA.** Con los 20 de GNL de Escobar y los 2 de Bolivia la red entrega todo. Los
    caños saturados: Neuquén–Bahía Blanca, Ordoqui–Buenos Aires y la cabecera del Centro Oeste.
    El GNL no cubre falta de gas: cubre falta de caño hacia el AMBA, que es donde entra.
12. **Ninguna obra sola cierra el invierno.** El Perito Moreno ampliado (2027) baja el faltante
    del AMBA de 16 a 2 pero no toca Santa Fe ni el NEA; el Tratayén–La Carlota (2029) hace lo
    contrario; las compresoras del Norte no cambian nada en el centro. Cierran el día más frío
    sin barcos: Perito Moreno + Tratayén–La Carlota, o Perito Moreno + la etapa 2 del Kirchner,
    que nadie tiene en agenda. Dos inviernos a barco como mínimo.

## Límites

- Temperatura del reanálisis ERA5 en una ciudad por distribuidora.
- Partes diarios provisorios; antes de 2019 no separan el gas de Bolivia.
- Balance nacional, sin cuellos regionales; supone la capacidad de 2026.
- Sin precios ni tarifas en los modelos.
- La red es un flujo máximo con un nodo por distribuidora y los directos repartidos con
  proporciones fijas; sin presiones ni combustible; capacidades de diseño del ENARGAS, con lo
  observado donde fue mayor.

## Ángulos posibles

- El frío no sube el consumo: lo reparte. Quién pierde el gas cuando hace frío.
- El modelo de España contra la Argentina: por qué acá el más simple gana en el total.
- ¿Alcanza el gas el invierno que viene? Cuántos barcos hacen falta según el frío.
- De 27 % a 7 %: cómo Vaca Muerta y el Perito Moreno cambiaron el invierno.
- Faltó caño, no gas: Neuquén produce 121 y tiene 99 de salida; qué obra cierra el invierno
  (ninguna sola).

## Links

- Repo: https://github.com/dpinero14/gas-lab
- Página: https://dpinero14.github.io/gas-lab/
