from __future__ import annotations

from dataclasses import dataclass, field

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock
from scraper.parsers.cleaning import compact_text


@dataclass
class QuoteCarouselBlock(LessonBlock):
    query_selector = '.block-quote.block-quote--carousel'

    slides: list[str] = field(default_factory=list)

    def _scrape(self) -> None:
        captions = self.locator.locator(
            '.slick-slide:not(.slick-cloned) .block-quote__caption .fr-view'
        )
        if not captions.count():
            captions = self.locator.locator('.block-quote__caption .fr-view')

        slides: list[str] = []
        seen: set[str] = set()
        for i in range(captions.count()):
            caption = captions.nth(i)
            html = (caption.inner_html() if caption.count() else '') or ''
            key = compact_text(caption.text_content() or '')
            if not key or key in seen:
                continue
            seen.add(key)
            slides.append(html.strip())

        self.slides = slides

    def _render_md(self, builder, assets_dir=None) -> str:
        if not self.slides:
            return self.fallback_text

        rendered = [MarkdownBuilder.build_html(html) for html in self.slides]
        return '\n\n'.join(slide for slide in rendered if slide.strip()).strip()

    def _render_pdf(self, builder, assets_dir=None) -> list:
        out: list = []
        for html in self.slides:
            out.extend(html_to_flowables(html, builder, assets_dir=assets_dir))
        return out
