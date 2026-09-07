from qgis.core import *
from qgis.PyQt.QtCore import QVariant

def add_field(layer, name, field_type=QVariant.Double):
    existing_fields = [field.name() for field in layer.fields()]
    if name not in existing_fields:
        layer.dataProvider().addAttributes([QgsField(name, field_type)])
        layer.updateFields()
    return layer.fields().indexFromName(name)

def spatial_join(parcels_layer, sections_layer, demographic_fields):
    joined_result = processing.run("qgis:joinattributesbylocation", {
        'INPUT': parcels_layer,
        'JOIN': sections_layer,
        'PREDICATE': [0],  # Intersects
        'JOIN_FIELDS': demographic_fields,
        'METHOD': 1,
        'DISCARD_NONMATCHING': False,
        'OUTPUT': 'memory:joined_layer'
    })
    return joined_result['OUTPUT']

def safe_float(value):
    if value in [None, '']:
        return 0.0
    try:
        return float(str(value).replace(',', '.'))
    except:
        return 0.0

def run_geoprocess():
    project = QgsProject.instance()

    # 1. Cargar capas
    sections_layer = next((l for l in project.mapLayersByName('secciones_carraixet')), None)
    parcels_layer = next((l for l in project.mapLayersByName('datos_parcelas_carraixet')), None)

    if not sections_layer or not parcels_layer:
        print("❌ ERROR: No se han encontrado las capas 'secciones_carraixet' o 'datos_parcelas_carraixet' en tu panel de QGIS.")
        return

    # 2. Validar campos 
    required_fields = [
        'CUSEC', 'Pob_total', 'Pob_mujere', 'Pob_niños', 'Pob_mayores', 'Pob_extran',
        '% hog_unip', '%baja_educ', '%paro','Renta_hoga'
    ]
    
    for f in required_fields:
        if f not in [field.name() for field in sections_layer.fields()]:
            print(f"❌ ERROR: Falta la columna '{f}' en la capa secciones_carraixet.")
            return
            
    for f in ['REFCAT', 'pob_parcela']:
        if f not in [field.name() for field in parcels_layer.fields()]:
            print(f"❌ ERROR: Falta la columna '{f}' en la capa datos_parcelas_carraixet.")
            return

    exclude_fields = ['fid', 'CUSEC', 'CUMUN', 'NMUN', 'MUNICIPIO', 'objectid', 'cumun', 'nmun', 'CUSEC']
    demographic_fields = [f for f in sections_layer.fields().names() if f not in exclude_fields]
    
    joined_layer = spatial_join(parcels_layer, sections_layer, demographic_fields)
    if not joined_layer or not joined_layer.isValid():
        print("❌ ERROR: La unión espacial ha fallado.")
        return

    # Campos relativos que se clonan directamente
    direct_fields = ['% hog_unip', '%baja_educ', '%paro', 'Renta_hoga']
    cusec_dict = {}
    
    for feature in sections_layer.getFeatures():
        cusec_val = feature['CUSEC']
        cusec_dict[cusec_val] = {field: feature[field] for field in direct_fields if field in feature.fields().names()}

    fields_to_add = [
        'proporcion', 'area_km2',
        *[f'est_{f}' for f in demographic_fields if f not in direct_fields],
        *direct_fields,
        'Densidad_pob', 'Total_mujeres', 'Total_menor5',
        'Total_mayor65', 'Total_extranjeros'
    ]
    
    field_indices = {}
    joined_layer.startEditing()

    try:
        for field in fields_to_add:
            field_indices[field] = add_field(joined_layer, field)
        
        for feature in joined_layer.getFeatures():
            fid = feature.id()
            cusec_val = feature['CUSEC']
            pob_parcela = safe_float(feature['pob_parcela'])

            if pob_parcela > 0 and cusec_val in cusec_dict:
                for field, value in cusec_dict[cusec_val].items():
                    joined_layer.changeAttributeValue(fid, field_indices[field], value)
            else:
                for field in direct_fields:
                    joined_layer.changeAttributeValue(fid, field_indices[field], 0.0)

        for feature in joined_layer.getFeatures():
            fid = feature.id()
            
            try:
                parcel_pop = safe_float(feature['pob_parcela'])
                section_total = safe_float(feature['Pob_total'])
                proportion = parcel_pop / section_total if section_total != 0 else 0.0
                joined_layer.changeAttributeValue(fid, field_indices['proporcion'], proportion)
            except Exception as e:
                proportion = 0.0

            est_values = {}
            for f in demographic_fields:
                if f not in direct_fields:
                    try:
                        val = safe_float(feature[f])
                        estimated = val * proportion
                        est_values[f] = estimated
                        joined_layer.changeAttributeValue(fid, field_indices[f'est_{f}'], estimated)
                    except Exception as e:
                        est_values[f] = 0.0

            try:
                area_km2 = feature.geometry().area() / 1000000
                joined_layer.changeAttributeValue(fid, field_indices['area_km2'], area_km2)
            except Exception as e:
                area_km2 = 0.0

            try:
                total = est_values.get('pob_total', 0.0)
                area_km2_val = area_km2 if area_km2 > 0 else 1.0
                densidad = total / area_km2_val
                
                # Variables absolutas
                pob_mujeres_abs = est_values.get('Pob_mujere', 0.0)
                pob_niños_abs = est_values.get('Pob_niños', 0.0)
                pob_mayores_abs = est_values.get('Pob_mayores', 0.0)
                pob_extran_abs = est_values.get('Pob_extran', 0.0)

                joined_layer.changeAttributeValue(fid, field_indices['Densidad_pob'], densidad)
                joined_layer.changeAttributeValue(fid, field_indices['Total_mujeres'], pob_mujeres_abs)
                joined_layer.changeAttributeValue(fid, field_indices['Total_menor5'], pob_niños_abs)
                joined_layer.changeAttributeValue(fid, field_indices['Total_mayor65'], pob_mayores_abs)
                joined_layer.changeAttributeValue(fid, field_indices['Total_extranjeros'], pob_extran_abs)
            except Exception as e:
                pass

        # 3. Limpieza de campos
        useful_fields = [
            'REFCAT', 'ANTIGUEDAD', 'N_PLANTAS', 'uso', 'num_dw', 'CUSEC',
            'pob_parcela', 'proporcion', 'area_km2', '% hog_unip', '%baja_educ', '%paro', 'Renta_hoga',
            *[f'est_{f}' for f in demographic_fields if f not in direct_fields],
            'Densidad_pob', 'Total_mujeres', 'Total_menor5',
            'Total_mayor65', 'Total_extranjeros'
        ]
        
        useful_lower = [f.lower() for f in useful_fields]
        for field in list(joined_layer.fields()):
            if field.name().lower() not in useful_lower:
                idx = joined_layer.fields().indexFromName(field.name())
                joined_layer.deleteAttribute(idx)
        joined_layer.updateFields()

        if not joined_layer.commitChanges():
            joined_layer.rollBack()
            return

    except Exception as e:
        print(f"Error: {e}")
        joined_layer.rollBack()
        return

    # 4. Guardar en un GeoPackage 
    output_path = project.homePath() + "/Datos_Desagregados_Carraixet.gpkg"
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "Datos_Parcelas_Final"

    error_code, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
        joined_layer, output_path, QgsProject.instance().transformContext(), options)
    
    if error_code == QgsVectorFileWriter.NoError:
        print(f"🚀 ¡PROCESO COMPLETADO CON ÉXITO!")
        print(f"El archivo se ha guardado en tu carpeta de proyecto como: Datos_Desagregados_Carraixet.gpkg")
        iface.addVectorLayer(output_path, "Parcel Data Final Carraixet", "ogr")
    else:
        print(f"arhivo_completo")

run_geoprocess()
