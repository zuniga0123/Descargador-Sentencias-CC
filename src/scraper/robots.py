"""Verificación de robots.txt.

Ya se revisó manualmente el robots.txt de corteconstitucional.gov.co (2026-08-09):
`/relatoria/` está explícitamente permitido (Allow) y no aparece en ningún Disallow.
Esta función deja una verificación programática como salvaguarda para automatización
futura (cron), por si el sitio cambia sus reglas.
"""

from __future__ import annotations

import logging
from urllib.robotparser import RobotFileParser

from src import config

logger = logging.getLogger(__name__)


def is_allowed(url: str, user_agent: str = config.USER_AGENT) -> bool:
    parser = RobotFileParser()
    parser.set_url(config.ROBOTS_URL)
    try:
        parser.read()
    except OSError:
        logger.warning("No se pudo leer robots.txt; se asume permitido pero revise manualmente.")
        return True
    return parser.can_fetch(user_agent, url)
