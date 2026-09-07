from qgis.core import *
from qgis.utils import iface

def run_fast_normalization():
    # 1. Coger la capa activa 
    layer = iface.activeLayer()
    
    if not layer:
        print("capa_parcela")
        return
        
    print(f"capa_parcela")

    # Definir variables de origen
    linear_fields = ['est_Densidad_h', 'est_Pob_mujere', 'est_Pob_niños', 'est_Pob_mayores', 'est_Pob_extran', '% hog_unip', '%baja_educ', '%paro']
    inverse_fields = ['Renta_hoga']
    fuzzy_fields = ['ANTIGUEDAD', 'N_PLANTAS']
    
    # Comprobación de que existan los campos en la tabla
    capa_fields = [f.name() for f in layer.fields()]
    missing_fields = [f for f in (linear_fields + inverse_fields + fuzzy_fields) if f not in capa_fields]
    
    if missing_fields:
        print(f"ERROR: Campos no encontrados: {missing_fields}")
        print("campos", capa_fields)
        return

    # Crear los campos '_norm'
    all_norm_fields = [f"{f}_norm" for f in linear_fields + inverse_fields] + ['antig_norm', 'plantas_norm']
    
    new_fields = []
    for f_norm in all_norm_fields:
        if f_norm not in capa_fields:
            new_fields.append(QgsField(f_norm, QVariant.Double))
            
    if new_fields:
        layer.dataProvider().addAttributes(new_fields)
        layer.updateFields()

    # Pre-calcular mínimos y máximos para que vaya más rápido
    stats = {}
    for field in linear_fields + inverse_fields:
        idx = layer.fields().indexFromName(field)
        stats[field] = {
            'min': float(layer.minimumValue(idx) or 0),
            'max': float(layer.maximumValue(idx) or 1)
        }

    # Obtener los índices de los campos destino
    field_indices = {f: layer.fields().indexFromName(f) for f in all_norm_fields}

    # --- abre y cierra la edición en bloque
    with edit(layer):
        for feature in layer.getFeatures():
            fid = feature.id()
            attrs_to_change = {} # Guardamos los cambios en memoria antes de aplicar
            
            # A) Min-Max Directo
            for field in linear_fields:
                val = feature[field]
                f_min = stats[field]['min']
                f_max = stats[field]['max']
                if val is not None and val != NULL and f_max != f_min:
                    norm_val = (float(val) - f_min) / (f_max - f_min)
                    attrs_to_change[field_indices[f"{field}_norm"]] = max(0.0, min(1.0, float(norm_val)))
                else:
                    attrs_to_change[field_indices[f"{field}_norm"]] = 0.0

            # B) Min-Max Inverso (Renta)
            for field in inverse_fields:
                val = feature[field]
                f_min = stats[field]['min']
                f_max = stats[field]['max']
                if val is not None and val != NULL and f_max != f_min:
                    norm_val = (f_max - float(val)) / (f_max - f_min)
                    attrs_to_change[field_indices[f"{field}_norm"]] = max(0.0, min(1.0, float(norm_val)))
                else:
                    attrs_to_change[field_indices[f"{field}_norm"]] = 0.0

            # C) Lógica Borrosa: Antigüedad
            try:
                val_antig = feature['ANTIGUEDAD']
                if val_antig == NULL or val_antig is None:
                    attrs_to_change[field_indices['antig_norm']] = 0.0
                else:
                    year = float(val_antig)
                    if year <= 1940: f_antig = 1.0
                    elif year >= 2000: f_antig = 0.0
                    else: f_antig = (2000 - year) / (2000 - 1940)
                    attrs_to_change[field_indices['antig_norm']] = float(f_antig)
            except:
                attrs_to_change[field_indices['antig_norm']] = 0.0

            # D) Lógica Borrosa: Plantas
            try:
                val_plantas = feature['N_PLANTAS']
                if val_plantas == NULL or val_plantas is None:
                    attrs_to_change[field_indices['plantas_norm']] = 0.0
                else:
                    plantas = float(val_plantas)
                    if plantas <= 1: f_plantas = 1.0
                    elif plantas >= 4: f_plantas = 0.0
                    else: f_plantas = (4 - plantas) / (4 - 1)
                    attrs_to_change[field_indices['plantas_norm']] = float(f_plantas)
            except:
                attrs_to_change[field_indices['plantas_norm']] = 0.0

            # Aplicar todos los cambios de esta parcela de una sola vez
            layer.changeAttributeValues(fid, attrs_to_change)

    print("capa_normalizada")

run_fast_normalization()
