from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scraper.formats.md import MarkdownBuilder
from scraper.parsers.blocks.base import LessonBlock
from scraper.utils.assets import ensure_asset, safe_basename_from_url, safe_filename


@dataclass()
class ImageBlock(LessonBlock):
    query_selector = '.block-image'

    image_url: str | None = None
    image_alt: str = ''
    asset_filename: str | None = None

    def _scrape(self) -> None:
        img = self.locator.locator(f'{self.query_selector} img').first
        if img.count():
            self.image_alt = (img.get_attribute('alt') or '').strip()
            try:
                self.image_url = img.evaluate('el => el.currentSrc || el.src')
            except Exception:
                self.image_url = img.get_attribute('src')

            basename = safe_basename_from_url(self.image_url) or 'image'
            prefix = (self.block_id or 'block').strip()
            self.asset_filename = safe_filename(f'{prefix}-{basename}')

        self.image_url = (self.image_url or '').strip() or None
        self.asset_filename = (self.asset_filename or '').strip() or None
        self.image_alt = (self.image_alt or '').strip()

    def _render_md(self, builder, assets_dir=None) -> str:
        if self.image_url and self.asset_filename and assets_dir:
            ensure_asset(
                locator=self.locator,
                url=self.image_url,
                assets_dir=assets_dir,
                filename=self.asset_filename,
            )

        if self.asset_filename:
            alt = self.image_alt or 'image'
            return MarkdownBuilder.build_image(alt, f'assets/{self.asset_filename}')

        return self.fallback_text

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if self.image_url and self.asset_filename and assets_dir:
            ensure_asset(
                locator=self.locator,
                url=self.image_url,
                assets_dir=assets_dir,
                filename=self.asset_filename,
            )
        if self.asset_filename and assets_dir:
            path = assets_dir / self.asset_filename
            if path.exists():
                return builder.build_image(path)
        return []
