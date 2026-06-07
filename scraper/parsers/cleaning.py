from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from bs4.element import Tag

_PLAYER_TEXT_PATTERNS = (
    'reproductor de video se esta cargando',
    'reproductor de video se está cargando',
    'reproducir video',
    'reproducir vídeo',
    'reproducir',
    'cargado:',
    'tiempo restante',
    'playback rate',
    'subtitulos especiales',
    'subtítulos especiales',
    'imagen sobre imagen',
    'pantalla completa',
    'desactivar el sonido',
    'activar el sonido',
    'this is a modal window',
)

_PLAYER_CLASS_PARTS = (
    'mejs',
    'plyr',
    'vjs',
    'video-js',
    'video-player',
    'media-player',
    'player-controls',
    'playback-rate',
    'fullscreen',
)


def compact_text(text: str) -> str:
    return ' '.join((text or '').split())


def _normalize_for_matching(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text or '')
    without_marks = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return without_marks.lower()


def is_line_number_run(text: str) -> bool:
    value = compact_text(text)
    if not value:
        return False
    parts = value.split()
    if len(parts) >= 3 and all(part.isdigit() for part in parts):
        numbers = [int(part) for part in parts]
        return numbers == list(range(numbers[0], numbers[0] + len(numbers)))
    compact = re.sub(r'\s+', '', value)
    for end in range(3, 200):
        if compact == ''.join(str(i) for i in range(1, end + 1)):
            return True
        if len(''.join(str(i) for i in range(1, end + 1))) > len(compact):
            break
    return False


def is_player_noise_text(text: str) -> bool:
    normalized = _normalize_for_matching(compact_text(text))
    if not normalized:
        return False
    if is_line_number_run(normalized):
        return True
    return any(_normalize_for_matching(pattern) in normalized for pattern in _PLAYER_TEXT_PATTERNS)


def remove_line_number_runs(text: str) -> str:
    cleaned = text or ''
    for end in range(200, 2, -1):
        run = ''.join(str(i) for i in range(1, end + 1))
        cleaned = cleaned.replace(run, '')
    cleaned = re.sub(r'(?m)^\s*(?:\d+\s+){2,}\d+\s*$', '', cleaned)
    return cleaned


def clean_scraped_text(text: str) -> str:
    cleaned = remove_line_number_runs(text or '')
    cleaned = re.sub(r'(?<!\d)[2-9](?=\d\.[a-z]\b)', '', cleaned)
    cleaned = re.sub(
        r'(^|[\n ]+)\d{1,3}(?=[A-ZÁÉÍÓÚ][^\n]*|En\s|El\s)',
        r'\1',
        cleaned,
    )
    cleaned = re.sub(
        r'Reproductor de video se est[áa] cargando\..*?This is a modal window\.',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r'Reproducir V[íi]deoReproducirCargado:\s*0%.*?Desactivar el sonido',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(r'\bStep\s+\d+\s+Title\b', '', cleaned, flags=re.IGNORECASE)
    for phrase in _PLAYER_TEXT_PATTERNS:
        cleaned = re.sub(re.escape(phrase), '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(Enunciado|Soluciones)(?=\d)', r'\1 ', cleaned)
    cleaned = re.sub(r'(?<=[.!?])(?=\d{1,3}[a-z]\.)', ' ', cleaned)
    cleaned = re.sub(r'(?<!\S)\d{1,3}(?=\s+(?:Video|Enunciado|Soluciones)\b)', '', cleaned)
    cleaned = re.sub(r'[ \t\xa0]{2,}', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def is_noise_only_text(text: str) -> bool:
    lines = [compact_text(line) for line in (text or '').splitlines()]
    lines = [line for line in lines if line]
    return bool(lines) and all(is_player_noise_text(line) for line in lines)


def is_standalone_slide_index(text: str) -> bool:
    value = compact_text(text)
    return value.isdigit() and 1 <= int(value) <= 999


def clean_markdown_output(markdown: str) -> str:
    cleaned = clean_scraped_text(markdown or '')
    cleaned = re.sub(
        r'(?m)^\s*(?:\d+\.\s+)?!\[[^\]]*]\(assets/[^)\n]*\.mp4\.0000000\.jpg\)\s*\n'
        r'(?=\s*<video\b)',
        '',
        cleaned,
    )
    cleaned = re.sub(r'(?m)^\s+(<video\b)', r'\1', cleaned)
    cleaned = re.sub(
        r'<video controls preload="metadata" (?!style=)',
        '<video controls preload="metadata" '
        'style="display:block;width:100%;max-width:960px;height:auto;margin:0.75rem 0;" ',
        cleaned,
    )
    cleaned = re.sub(r'(?m)^\s*\d{1,3}\s*$', '', cleaned)
    cleaned = re.sub(r'(?m)^(\d{1,3}\.[a-z])\s+\d{1,3}\s*$', r'\1', cleaned)
    cleaned = re.sub(r'(?m)(\S)\s+\d{1,3}\s*$', r'\1', cleaned)
    cleaned = re.sub(r'(?<!\S)\d{1,3}(?=\s+\d{1,3}\.[a-z]\b)', '', cleaned)
    cleaned = re.sub(r'(?<=[.!?])\s+\d{1,3}\s+(?=[A-ZÁÉÍÓÚ])', ' ', cleaned)
    cleaned = re.sub(
        r'\b(Video Solución [^\n]*?)\s+\d{1,3}'
        r'(?=[A-ZÁÉÍÓÚa-záéíóú]|\s+[A-ZÁÉÍÓÚa-záéíóú]|\s*$)',
        r'\1',
        cleaned,
    )
    cleaned = re.sub(r'\b(Soluciones)\s+\d{1,3}\s+(?=[A-ZÁÉÍÓÚ])', r'\1\n\n', cleaned)
    cleaned = re.sub(r'\b(Soluciones)(?=[A-ZÁÉÍÓÚ])', r'\1\n\n', cleaned)
    cleaned = re.sub(r'\b(Soluciones)\s+(?=[A-ZÁÉÍÓÚ])', r'\1\n\n', cleaned)
    cleaned = re.sub(r'\b(Soluciones)\s*(?=\n?##)', r'\1\n\n', cleaned)
    cleaned = re.sub(r'\b(Video Solución [\d.a-z, y]+)(?=\s+[A-ZÁÉÍÓÚ])', r'\1\n\n', cleaned)
    cleaned = re.sub(r'(?<=[.!?])\s*(\d{1,3}\.[a-z]\b)', r'\n\n\1', cleaned)
    cleaned = re.sub(
        r'\b(Enunciado|Soluciones)\s+((?:\d{1,3}\.[a-z]\s+))',
        lambda m: f'{m.group(1)}\n\n{m.group(2)}',
        cleaned,
    )

    blocks = [block.strip() for block in re.split(r'\n{2,}', cleaned)]
    deduped: list[str] = []
    seen_in_section: set[str] = set()
    for block in blocks:
        if not block:
            continue
        if block.startswith('#'):
            seen_in_section.clear()
            deduped.append(block)
            continue
        key = compact_text(block)
        if key in seen_in_section and len(key) > 30:
            continue
        seen_in_section.add(key)
        deduped.append(block)

    out = '\n\n'.join(deduped)
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.rstrip() + '\n'


def remove_line_number_prefix(code: str) -> str:
    lines = (code or '').splitlines()
    if len(lines) >= 2 and is_line_number_run(lines[0]):
        return '\n'.join(lines[1:]).lstrip('\n')
    return code


def _class_values(tag: Tag) -> Iterable[str]:
    classes = tag.get('class') or []
    for cls in classes:
        yield str(cls).lower()


def is_hidden_or_player_control(tag: Tag) -> bool:
    classes = tuple(_class_values(tag))
    if any('visually-hidden' in cls or 'sr-only' in cls for cls in classes):
        return True
    if any(part in cls for cls in classes for part in _PLAYER_CLASS_PARTS):
        return True

    attrs = ' '.join(
        str(tag.get(attr) or '').lower()
        for attr in ('aria-label', 'role', 'title', 'data-title')
    )
    return any(pattern in attrs for pattern in _PLAYER_TEXT_PATTERNS)


def clean_content_soup(soup) -> None:
    for tag in list(soup.find_all(True)):
        if is_hidden_or_player_control(tag):
            tag.decompose()
