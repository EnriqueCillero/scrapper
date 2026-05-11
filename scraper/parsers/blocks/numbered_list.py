from __future__ import annotations

from dataclasses import dataclass, field

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock


@dataclass
class NumberedListBlock(LessonBlock):
    query_selector = '.block-list.block-list--numbered'

    items: list[tuple[str, str]] = field(default_factory=list)  # (num, item_html)

    def _scrape(self) -> None:
        items: list[tuple[str, str]] = []

        lis = self.locator.locator('ol.block-list__list > li.block-list__item--numbered')
        if not lis.count():
            lis = self.locator.locator('.block-list--numbered li.block-list__item--numbered')

        for i in range(lis.count()):
            li = lis.nth(i)

            num_el = li.locator('.block-list__number').first
            num = (num_el.text_content() or '').strip() if num_el.count() else ''
            if not num.isdigit():
                num = str(i + 1)

            fr = li.locator('.block-list__content .fr-view').first
            html = fr.inner_html() if fr.count() else ''
            items.append((num, (html or '').strip()))

        self.items = items

    def _render_md(self, builder, assets_dir=None) -> str:
        if not self.items:
            return self.fallback_text

        rendered: list[str] = []
        for num, item_html in self.items:
            md = MarkdownBuilder.build_html(item_html) or ''
            rendered.append(MarkdownBuilder.build_numbered_item(num, md))
        return '\n'.join(r for r in rendered if r.strip()).strip()

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if not self.items:
            return []
        items_flows = [html_to_flowables(html, builder, assets_dir=assets_dir) for _, html in self.items]
        return builder.build_numbered_list_with_content(items_flows)
