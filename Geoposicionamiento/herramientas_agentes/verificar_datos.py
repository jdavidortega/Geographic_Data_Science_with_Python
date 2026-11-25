"""Inspección de las capas y cifras de referencia del ejercicio de agentes.
Se ejecuta con el .venv del repositorio desde la raíz del repo."""
import json, sys
from pathlib import Path
import pandas as pd, geopandas as gpd

D = Path("Geoposicionamiento/data")
out = {}
b = gpd.read_file(D/"barrios_y_veredas_mr.geojson")
c = gpd.read_file(D/"cruces_semaforicos.geojson")
out["barrios"] = {"n": len(b), "crs": str(b.crs), "columnas": list(b.columns), "geom": sorted(b.geom_type.unique().tolist()),
                  "bounds": [round(x,1) for x in b.total_bounds], "validas": int(b.is_valid.sum()), "ejemplo": b.drop(columns="geometry").head(3).to_dict("records")}
out["cruces"] = {"n": len(c), "crs": str(c.crs), "columnas": list(c.columns), "geom": sorted(c.geom_type.unique().tolist()),
                 "bounds": [round(x,1) for x in c.total_bounds], "ejemplo": c.drop(columns="geometry").head(3).to_dict("records")}
# columna de nombre y de id
print(b.drop(columns="geometry").head(3).to_string())
print(c.drop(columns="geometry").head(3).to_string())
print(b.crs, c.crs)
# conteo por barrio con predicado within
cols_nombre = [x for x in b.columns if "nombre" in x.lower()]
nombre = cols_nombre[0]
j = gpd.sjoin(c, b[[nombre, "geometry"]], how="left", predicate="within")
asignados = j[nombre].notna().sum()
conteo = j.groupby(nombre).size().sort_values(ascending=False)
out["conteo"] = {"columna_nombre": nombre, "asignados": int(asignados), "fuera": int(len(c)-asignados), "duplicados_en_join": int(len(j)-len(c)),
                 "top10": conteo.head(10).to_dict(), "barrios_con_cruces": int((conteo>0).sum()), "barrios_sin_cruces": int(len(b)-(conteo>0).sum())}
# cercanía al cruce 125
idcol = [x for x in c.columns if "id" in x.lower() or "objectid" in x.lower()]
print("id cols", idcol, c[idcol].head(3).to_string() if idcol else "")
out["cercania"] = {}
for col in idcol:
    sel = c[c[col]==125]
    if len(sel)==1:
        p = sel.geometry.iloc[0]
        d = c.geometry.distance(p)
        out["cercania"][col] = {"r300": int(((d<=300)&(d>0)).sum()), "r500": int(((d<=500)&(d>0)).sum()), "r1000": int(((d<=1000)&(d>0)).sum()),
                                "barrio": str(j.loc[c[col]==125, nombre].iloc[0]), "xy": [round(p.x,1), round(p.y,1)]}
# hurtos
h = pd.read_csv(D/"hurto_a_residencia.csv", low_memory=False)
h["fecha"] = pd.to_datetime(h["fecha_hecho"], utc=True, errors="coerce").dt.tz_convert("America/Bogota")
out["hurtos"] = {"n": len(h), "columnas": list(h.columns), "sin_lat": int(h.latitud.isna().sum()), "sin_lon": int(h.longitud.isna().sum()),
                 "lat_min_max": [float(h.latitud.min()), float(h.latitud.max())], "lon_min_max": [float(h.longitud.min()), float(h.longitud.max())],
                 "fecha_min": str(h.fecha.min()), "fecha_max": str(h.fecha.max()), "fecha_nula": int(h.fecha.isna().sum()),
                 "cantidad_valores": h.cantidad.value_counts().head(5).to_dict(), "por_anio": h.fecha.dt.year.value_counts().sort_index().to_dict(),
                 "conducta": h.conducta.value_counts().head(3).to_dict(), "duplicados_exactos": int(h.duplicated().sum()),
                 "modalidad_top": h.modalidad.value_counts().head(5).to_dict(), "nombre_barrio_top": h.nombre_barrio.value_counts().head(5).to_dict(),
                 "lat_fuera_medellin": int(((h.latitud<6.1)|(h.latitud>6.4)|(h.longitud<-75.75)|(h.longitud>-75.45)).sum())}
hh = h.dropna(subset=["latitud","longitud"])
g = gpd.GeoDataFrame(hh, geometry=gpd.points_from_xy(hh.longitud, hh.latitud), crs="EPSG:4326").to_crs(b.crs)
jh = gpd.sjoin(g, b[[nombre,"geometry"]], how="left", predicate="within")
out["hurtos"]["asignados_barrio"] = int(jh[nombre].notna().sum())
out["hurtos"]["top10_barrio_total"] = jh.groupby(nombre).size().sort_values(ascending=False).head(10).to_dict()
for y in [2023, 2024, 2025]:
    s = jh[jh.fecha.dt.year==y]
    out["hurtos"][f"top5_{y}"] = s.groupby(nombre).size().sort_values(ascending=False).head(5).to_dict()
    out["hurtos"][f"n_{y}"] = int(len(s))
# hurtos a 300 m y 500 m del cruce 125
if out["cercania"]:
    p = c[c[idcol[0]]==125].geometry.iloc[0]
    d = g.geometry.distance(p)
    out["hurtos"]["r300_cruce125"] = int((d<=300).sum()); out["hurtos"]["r500_cruce125"] = int((d<=500).sum())
json.dump(out, open("Geoposicionamiento/herramientas_agentes/verificacion_datos.json","w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:6000])
