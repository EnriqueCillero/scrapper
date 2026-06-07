from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import Locator

from scraper.config import get_config
from scraper.parsers.blocks import (
    AccordionBlock,
    BulletedListBlock,
    ButtonBlock,
    ButtonStackBlock,
    CodeBlock,
    EndOfLessonBlock,
    FlashcardsBlock,
    GalleryCarouselBlock,
    ImageBlock,
    LabeledImageBlock,
    LessonBlock,
    NumberedListBlock,
    QuoteCarouselBlock,
    SlideshowBlock,
    TabsBlock,
    TextBlock,
    TitleBlock,
    UnknownBlock,
    VideoBlock,
)


class BlockParser:
    def __init__(self, wrapper: Locator) -> None:
        self.wrapper = wrapper

    def _identify_block(self) -> type[LessonBlock]:
        # Order matters
        for block_cls in (
            EndOfLessonBlock,
            CodeBlock,
            TitleBlock,
            AccordionBlock,
            ButtonStackBlock,
            ButtonBlock,
            LabeledImageBlock,
            GalleryCarouselBlock,
            ImageBlock,
            FlashcardsBlock,
            NumberedListBlock,
            BulletedListBlock,
            QuoteCarouselBlock,
            SlideshowBlock,
            TabsBlock,
            VideoBlock,
            TextBlock,
        ):
            selector = getattr(block_cls, 'query_selector', '') or ''
            if selector and self.wrapper.locator(selector).count():
                return block_cls

        return UnknownBlock

    def parse_block(self, *, block_id: str | None) -> LessonBlock:
        block_cls = self._identify_block()
        block = block_cls(block_id=block_id, locator=self.wrapper)
        self._dump_debug_block(block_cls, block_id)
        return block

    def _dump_debug_block(self, block_cls: type[LessonBlock], block_id: str | None) -> None:
        if os.getenv('SCRAPER_DEBUG_BLOCKS') not in {'1', 'true', 'TRUE', 'yes', 'YES'}:
            return

        try:
            html = self.wrapper.inner_html(timeout=1000) or ''
        except Exception:
            return

        safe_id = ''.join(ch if ch.isalnum() or ch in {'-', '_'} else '_' for ch in (block_id or 'block'))
        output_dir = Path(get_config().output_path) / 'debug-blocks'
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f'{safe_id}-{block_cls.__name__}.html'
        (output_dir / filename).write_text(html, encoding='utf-8')
