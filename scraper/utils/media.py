from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scraper.config import get_config
from scraper.utils.assets import ensure_asset, safe_basename_from_url, safe_filename


@dataclass(frozen=True)
class VideoAsset:
    url: str
    filename: str
    poster_url: str | None = None
    poster_filename: str | None = None


def _read_media_url(el) -> str | None:
    try:
        url = el.evaluate('el => el.currentSrc || el.src')
    except Exception:
        url = el.get_attribute('src')
    return (url or '').strip() or None


def extract_video_assets(locator, *, prefix: str) -> list[VideoAsset]:
    videos = locator.locator('video')
    poster_imgs = locator.locator('.vjs-poster img, picture.vjs-poster img')
    assets: list[VideoAsset] = []
    seen: set[str] = set()

    for i in range(videos.count()):
        video = videos.nth(i)
        url = _read_media_url(video)
        if not url:
            source = video.locator('source').first
            if source.count():
                url = _read_media_url(source)
        if not url or url in seen:
            continue

        seen.add(url)
        basename = safe_basename_from_url(url) or f'video{i + 1}.mp4'
        filename = safe_filename(f'{prefix}-video{i + 1}-{basename}')

        poster_url = (video.get_attribute('poster') or '').strip() or None
        if not poster_url and poster_imgs.count() > i:
            poster_url = _read_media_url(poster_imgs.nth(i))
        poster_filename = None
        if poster_url:
            poster_base = safe_basename_from_url(poster_url) or f'poster{i + 1}.jpg'
            poster_filename = safe_filename(f'{prefix}-video{i + 1}-{poster_base}')

        assets.append(
            VideoAsset(
                url=url,
                filename=filename,
                poster_url=poster_url,
                poster_filename=poster_filename,
            )
        )

    return assets


def should_render_videos() -> bool:
    return get_config().download_videos


def render_video_markdown(*, locator, video: VideoAsset, assets_dir: Path | None = None) -> str:
    if not should_render_videos():
        return ''

    if not assets_dir:
        return ''

    ok = ensure_asset(locator=locator, url=video.url, assets_dir=assets_dir, filename=video.filename)
    if not ok:
        return ''

    poster_attr = ''
    if video.poster_url and video.poster_filename:
        if ensure_asset(
            locator=locator,
            url=video.poster_url,
            assets_dir=assets_dir,
            filename=video.poster_filename,
        ):
            poster_attr = f' poster="assets/{video.poster_filename}"'

    return (
        '<video controls preload="metadata" '
        'style="display:block;width:100%;max-width:960px;height:auto;margin:0.75rem 0;" '
        f'src="assets/{video.filename}"{poster_attr}></video>'
    )
