from descargador_sentencias_cc.utils import normalize_key, slugify, strip_accents


def test_strip_accents():
    assert strip_accents("Límites") == "Limites"
    assert strip_accents("Niñez") == "Ninez"


def test_slugify():
    assert slugify("Libertad de Expresión-Límites") == "libertad-de-expresion-limites"
    assert slugify("") == "sin-clasificar"
    assert slugify(None) == "sin-clasificar"
    assert slugify("Salud", default="otro") == "salud"


def test_normalize_key():
    assert normalize_key("Fecha de Publicación") == "fechadepublicacion"
    assert normalize_key("RADICADO") == "radicado"
