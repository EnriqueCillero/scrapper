from __future__ import annotations

from dataclasses import dataclass, field

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock
from scraper.parsers.cleaning import clean_scraped_text, compact_text, is_standalone_slide_index
from scraper.utils.assets import ensure_asset, safe_basename_from_url, safe_filename
from scraper.utils.media import VideoAsset, extract_video_assets, render_video_markdown


@dataclass
class SlideshowBlock(LessonBlock):
    query_selector = '.block-process'

    intro_title: str = ''
    intro_body_html: str = ''
    intro_body_text: str = ''

    steps: list[tuple[str, str, str, str, str | None, str, list[VideoAsset]]] = field(
        default_factory=list
    )
    # (step_num, title, body_html, body_text, asset_filename, alt, videos)

    image_url_by_filename: dict[str, str] = field(default_factory=dict)  # filename -> url

    def _scrape(self) -> None:
        def _safe_text_content(el) -> str:
            try:
                if not el.count():
                    return ''
                return (el.text_content(timeout=1000) or '').strip()
            except Exception:
                return ''

        def _safe_inner_html(el) -> str:
            try:
                if not el.count():
                    return ''
                return el.inner_html(timeout=1000) or ''
            except Exception:
                return ''

        def _first_text(scope, selector: str) -> str:
            return clean_scraped_text(_safe_text_content(scope.locator(selector).first))

        def _first_html(scope, selector: str) -> str:
            return (_safe_inner_html(scope.locator(selector).first) or '').strip()

        def _is_placeholder_title(text: str) -> bool:
            value = compact_text(text)
            return (not value) or is_standalone_slide_index(value) or value.lower().startswith('step ')

        intro = self.locator.locator('.process-card--intro').first
        if intro.count():
            self.intro_title = _first_text(
                intro,
                '.process-card__title .fr-view, .process-card__title',
            )
            if _is_placeholder_title(self.intro_title):
                self.intro_title = ''

            self.intro_body_html = _first_html(
                intro,
                '.process-card__description .fr-view, .process-card__description',
            )
            self.intro_body_text = _first_text(
                intro,
                '.process-card__description .fr-view, .process-card__description',
            )

        steps: list[tuple[str, str, str, str, str | None, str, list[VideoAsset]]] = []
        image_url_by_filename: dict[str, str] = {}
        prefix = (self.block_id or 'block').strip()

        cards = self.locator.locator('.process-card[data-slide]')
        if not cards.count():
            cards = self.locator.locator('.process-card')

        for i in range(cards.count()):
            card = cards.nth(i)
            if 'process-card--intro' in (card.get_attribute('class') or ''):
                continue

            num_el = card.locator('.process-card__number p').first
            step_num = _safe_text_content(num_el) if num_el.count() else ''
            step_num = ''.join(ch for ch in step_num if ch.isdigit()) or str(len(steps) + 1)

            title = _first_text(card, '.process-card__title .fr-view, .process-card__title')
            if _is_placeholder_title(title):
                title = ''

            # Description
            body_html = _first_html(
                card,
                '.process-card__description .fr-view, .process-card__description',
            )
            body_text = _first_text(
                card,
                '.process-card__description .fr-view, .process-card__description',
            )
            videos = extract_video_assets(card, prefix=f'{prefix}-step{step_num}')
            video_posters = {video.poster_url for video in videos if video.poster_url}

            # Image (optional)
            img = card.locator('.process-card__media img').first
            asset_filename: str | None = None
            alt = ''
            if img.count():
                alt = (img.get_attribute('alt') or '').strip() or 'image'
                try:
                    url = img.evaluate('el => el.currentSrc || el.src')
                except Exception:
                    url = img.get_attribute('src')

                if url:
                    if url not in video_posters:
                        basename = safe_basename_from_url(url) or 'image'
                        asset_filename = safe_filename(f'{prefix}-step{step_num}-{basename}')
                        image_url_by_filename[asset_filename] = url

            if title or body_html.strip() or body_text.strip() or asset_filename or videos:
                steps.append(
                    (
                        step_num,
                        title,
                        body_html.strip(),
                        body_text.strip(),
                        asset_filename,
                        alt,
                        videos,
                    )
                )

        self.steps = steps
        self.image_url_by_filename = image_url_by_filename
        self.intro_body_html = (self.intro_body_html or '').strip()
        self.intro_body_text = (self.intro_body_text or '').strip()

    def _render_md(self, builder, assets_dir=None) -> str:
        if assets_dir and self.image_url_by_filename:
            for filename, url in self.image_url_by_filename.items():
                ensure_asset(locator=self.locator, url=url, assets_dir=assets_dir, filename=filename)

        intro_md = MarkdownBuilder.build_html(self.intro_body_html) or self.intro_body_text or ''

        lines: list[str] = []
        if self.intro_title:
            lines.append(MarkdownBuilder.build_heading(4, self.intro_title))
            if intro_md:
                lines.append(intro_md.strip())
            lines.append('')
        elif intro_md:
            lines.append(intro_md.strip())
            lines.append('')

        for _step_num, title, body_html, body_text, asset_filename, alt, videos in self.steps:
            body_md = MarkdownBuilder.build_html(body_html) or body_text or ''

            content_lines: list[str] = []
            if title:
                heading_level = 5 if title.lower().startswith('video solución') else 4
                content_lines.append(MarkdownBuilder.build_heading(heading_level, title))
            if body_md:
                content_lines.append(body_md)
            media_lines: list[str] = []
            if asset_filename:
                img = MarkdownBuilder.build_image(alt or 'image', f'assets/{asset_filename}')
                media_lines.append(img)
            for video in videos:
                media_lines.append(
                    render_video_markdown(locator=self.locator, video=video, assets_dir=assets_dir)
                )

            content = '\n'.join([*content_lines, *media_lines]).strip()
            if content:
                lines.append(content)

        out = '\n'.join(lines).strip()
        return out if out else self.fallback_text

    def _render_pdf(self, builder, assets_dir=None) -> list:
        out: list = []
        if assets_dir and self.image_url_by_filename:
            for filename, url in self.image_url_by_filename.items():
                ensure_asset(locator=self.locator, url=url, assets_dir=assets_dir, filename=filename)
        intro_flows = html_to_flowables(
            self.intro_body_html or self.intro_body_text or '',
            builder,
            assets_dir=assets_dir,
        )
        if self.intro_title:
            out.extend(builder.build_subheading(self.intro_title))
        out.extend(intro_flows)
        step_items: list[list] = []
        for _step_num, title, body_html, body_text, asset_filename, alt, videos in self.steps:
            body_flows = html_to_flowables(body_html or body_text or '', builder, assets_dir=assets_dir)
            path = (assets_dir / asset_filename) if (asset_filename and assets_dir) else None
            has_image = path is not None and path.exists()
            if title or body_flows or has_image or videos:
                step_content: list = []
                if title:
                    step_content.extend(builder.build_subheading(title))
                if has_image and path:
                    step_content.extend(builder.build_image(path))
                for video in videos:
                    step_content.extend(builder.build_callout(href=video.url, link_text='Link al vídeo'))
                step_content.extend(body_flows)
                step_items.append(step_content)
        if step_items:
            out.extend(builder.build_numbered_list_with_content(step_items))
        return out
