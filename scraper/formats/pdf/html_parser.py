from __future__ import annotations

import html
from pathlib import Path

from bs4 import BeautifulSoup
from reportlab.platypus import Paragraph

from scraper.parsers.cleaning import clean_content_soup

from .builder import PDFBuilder
from .config import PDF_FONT_JETBRAINS
from .utils import link_tag


def _is_visually_hidden(node) -> bool:
    if not hasattr(node, 'get'):
        return False
    classes = node.get('class') or []
    return any('visually-hidden' in str(c) for c in classes)


def _html_inline_to_markup(node) -> str:
    from bs4 import NavigableString

    if isinstance(node, NavigableString):
        return html.escape(str(node))
    if not hasattr(node, 'name') or not node.name:
        return html.escape(str(node))

    if _is_visually_hidden(node):
        return ''

    name = node.name.lower()
    if name == 'br':
        return '<br/>'
    if name in {'strong', 'b'}:
        inner = ''.join(_html_inline_to_markup(c) for c in node.contents)
        return f'<b>{inner}</b>' if inner.strip() else inner
    if name in {'em', 'i'}:
        inner = ''.join(_html_inline_to_markup(c) for c in node.contents)
        return f'<i>{inner}</i>' if inner.strip() else inner
    if name == 'a':
        href = (node.get('href') or '').strip()
        label = ''.join(_html_inline_to_markup(c) for c in node.contents).strip()
        label = label or node.get_text(' ', strip=True)
        if href:
            return link_tag(href, label or href)
        return html.escape(label)
    if name == 'code':
        inner = ''.join(_html_inline_to_markup(c) for c in node.contents)
        return f'<font name="{html.escape(PDF_FONT_JETBRAINS)}">{html.escape(inner)}</font>'
    return ''.join(_html_inline_to_markup(c) for c in node.contents)


def html_to_flowables(
    html_text: str,
    builder: PDFBuilder,
    *,
    assets_dir: Path | None = None,
) -> list:
    soup = BeautifulSoup(html_text or '', 'html.parser')
    clean_content_soup(soup)
    flowables: list = []

    def render_inline(node) -> str:
        from bs4 import NavigableString

        if isinstance(node, NavigableString):
            return html.escape(str(node))
        if not hasattr(node, 'name'):
            return html.escape(str(node))
        return _html_inline_to_markup(node)

    def render_inline_children(tag) -> str:
        return ''.join(render_inline(c) for c in tag.contents)

    def render_block(node):
        if not hasattr(node, 'name') or not node.name:
            txt = str(node).strip()
            if txt:
                flowables.append(Paragraph(html.escape(txt), builder.theme.normal))
            return

        name = node.name.lower()

        if name == 'table':
            rows = node.find_all('tr')
            if rows:
                col_count = max(len(tr.find_all(['th', 'td'])) for tr in rows) if rows else 0
                data = []
                for tr in rows:
                    cells = tr.find_all(['th', 'td'])
                    row = [render_inline_children(c).strip() for c in cells]
                    row.extend([''] * (col_count - len(row)))
                    data.append(row)
                if data:
                    flowables.extend(builder.build_table(data))
            return

        if name in {'ul', 'ol'}:
            items = []
            for li in node.find_all('li', recursive=False):
                txt = render_inline_children(li).strip()
                if txt:
                    items.append(txt)
            if items:
                if name == 'ol':
                    flowables.extend(builder.build_numbered_list(items))
                else:
                    flowables.extend(builder.build_bullet_list(items))
            return

        if name == 'img':
            src = (node.get('src') or '').strip()
            if assets_dir and src:
                path = assets_dir / Path(src).name
                if not path.exists():
                    for p in assets_dir.rglob(Path(src).name):
                        path = p
                        break
                if path.exists():
                    flowables.extend(builder.build_image(path))
            return

        if name in {'div', 'section', 'article'}:
            for child in node.contents:
                render_block(child)
            return

        if name in {'p', 'span'}:
            txt = render_inline_children(node).strip()
            if txt:
                flowables.append(Paragraph(txt, builder.theme.normal))
            return

        if name == 'pre':
            code = node.get_text('\n', strip=False).rstrip('\n')
            if code.strip():
                flowables.extend(builder.build_code_block(code))
            return

        if name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            txt = render_inline_children(node).strip()
            if txt:
                if name in {'h1', 'h2'}:
                    flowables.extend(builder.build_heading(txt))
                else:
                    flowables.extend(builder.build_subheading(txt))
            return

        for child in node.contents:
            if hasattr(child, 'name') and child.name:
                render_block(child)
            else:
                txt = str(child).strip()
                if txt:
                    flowables.append(Paragraph(html.escape(txt), builder.theme.normal))

    for child in soup.contents:
        render_block(child)

    return flowables
