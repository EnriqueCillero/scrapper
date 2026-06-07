from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from scraper.parsers.cleaning import clean_content_soup, clean_scraped_text


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html or '', 'html.parser')
    clean_content_soup(soup)
    parts: list[str] = []
    for child in soup.contents:
        out = _render_node_as_blocks(child)
        if out:
            parts.extend(out)
    return clean_scraped_text(_join_blocks(parts))


def _render_node_as_blocks(node) -> list[str]:
    if isinstance(node, NavigableString):
        text = str(node).strip()
        return [text] if text else []

    if not isinstance(node, Tag):
        return []

    name = node.name.lower()

    if name == 'p':
        txt = _render_inline(node).strip()
        return [txt] if txt else []

    if name in {'ul', 'ol'}:
        return _render_html_list(node)

    if name == 'table':
        md = _render_html_table(node)
        return [md] if md else []

    if name == 'pre':
        code = node.get_text('\n', strip=False).rstrip('\n')
        if not code.strip():
            return []
        return [f'```\n{code}\n```']

    if name in {'div', 'section', 'article', 'span'}:
        parts: list[str] = []
        for child in node.contents:
            parts.extend(_render_node_as_blocks(child))
        return parts

    txt = _render_inline(node).strip()
    return [txt] if txt else []


def _is_visually_hidden(node) -> bool:
    if not isinstance(node, Tag):
        return False
    classes = node.get('class') or []
    return any('visually-hidden' in str(c) for c in classes)


def _render_inline(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ''

    if _is_visually_hidden(node):
        return ''

    name = node.name.lower()

    if name == 'br':
        return '\n'

    if name in {'strong', 'b'}:
        inner = _render_inline_children(node).strip()
        return f'**{inner}**' if inner else ''

    if name in {'em', 'i'}:
        inner = _render_inline_children(node).strip()
        return f'*{inner}*' if inner else ''

    if name == 'code':
        inner = _render_inline_children(node).strip().replace('`', r'\`')
        return f'`{inner}`' if inner else ''

    if name == 'a':
        label = _render_inline_children(node).strip() or node.get_text(' ', strip=True)
        href = (node.get('href') or '').strip()
        if href:
            return f'[{label}]({href})'
        return label

    if name in {'p', 'li'}:
        return _render_inline_children(node)

    return _render_inline_children(node)


def _render_inline_children(tag: Tag) -> str:
    pieces = [_render_inline(child) for child in tag.contents]
    out: list[str] = []

    for piece in pieces:
        if not piece:
            continue

        if out:
            prev = out[-1]
            if prev.endswith('**') and piece[:1] and not piece[:1].isspace() and piece[:1].isalnum():
                out[-1] = prev + ' '

        out.append(piece)

    return ''.join(out)


def _render_html_list(list_tag: Tag, *, indent: int = 0) -> list[str]:
    ordered = list_tag.name.lower() == 'ol'
    items: list[str] = []
    i = 1

    for li in list_tag.find_all('li', recursive=False):
        bullet = f'{i}.' if ordered else '-'
        i += 1

        chunks: list[str] = []
        for child in li.contents:
            if isinstance(child, Tag) and child.name and child.name.lower() in {'ul', 'ol'}:
                continue
            chunks.append(_render_inline(child))
        line = ' '.join(''.join(chunks).split())
        prefix = ('  ' * indent) + f'{bullet} '
        if line.strip():
            items.append(prefix + line.strip())

        for nested in li.find_all(['ul', 'ol'], recursive=False):
            items.extend(_render_html_list(nested, indent=indent + 1))

    return ['\n'.join(items).rstrip()] if items else []


def _render_html_table(table: Tag) -> str:
    rows = table.find_all('tr')
    if not rows:
        return ''

    def cell_text(cell: Tag) -> str:
        txt = cell.get_text(' ', strip=True)
        return txt.replace('|', r'\|')

    parsed_rows: list[list[str]] = []
    for r in rows:
        cells = r.find_all(['th', 'td'], recursive=False) or r.find_all(['th', 'td'])
        parsed_rows.append([cell_text(c) for c in cells])

    col_count = max((len(r) for r in parsed_rows), default=0)
    if col_count == 0:
        return ''

    for r in parsed_rows:
        r.extend([''] * (col_count - len(r)))

    header = parsed_rows[0]
    body = parsed_rows[1:]
    h = header + [''] * (col_count - len(header))

    def fmt_row(r: list[str]) -> str:
        row = r + [''] * (col_count - len(r))
        return '| ' + ' | '.join(c.replace('|', r'\|') for c in row) + ' |'

    lines = [fmt_row(h), '| ' + ' | '.join(['---'] * col_count) + ' |']
    lines.extend(fmt_row(r) for r in body)
    return '\n'.join(lines)


def _join_blocks(blocks: list[str]) -> str:
    cleaned = [b.strip() for b in blocks if b and b.strip()]
    return '\n\n'.join(cleaned)
