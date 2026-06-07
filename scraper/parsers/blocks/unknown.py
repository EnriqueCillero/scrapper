from __future__ import annotations

from dataclasses import dataclass

from scraper.parsers.blocks.base import LessonBlock
from scraper.parsers.cleaning import clean_scraped_text, is_noise_only_text, is_standalone_slide_index


@dataclass()
class UnknownBlock(LessonBlock):
    # Used as the fallback.

    text: str = ''

    def _scrape(self) -> None:
        self.text = (self.locator.inner_text() or '').strip()
        self.text = clean_scraped_text(self.text)
        if is_noise_only_text(self.text) or is_standalone_slide_index(self.text):
            self.skip = True
            self.text = ''

    def _render_md(self, builder, assets_dir=None) -> str:
        return self.text

    def _render_pdf(self, builder, assets_dir=None) -> list:
        return builder.build_paragraph(self.text) if self.text else []
