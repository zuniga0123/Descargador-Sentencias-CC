"""Estructuras de datos compartidas por el pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Una fila de la página/exportación de resultados del buscador de Relatoría."""

    radicado: str
    url_ficha: str
    fecha_sentencia: str | None = None
    fecha_publicacion: str | None = None
    sala: str | None = None
    ponente: str | None = None
    tema_oficial: str | None = None
    subtema_oficial: str | None = None
    resumen: str | None = None

    @property
    def tipo_providencia(self) -> str:
        """Prefijo del radicado (T, C, SU, A, ...) que indica el tipo de providencia."""
        prefijo = self.radicado.split("-", 1)[0]
        return prefijo.upper()


@dataclass
class Providencia:
    """Un SearchResult ya descargado y clasificado, listo para persistir."""

    resultado: SearchResult
    contenido_html: str
    hash_contenido: str
    area_slug: str
    area_label: str
    area_metodo: str  # 'regla' | 'ia' | 'sin_clasificar'
    tema_slug: str
    subtema_slug: str | None
    ruta_archivo: str
    fecha_descarga: str
    extras: dict = field(default_factory=dict)
