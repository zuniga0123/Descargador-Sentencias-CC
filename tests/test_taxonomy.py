from descargador_sentencias_cc.taxonomy import SIN_CLASIFICAR, classify_area_by_rules


def test_clasifica_salud():
    area = classify_area_by_rules(
        "DERECHO A LA SALUD-Continuidad", None, "Tutela contra una EPS por negar un tratamiento medico."
    )
    assert area == "derecho-a-la-salud"


def test_clasifica_consulta_previa():
    area = classify_area_by_rules(
        "DERECHOS DE LOS PUEBLOS INDIGENAS-Consulta previa", None,
        "Proyecto minero en territorio de una comunidad indigena.",
    )
    assert area == "derechos-etnicos-consulta-previa"


def test_clasifica_laboral():
    area = classify_area_by_rules(
        "DERECHO A LA PENSION-Reconocimiento", None, "Trabajador solicita el reconocimiento de su pension de vejez."
    )
    assert area == "derecho-laboral-seguridad-social"


def test_clasifica_control_abstracto():
    area = classify_area_by_rules(
        "DEMANDA DE INCONSTITUCIONALIDAD-Norma tributaria", None,
        "La Corte declara exequible el articulo demandado.",
    )
    assert area in {"control-constitucionalidad-abstracto", "derecho-constitucional-economico"}


def test_clasifica_debido_proceso_como_fallback_amplio():
    area = classify_area_by_rules(
        "DEBIDO PROCESO-Defecto factico", None, "Accion de tutela contra providencia judicial."
    )
    assert area == "derechos-fundamentales-debido-proceso"


def test_sin_coincidencias_devuelve_none():
    area = classify_area_by_rules(None, None, None)
    assert area is None


def test_texto_no_reconocido_no_usa_sin_clasificar_directamente():
    # classify_area_by_rules nunca devuelve SIN_CLASIFICAR: eso lo decide el pipeline
    # cuando ni las reglas ni la IA (si está activa) resuelven el caso.
    area = classify_area_by_rules("TEMA INVENTADO SIN COINCIDENCIAS", None, "Resumen generico sin palabras clave.")
    assert area is None
    assert area != SIN_CLASIFICAR
