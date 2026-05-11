from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from playwright.sync_api import Locator

from scraper.config import OutputFormat
from scraper.formats.base import CourseBuilder
from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import PDFBuilder


@dataclass
class LessonBlock(ABC):
    query_selector: ClassVar[str] = ''
    skip: ClassVar[bool] = False

    block_id: str | None
    locator: Locator
    fallback_text: str = ''

    def __post_init__(self) -> None:
        self._scrape()
        self.fallback_text = self._capture_fallback_text()

    def _capture_fallback_text(self) -> str:
        try:
            return (self.locator.text_content(timeout=1000) or '').strip()
        except Exception:
            return ''

    @abstractmethod
    def _scrape(self) -> None:
        """Extract and store structured data from the live locator."""
        raise NotImplementedError

    @abstractmethod
    def _render_md(self, builder: MarkdownBuilder, assets_dir: Path | None = None) -> str:
        """Render this block as Markdown."""
        raise NotImplementedError

    @abstractmethod
    def _render_pdf(self, builder: PDFBuilder, assets_dir: Path | None = None) -> list:
        """Return flowables for this block's PDF content."""
        raise NotImplementedError

    def render(
        self,
        fmt: OutputFormat = OutputFormat.MD,
        assets_dir: Path | None = None,
        builder: CourseBuilder | None = None,
    ) -> Any:
        if self.skip:
            return None

        if fmt == OutputFormat.PDF:
            return self._render_pdf(builder, assets_dir=assets_dir)

        if fmt == OutputFormat.MD:
            return self._render_md(builder, assets_dir=assets_dir)

        raise ValueError(f'Unknown output format: {fmt!r}')
