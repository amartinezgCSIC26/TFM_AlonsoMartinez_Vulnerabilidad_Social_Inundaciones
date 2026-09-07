e ha recopilado el conjunto de scripts desarrollados en lenguaje de Python para automatizar el flujo de trabajo del TFM. 
El código se estructura en tres módulos independientes orientados a la redistribución de la información sociodemográfica, 
la estandarización de los indicadores urbanos. 
Este proyecto propone un marco metodológico de análisis espacial mediante EMC a escala de parcela catastral fundamentado 
en la desagregación dasimétrica de estadísticas oficiales del INE y en la normalización de las variables por diferentes 
métodos. La metodología se ha aplicado para elaborar un índice de vulnerabilidad social para 8 municipios de Valencia. 
El script llamado traspasar_datos.py ejecuta la desagregación dsimétrica de la información del Censo de Población y 
Viviendas desde la sección censal hasta la parcela catastral, utilizando el recuento de viviendas residenciales como 
variable de reparto. El segundo script (normalizar_datos.py) se encarga de homogeneizar las 12 variables utilizadas en 
el estudio aplicando normalización lineal y lógica borrosa para estandarizar todos los indicadores a una escala común entre 
0 y 1. Existen tres documentos, uno por script y  la capa final con los datos normalizados. 
