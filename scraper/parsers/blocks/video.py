from __future__ import annotations

from dataclasses import dataclass

from scraper.parsers.blocks.base import LessonBlock
from scraper.utils.media import VideoAsset, extract_video_assets, render_video_markdown, should_render_videos


@dataclass
class VideoBlock(LessonBlock):
    query_selector = '.block-video'

    video_url: str | None = None
    video_asset_filename: str | None = None

    poster_url: str | None = None
    poster_asset_filename: str | None = None

    def _scrape(self) -> None:
        prefix = (self.block_id or 'block').strip()
        assets = extract_video_assets(self.locator.locator(self.query_selector).first, prefix=prefix)
        if not assets:
            return
        video = assets[0]
        self.video_url = video.url
        self.video_asset_filename = video.filename
        self.poster_url = video.poster_url
        self.poster_asset_filename = video.poster_filename

    def _render_video_unavailable(self) -> str:
        msg = 'Video is not available in this output.'
        if self.video_url:
            msg = f'{msg} Source: {self.video_url}'
        return '\n'.join([f'> {line}'.rstrip() for line in msg.splitlines()]).strip()

    def _render_md(self, builder, assets_dir=None) -> str:
        if not self.video_url:
            return self._render_video_unavailable()

        return render_video_markdown(
            locator=self.locator,
            video=VideoAsset(
                url=self.video_url,
                filename=self.video_asset_filename or 'video.mp4',
                poster_url=self.poster_url,
                poster_filename=self.poster_asset_filename,
            ),
            assets_dir=assets_dir,
        )

    def _render_pdf(self, builder, assets_dir=None) -> list:
        if not should_render_videos():
            return []
        if not self.video_url:
            return builder.build_callout('Video is not available in this output.')
        return builder.build_callout(href=self.video_url, link_text='Link al vídeo')
