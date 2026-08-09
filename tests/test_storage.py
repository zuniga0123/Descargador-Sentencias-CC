from descargador_sentencias_cc import storage
from descargador_sentencias_cc.models import Providencia, SearchResult


def _providencia(radicado="T-388-19", fecha_publicacion="2019-09-10"):
    resultado = SearchResult(
        radicado=radicado,
        url_ficha=f"https://www.corteconstitucional.gov.co/relatoria/2019/{radicado}.htm",
        fecha_sentencia="2019-08-22",
        fecha_publicacion=fecha_publicacion,
        tema_oficial="LIBERTAD DE EXPRESION DE IDEAS Y OPINIONES",
        subtema_oficial="Limites",
        resumen="Resumen de prueba.",
    )
    return Providencia(
        resultado=resultado,
        contenido_html="<html>contenido</html>",
        hash_contenido="deadbeef",
        area_slug="derechos-fundamentales-debido-proceso",
        area_label="Derechos Fundamentales y Debido Proceso",
        area_metodo="regla",
        tema_slug="libertad-de-expresion-de-ideas-y-opiniones",
        subtema_slug="limites",
        ruta_archivo="/tmp/no-usado.htm",
        fecha_descarga="2026-08-09T00:00:00+00:00",
    )


def test_build_output_dir_crea_estructura_area_tema_subtema(tmp_path):
    path = storage.build_output_dir(
        tmp_path, "derecho-a-la-salud", "CONTINUIDAD EN EL SERVICIO", "EPS"
    )
    assert path.exists()
    assert path.parts[-3:] == ("derecho-a-la-salud", "continuidad-en-el-servicio", "eps")


def test_build_output_dir_sin_subtema(tmp_path):
    path = storage.build_output_dir(tmp_path, "derecho-a-la-salud", "SALUD", None)
    assert path.name == "salud"
    assert path.parent.name == "derecho-a-la-salud"


def test_save_providencia_files(tmp_path):
    dir_path = tmp_path / "area" / "tema"
    dir_path.mkdir(parents=True)
    ruta_html = storage.save_providencia_files(dir_path, "T-388-19", "<html>x</html>", {"radicado": "T-388-19"})

    assert ruta_html.exists()
    assert ruta_html.name == "T-388-19.htm"
    assert (dir_path / "T-388-19_metadata.json").exists()
    assert ruta_html.read_text(encoding="utf-8") == "<html>x</html>"


def test_ciclo_completo_sqlite(tmp_path):
    db_path = tmp_path / "indice.sqlite"
    conn = storage.get_connection(db_path)
    storage.init_db(conn)

    assert storage.providencia_existe(conn, "T-388-19") is False
    assert storage.get_ultima_fecha_publicacion(conn) is None

    storage.upsert_providencia(conn, _providencia())
    assert storage.providencia_existe(conn, "T-388-19") is True
    assert storage.get_ultima_fecha_publicacion(conn) == "2019-09-10"

    # Upsert con la misma radicación no debe duplicar la fila.
    storage.upsert_providencia(conn, _providencia(fecha_publicacion="2019-10-01"))
    cur = conn.execute("SELECT COUNT(*) AS n FROM providencias")
    assert cur.fetchone()["n"] == 1
    assert storage.get_ultima_fecha_publicacion(conn) == "2019-10-01"

    conn.close()
