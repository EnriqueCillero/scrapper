from __future__ import annotations

from dataclasses import dataclass

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock
from scraper.parsers.cleaning import clean_scraped_text


@dataclass
class TextBlock(LessonBlock):
    query_selector = '.block-text .fr-view'

    html: str = ''
    text: str = ''

    def _scrape(self) -> None:
        fr = self.locator.locator('.block-text .fr-view').first
        if fr.count():
            self.html = fr.inner_html() or ''
            self.text = fr.inner_text() or ''
        else:
            self.html = self.locator.inner_html() or ''
            self.text = self.locator.inner_text() or ''

        self.html = (self.html or '').strip()
        self.text = clean_scraped_text(self.text or '')

    def _render_md(self, builder, assets_dir=None) -> str:
        md = MarkdownBuilder.build_html(self.html)
        return md if md else (self.text or '')

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if not (self.html or self.text):
            return []
        flows = html_to_flowables(self.html or self.text, builder, assets_dir=assets_dir)
        return flows if flows else (builder.build_paragraph(self.text) if self.text else [])
