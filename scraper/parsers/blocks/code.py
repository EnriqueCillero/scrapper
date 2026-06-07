from __future__ import annotations

from dataclasses import dataclass

from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

from scraper.formats.md import MarkdownBuilder
from scraper.parsers.blocks.base import LessonBlock
from scraper.parsers.cleaning import remove_line_number_prefix


def _guess_language_name(code: str) -> str | None:
    try:
        lexer = guess_lexer(code)
    except ClassNotFound:
        return None
    aliases = getattr(lexer, 'aliases', None) or []
    return aliases[0] if aliases else getattr(lexer, 'name', None)


def _md_lang_tag(language_name: str | None) -> str | None:
    if not language_name:
        return None

    raw = language_name.strip()
    if not raw:
        return None

    overrides = {
        'Batchfile': 'bat',
        'C#': 'csharp',
        'C++': 'cpp',
        'CoffeeScript': 'coffeescript',
        'Dockerfile': 'dockerfile',
        'F#': 'fsharp',
        'JavaScript': 'javascript',
        'Objective-C': 'objectivec',
        'PowerShell': 'powershell',
        'Shell': 'bash',
        'TypeScript': 'typescript',
        'Visual Basic': 'vb',
    }
    if raw in overrides:
        return overrides[raw]

    return raw.lower().replace(' ', '')


@dataclass
class CodeBlock(LessonBlock):
    query_selector = 'pre.block-text__code, .block-text--code'

    code: str = ''
    lang: str | None = None

    def _scrape(self) -> None:
        pre = self.locator.locator('pre.block-text__code').first
        code = pre.text_content() if pre.count() else self.locator.text_content()
        code = (code or '').rstrip('\n\r\t')
        code = remove_line_number_prefix(code)
        self.code = code

        lang: str | None = None
        if code.strip():
            try:
                lang = _md_lang_tag(_guess_language_name(code))
            except Exception:
                lang = None

        self.lang = lang

    def _render_md(self, builder, assets_dir=None) -> str:
        return MarkdownBuilder.build_code_block(self.code, self.lang)

    def _render_pdf(self, builder, assets_dir=None) -> list:
        return builder.build_code_block(self.code, self.lang) if self.code else []
