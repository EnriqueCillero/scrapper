from __future__ import annotations

from dataclasses import dataclass, field

from scraper.formats.md import MarkdownBuilder
from scraper.formats.pdf import html_to_flowables
from scraper.parsers.blocks.base import LessonBlock
from scraper.utils.assets import ensure_asset, safe_basename_from_url, safe_filename
from scraper.utils.media import VideoAsset, extract_video_assets, render_video_markdown, should_render_videos


@dataclass
class TabsBlock(LessonBlock):
    query_selector = '.blocks-tabs'

    tabs: list[tuple[str, str, str]] = field(default_factory=list)
    # (title, body_html, body_text)

    images: dict[str, str] = field(default_factory=dict)
    # asset_filename -> url

    images_by_tab_index: dict[int, list[tuple[str, str]]] = field(default_factory=dict)
    # tab_index -> [(asset_filename, alt)]

    videos_by_tab_index: dict[int, list[VideoAsset]] = field(default_factory=dict)

    def _scrape(self) -> None:
        headers = self.locator.locator(f'{self.query_selector} .blocks-tabs__header-item')
        contents = self.locator.locator(f'{self.query_selector} .blocks-tabs__content-item')

        tab_count = min(headers.count(), contents.count())
        tabs: list[tuple[str, str, str]] = []
        images: dict[str, str] = {}
        images_by_tab_index: dict[int, list[tuple[str, str]]] = {}
        videos_by_tab_index: dict[int, list[VideoAsset]] = {}

        prefix = (self.block_id or 'block').strip()

        for i in range(tab_count):
            header = headers.nth(i)
            content = contents.nth(i)

            title_el = header.locator('.fr-view').first
            title = (
                (title_el.text_content() or '').strip()
                if title_el.count()
                else (header.text_content() or '').strip()
            )
            title = ' '.join(title.split())

            desc_fr = content.locator('.blocks-tabs__description .fr-view').first
            body_html = (desc_fr.inner_html() if desc_fr.count() else '') or ''
            body_text = (desc_fr.text_content() or '').strip() if desc_fr.count() else ''

            tabs.append((title, body_html.strip(), body_text.strip()))

            videos = extract_video_assets(content, prefix=f'{prefix}-tab{i + 1}')
            if videos:
                videos_by_tab_index[i] = videos
            video_posters = {video.poster_url for video in videos if video.poster_url}

            imgs = content.locator('img')
            for j in range(imgs.count()):
                img = imgs.nth(j)
                alt = (img.get_attribute('alt') or '').strip() or 'image'
                try:
                    url = img.evaluate('el => el.currentSrc || el.src')
                except Exception:
                    url = img.get_attribute('src')
                url = (url or '').strip()
                if not url:
                    continue
                if url in video_posters:
                    continue

                basename = safe_basename_from_url(url) or f'image{j + 1}'
                filename = safe_filename(f'{prefix}-tab{i + 1}-img{j + 1}-{basename}')
                images[filename] = url
                images_by_tab_index.setdefault(i, []).append((filename, alt))

        self.tabs = tabs
        self.images = images
        self.images_by_tab_index = images_by_tab_index
        self.videos_by_tab_index = videos_by_tab_index

    def _render_md(self, builder, assets_dir=None) -> str:
        if not self.tabs:
            return self.fallback_text

        if assets_dir and self.images:
            for filename, url in self.images.items():
                ensure_asset(locator=self.locator, url=url, assets_dir=assets_dir, filename=filename)

        lines: list[str] = []
        for i, (title, body_html, body_text) in enumerate(self.tabs):
            title_str = title.strip() or f'Tab {i + 1}'
            body_md = MarkdownBuilder.build_html(body_html) or body_text or ''

            if title_str and title_str != f'Tab {i + 1}':
                lines.append(MarkdownBuilder.build_heading(5, title_str))
            if body_md:
                lines.append(body_md)

            for filename, alt in self.images_by_tab_index.get(i, []):
                lines.append(MarkdownBuilder.build_image(alt, f'assets/{filename}'))
            for video in self.videos_by_tab_index.get(i, []):
                rendered_video = render_video_markdown(
                    locator=self.locator,
                    video=video,
                    assets_dir=assets_dir,
                )
                if rendered_video:
                    lines.append(rendered_video)

        return '\n\n'.join(line for line in lines if line.strip()).strip()

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if not self.tabs:
            return []
        if assets_dir and self.images:
            for filename, url in self.images.items():
                ensure_asset(locator=self.locator, url=url, assets_dir=assets_dir, filename=filename)
        items_with_content: list[tuple[str, list]] = []
        for i, (title, body_html, body_text) in enumerate(self.tabs):
            title_str = title.strip() or f'Tab {i + 1}'
            body_flows = html_to_flowables(body_html or body_text or '', builder, assets_dir=assets_dir)
            tab_flows = list(body_flows)
            if assets_dir:
                for filename, _alt in self.images_by_tab_index.get(i, []):
                    path = assets_dir / filename
                    if path.exists():
                        tab_flows.extend(builder.build_image(path))
            if should_render_videos():
                for video in self.videos_by_tab_index.get(i, []):
                    tab_flows.extend(builder.build_callout(href=video.url, link_text='Link al vídeo'))
            items_with_content.append((title_str, tab_flows))
        return builder.build_bullet_list_with_content(items_with_content)
