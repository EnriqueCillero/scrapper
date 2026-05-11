from __future__ import annotations

from dataclasses import dataclass, field

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock


@dataclass
class FlashcardsBlock(LessonBlock):
    query_selector = '.block-flashcards'

    cards: list[tuple[str, str]] = field(default_factory=list)  # (front_title, back_html)

    def _scrape(self) -> None:
        cards: list[tuple[str, str]] = []

        flashcards = self.locator.locator('li.flashcard')
        for i in range(flashcards.count()):
            li = flashcards.nth(i)

            front_fr = li.locator('.flashcard-side--front .fr-view').first
            front_text = (front_fr.text_content() or '').strip() if front_fr.count() else ''
            front_text = ' '.join(front_text.split())
            if not front_text:
                continue

            back_fr = li.locator('.flashcard-side--back .fr-view').first
            back_html = back_fr.inner_html() if back_fr.count() else ''
            cards.append((front_text, (back_html or '').strip()))

        self.cards = cards

    def _render_md(self, builder, assets_dir=None) -> str:
        if not self.cards:
            return self.fallback_text

        lines: list[str] = []
        for title, back_html in self.cards:
            back_md = MarkdownBuilder.build_html(back_html)
            lines.append(MarkdownBuilder.build_bullet_item(title, back_md))
        return '\n'.join(lines).strip()

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if not self.cards:
            return []
        items_with_content: list[tuple[str, list]] = []
        for title, back_html in self.cards:
            back_flows = html_to_flowables(back_html or '', builder, assets_dir=assets_dir)
            items_with_content.append((title, back_flows))
        return builder.build_bullet_list_with_content(items_with_content)
