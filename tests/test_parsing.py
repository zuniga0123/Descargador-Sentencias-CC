from pathlib import Path

from descargador_sentencias_cc.parsing import (
    enrich_with_ficha,
    extract_tema_subtema_ficha,
    find_export_excel_link,
    find_ficha_links,
    parse_resultados_table,
    split_tema_subtema,
)

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://www.corteconstitucional.gov.co/relatoria/buscador_new/"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_find_ficha_links_extrae_radicados_unicos():
    html = _read("resultados_sample.html")
    links = find_ficha_links(html, BASE_URL)
    radicados = [r for r, _url in links]
    assert radicados == ["T-388-19", "C-123-20"]
    assert links[0][1].endswith("/relatoria/2019/T-388-19.htm")


def test_parse_resultados_table_extrae_campos():
    html = _read("resultados_sample.html")
    resultados = parse_resultados_table(html, BASE_URL)
    assert len(resultados) == 2

    primero = resultados[0]
    assert primero.radicado == "T-388-19"
    assert primero.tipo_providencia == "T"
    assert "LIBERTAD DE EXPRESION" in primero.tema_oficial
    assert "tutela" in primero.resumen
    assert primero.fecha_sentencia == "2019-08-22"
    assert primero.fecha_publicacion == "2019-09-10"

    segundo = resultados[1]
    assert segundo.radicado == "C-123-20"
    assert segundo.tipo_providencia == "C"


def test_find_export_excel_link():
    html = _read("resultados_sample.html")
    link = find_export_excel_link(html, BASE_URL)
    assert link is not None
    assert "exportar_excel" in link


def test_split_tema_subtema():
    tema, subtema = split_tema_subtema("LIBERTAD DE EXPRESION DE IDEAS Y OPINIONES-Limites")
    assert tema == "LIBERTAD DE EXPRESION DE IDEAS Y OPINIONES"
    assert subtema == "Limites"


def test_split_tema_subtema_sin_guion():
    tema, subtema = split_tema_subtema("DERECHO A LA IGUALDAD")
    assert tema == "DERECHO A LA IGUALDAD"
    assert subtema is None


def test_extract_tema_subtema_ficha():
    html = _read("ficha_sample.html")
    pares = extract_tema_subtema_ficha(html)
    assert pares == [("LIBERTAD DE EXPRESION DE IDEAS Y OPINIONES", "Limites")]


def test_enrich_with_ficha_completa_subtema_faltante():
    resultados = parse_resultados_table(_read("resultados_sample.html"), BASE_URL)
    primero = resultados[0]
    assert primero.subtema_oficial is None  # el listado no trae subtema separado

    enriquecido = enrich_with_ficha(primero, _read("ficha_sample.html"))
    assert enriquecido.subtema_oficial == "Limites"
    assert enriquecido.tema_oficial == primero.tema_oficial  # no se pisa lo ya conocido
