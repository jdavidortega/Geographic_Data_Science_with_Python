# Geographic Data Science with Python

Material de clase de José Ortega para dos materias: **Geoposicionamiento** y **Percepción remota**. Incluye notebooks prácticos en Python y presentaciones interactivas en HTML que reemplazan progresivamente las diapositivas de PowerPoint. La carpeta `ML/` reúne contenidos de aprendizaje automático que se usan en ambas materias.

## Estructura

```
Geoposicionamiento/          Materia: GNSS y análisis espacial
  *.ipynb                    Notebooks
  data/                      Datos de los notebooks de esta materia
  presentaciones/            Presentaciones interactivas (HTML)
Percepcion_remota/           Materia: imágenes satelitales y radar
  *.ipynb                    Notebooks
  radar_meteorologico/       Radares meteorológicos del IDEAM
  presentaciones/            Presentaciones interactivas (HTML)
ML/                          Aprendizaje automático (transversal)
data/                        Datos compartidos (Landsat 8, Sentinel-2, rásteres)
requirementes.txt            Dependencias de Python
```

## Presentaciones

Cada presentación es un único archivo HTML con estilos, simulaciones y figuras incluidos. Se abre con cualquier navegador, sin servidor ni instalación, y funciona sin conexión (solo los enlaces a las fuentes requieren internet).

Para usarla, descarga el HTML y ábrelo con doble clic. Por defecto se abre en modo láminas: se avanza con las flechas del teclado o los botones de la barra inferior, el botón **Índice** lleva a cualquier lámina y **Modo lectura** muestra todo el contenido en una sola página.

| Materia | Presentación | Archivo |
|---|---|---|
| Geoposicionamiento | SAR abierto: del eco al desplazamiento (Sentinel-1, InSAR) | [HTML](Geoposicionamiento/presentaciones/insar_sentinel1.html) |

Al agregar una presentación nueva: guárdala en la carpeta `presentaciones/` de su materia y añade una fila a esta tabla. Si el HTML tiene un botón de descarga, debe apuntar al propio archivo con una ruta relativa (`href="nombre.html"`), nunca a rutas absolutas como `/descargas/...`.

## Notebooks

### Geoposicionamiento

| Notebook | Contenido |
|---|---|
| `gnss_pseudodistancia.ipynb` | De la señal a la pseudodistancia: qué mide un receptor GNSS, con datos RINEX de la estación BOGT. |
| `gnss_estimacion_posicion.ipynb` | Estimación de la posición: de las pseudodistancias a X, Y, Z y el error del reloj del receptor. |
| `geospatial_data_types.ipynb` | Tipos de datos geoespaciales: geotablas, superficies y grafos espaciales. |
| `db.ipynb` | Una base de datos espacial para el curso. |
| `choropleth_es.ipynb` | Mapas coropléticos: de los puntos a las entidades espaciales, y de la variable al color. |
| `geospatial_weights.ipynb` | Pesos espaciales: contigüidad y distancia. |
| `autocorrelacion_espacial.ipynb` | Autocorrelación espacial de hurtos a residencia en barrios y veredas de Medellín. |
| `point_pattern_analysis.ipynb` | Análisis de patrones de puntos. |

### Percepción remota

| Notebook | Contenido |
|---|---|
| `processing_landsat_and_sentinel_data.ipynb` | Landsat 8 y Sentinel-2: reflectancia de superficie e índices espectrales (NDVI, NDWI, NDBI, SAVI). |
| `radar_meteorologico/get_data.ipynb` | Descarga de datos de los radares meteorológicos del IDEAM desde su repositorio público en AWS S3. |
| `radar_meteorologico/visualization.ipynb` | Lectura y visualización de reflectividad con Py-ART y exportación a GeoTIFF. |

### Aprendizaje automático (transversal)

| Notebook | Contenido |
|---|---|
| `conceptos_estadisticos.ipynb` | Teorema central del límite, muestreo aleatorio y ley de los grandes números. |
| `EDA.ipynb` | Análisis exploratorio de datos. |
| `knn_iris.ipynb` | K vecinos más cercanos (KNN): conceptos, matemática e implementación. |
| `nosupervisado.ipynb` | Aprendizaje no supervisado: K-means y DBSCAN. |
| `sentinel2_classification.ipynb` | Clasificación de coberturas con imágenes Sentinel-2. |

## Entorno

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirementes.txt
```

Las imágenes Landsat 8 y Sentinel-2 de `data/` no están en el repositorio por su tamaño (ver `.gitignore`); se descargan de los portales de USGS y Copernicus.
