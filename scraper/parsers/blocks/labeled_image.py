from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock
from scraper.utils.assets import ensure_asset, safe_basename_from_url, safe_filename


@dataclass()
class LabeledImageBlock(LessonBlock):
    query_selector = '.block-labeled-graphic'

    image_url: str | None = None
    image_alt: str = ''
    asset_filename: str | None = None
    items: list[tuple[str, str]] = field(default_factory=list)  # (title, desc_html)

    def _scrape(self) -> None:
        img = self.locator.locator('img.labeled-graphic-canvas__image').first
        if img.count():
            self.image_alt = (img.get_attribute('alt') or '').strip()
            try:
                self.image_url = img.evaluate('el => el.currentSrc || el.src')
            except Exception:
                self.image_url = img.get_attribute('src')

            basename = safe_basename_from_url(self.image_url) or 'image'
            prefix = (self.block_id or 'block').strip()
            self.asset_filename = safe_filename(f'{prefix}-{basename}')

        items: list[tuple[str, str]] = []
        map_items = self.locator.locator('li.map-item')
        for i in range(map_items.count()):
            li = map_items.nth(i)
            title_el = li.locator('h2.bubble__title').first

            title = (title_el.text_content() or '').strip() if title_el.count() else ''
            if not title:
                continue

            desc_fr = li.locator('.bubble__description .fr-view').first
            desc_html = desc_fr.inner_html() if desc_fr.count() else ''
            items.append((title, (desc_html or '').strip()))

        self.items = items

        self.image_url = (self.image_url or '').strip() or None
        self.asset_filename = (self.asset_filename or '').strip() or None
        self.image_alt = (self.image_alt or '').strip()

    def _render_md(self, builder, assets_dir=None) -> str:
        if assets_dir and self.image_url and self.asset_filename:
            ensure_asset(
                locator=self.locator,
                url=self.image_url,
                assets_dir=assets_dir,
                filename=self.asset_filename,
            )

        lines: list[str] = []
        if self.asset_filename:
            alt = self.image_alt or 'image'
            lines.append(MarkdownBuilder.build_image(alt, f'assets/{self.asset_filename}'))
            lines.append('')

        for title, desc_html in self.items:
            desc_md = MarkdownBuilder.build_html(desc_html)
            lines.append(MarkdownBuilder.build_bullet_item(title, desc_md))

        out = '\n'.join(lines).strip()
        return out if out else self.fallback_text

    def _render_pdf(self, builder, assets_dir=None) -> list:
        out: list = []
        if assets_dir and self.image_url and self.asset_filename:
            ensure_asset(
                locator=self.locator,
                url=self.image_url,
                assets_dir=assets_dir,
                filename=self.asset_filename,
            )
        if self.asset_filename and assets_dir:
            path = assets_dir / self.asset_filename
            if path.exists():
                out.extend(builder.build_image(path))
        items_with_content: list[tuple[str, list]] = []
        for title, desc_html in self.items:
            desc_flows = html_to_flowables(desc_html or '', builder, assets_dir=assets_dir)
            items_with_content.append((title, desc_flows))
        out.extend(builder.build_bullet_list_with_content(items_with_content))
        return out
