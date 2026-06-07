from __future__ import annotations

from dataclasses import dataclass, field

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock
from scraper.parsers.cleaning import compact_text


@dataclass
class BulletedListBlock(LessonBlock):
    query_selector = '.block-list.block-list--bulleted'

    items: list[str] = field(default_factory=list)

    def _scrape(self) -> None:
        lis = self.locator.locator('ul.block-list__list > li.block-list__item')
        if not lis.count():
            lis = self.locator.locator('.block-list--bulleted li.block-list__item')

        items: list[str] = []
        seen: set[str] = set()
        for i in range(lis.count()):
            li = lis.nth(i)
            fr = li.locator(
                '.block-list__content:not(.hidden):not([aria-hidden="true"]) .fr-view'
            ).first
            if not fr.count():
                fr = li.locator('.block-list__content .fr-view').last

            html = (fr.inner_html() if fr.count() else '') or ''
            key = compact_text(fr.text_content() or '') if fr.count() else ''
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(html.strip())

        self.items = items

    def _render_md(self, builder, assets_dir=None) -> str:
        if not self.items:
            return self.fallback_text

        rendered: list[str] = []
        for html in self.items:
            md = MarkdownBuilder.build_html(html)
            if md:
                rendered.append(f'- {md}')
        return '\n'.join(rendered).strip()

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if not self.items:
            return []
        items_flows = [html_to_flowables(html, builder, assets_dir=assets_dir) for html in self.items]
        return builder.build_bullet_list_with_content(items_flows)
