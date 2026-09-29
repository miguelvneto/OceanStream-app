"""Interpretação de versões e destinos de atualização, sem dependências de UI."""

import json
import re
from itertools import zip_longest

APP_STORE_ID = None
PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream"
MAX_VERSION_LENGTH = 256
MAX_RESPONSE_LENGTH = 4096


def normalize_version(value):
    """Retorna componentes numéricos ou None para uma entrada inválida."""
    if not isinstance(value, str) or len(value) > MAX_VERSION_LENGTH:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1].strip()
    if value.startswith(("v", "V")):
        value = value[1:]
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", value):
        return None
    return tuple(int(part) for part in value.split("."))


def tem_atualizacao(current, available):
    """Compara versões; valores inválidos nunca indicam atualização."""
    current = normalize_version(current)
    available = normalize_version(available)
    if current is None or available is None:
        return False
    for old, new in zip_longest(current, available, fillvalue=0):
        if old != new:
            return new > old
    return False


def parse_version_response(body):
    """Aceita corpo HTTP textual: objeto JSON, JSON string ou versão simples."""
    if not isinstance(body, str) or len(body) > MAX_RESPONSE_LENGTH:
        return None
    body = body.strip()
    try:
        data = json.loads(body)
    except (ValueError, RecursionError):
        data = body
    if isinstance(data, dict):
        candidates = (data.get("version"), data.get("latest_version"))
    elif isinstance(data, str):
        candidates = (data,)
    else:
        # 0.4 é ambíguo: validar o texto original, nunca converter o float.
        # Exigir ponto neste fallback mantém o número isolado 42 inválido.
        candidates = (body,) if "." in body else ()
    for value in candidates:
        parts = normalize_version(value)
        if parts is not None:
            return ".".join(str(part) for part in parts)
    return None


def store_urls(platform, app_store_id=None):
    """Retorna destinos conhecidos, ou uma tupla vazia se faltar o ID iOS."""
    if platform != "ios":
        return (PLAY_STORE_URL,)
    if (not isinstance(app_store_id, str)
            or not re.fullmatch(r"[1-9][0-9]{0,19}", app_store_id)):
        return ()
    return (
        "itms-apps://itunes.apple.com/app/id" + app_store_id,
        "https://apps.apple.com/app/id" + app_store_id,
    )
