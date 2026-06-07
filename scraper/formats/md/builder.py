from __future__ import annotations

from pathlib import Path

from scraper.formats.base import CourseBuilder
from scraper.parsers.cleaning import clean_markdown_output

from .html_parser import html_to_markdown


class MarkdownBuilder(CourseBuilder):
    def __init__(
        self,
        output_path: Path | None = None,
        elements: list[str] | None = None,
    ) -> None:
        self.output_path = output_path
        self.elements: list[str] = elements if elements is not None else []

    def add_elements(self, chunks: str | list[str]) -> None:
        if isinstance(chunks, str):
            self.elements.append(chunks)
        else:
            self.elements.extend(chunks)

    def build(self) -> None:
        if self.output_path is not None:
            content = '\n\n'.join(c for c in self.elements if c is not None).rstrip() + '\n'
            self.output_path.write_text(clean_markdown_output(content), encoding='utf-8')

    @staticmethod
    def build_heading(level: int, text: str) -> str:
        h = min(max(level, 1), 6)
        return f'{"#" * h} {text}'.strip()

    @staticmethod
    def build_spacer() -> str:
        return ''

    @staticmethod
    def build_html(html: str) -> str:
        return html_to_markdown(html or '').strip()

    @staticmethod
    def build_numbered_item(num: str, body: str) -> str:
        prefix = f'{num}. '
        lines = body.splitlines() if body else ['']
        if not lines:
            return prefix.rstrip()
        out = [prefix + lines[0].strip()]
        indent = ' ' * len(prefix)
        for ln in lines[1:]:
            out.append((indent + ln) if ln.strip() else '')
        return '\n'.join(out).rstrip()

    @staticmethod
    def build_bullet_item(title: str, body: str) -> str:
        lines: list[str] = [f'- **{title}**  ']
        if body:
            for ln in body.splitlines():
                lines.append(('  ' + ln) if ln.strip() else '')
        return '\n'.join(lines).rstrip()

    @staticmethod
    def build_bullet_list(items: list[str]) -> str:
        return '\n'.join(f'- {s.strip()}' for s in items if s and s.strip()).strip()

    def build_numbered_list(self, items: list[str]) -> str:
        lines: list[str] = []
        for i, s in enumerate((s for s in items if s and s.strip()), start=1):
            lines.append(f'{i}. {s.strip()}')
        return '\n'.join(lines).strip()

    @staticmethod
    def build_link_callout(body: str, href: str | None) -> str:
        lines: list[str] = []
        body = (body or '').strip()
        if body:
            for ln in body.splitlines():
                lines.append(f'> {ln}'.rstrip())
        if href:
            if lines:
                lines.append('>')
            lines.append(f'> [Link]({href})')
        return '\n'.join(lines).strip()

    @staticmethod
    def build_image(alt: str, path: str) -> str:
        return f'![{alt or "image"}]({path})'

    @staticmethod
    def build_code_block(code: str, lang: str | None = None) -> str:
        fence = f'```{lang}' if lang else '```'
        return f'{fence}\n{code}\n```'

    @staticmethod
    def build_table(headers: list[str], rows: list[list[str]]) -> str:
        col_count = max(len(headers), max((len(r) for r in rows), default=0))
        if col_count == 0:
            return ''
        h = headers + [''] * (col_count - len(headers))

        def fmt_row(r: list[str]) -> str:
            row = r + [''] * (col_count - len(r))
            return '| ' + ' | '.join(c.replace('|', r'\|') for c in row) + ' |'

        lines = [fmt_row(h), '| ' + ' | '.join(['---'] * col_count) + ' |']
        lines.extend(fmt_row(r) for r in rows)
        return '\n'.join(lines)
