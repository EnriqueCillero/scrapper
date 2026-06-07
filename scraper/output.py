from __future__ import annotations

import logging
from pathlib import Path

from scraper.config import DEFAULT_PDF_THEME, OutputFormat
from scraper.formats.pdf.themes import PDFTheme
from scraper.models.course_scheme import CourseScheme

logger = logging.getLogger(__name__)


def _safe_output_name(name: str, *, fallback: str) -> str:
    safe_name = ''.join(
        ch if ch.isalnum() or ch in {'.', '-', '_', ' '} else '_' for ch in name
    )
    while '  ' in safe_name:
        safe_name = safe_name.replace('  ', ' ')
    safe_name = safe_name.strip().strip('.')
    return safe_name or fallback


def write_course(
    course: CourseScheme,
    path: str | Path,
    *,
    output_formats: list[OutputFormat] | None = None,
    output_format: OutputFormat | str | None = None,
    pdf_theme: PDFTheme = DEFAULT_PDF_THEME,
) -> None:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_formats:
        fmts = output_formats
    elif output_format is not None:
        fmt = (
            output_format
            if isinstance(output_format, OutputFormat)
            else OutputFormat.from_extension(output_format)
        )
        fmts = [fmt]
    else:
        fmts = [OutputFormat.MD]

    lessons_count = sum(len(s.lessons) for s in course.sections)
    topic_name = _safe_output_name(course.title, fallback='course')
    topic_dir = output_dir / topic_name
    topic_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = topic_dir / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)

    for fmt in fmts:
        filename = f'{topic_name}.{fmt.extension}'
        safe_filename = _safe_output_name(filename, fallback=f'course.{fmt.extension}')
        output_file = topic_dir / safe_filename
        write_file(course, output_file, fmt, assets_dir=assets_dir, pdf_theme=pdf_theme)
        logger.info('Wrote %s lessons to %s', lessons_count, output_file)


def write_file(
    course: CourseScheme,
    output_path: Path,
    fmt: OutputFormat,
    *,
    assets_dir: Path,
    pdf_theme: PDFTheme = DEFAULT_PDF_THEME,
) -> None:
    if fmt == OutputFormat.MD:
        from scraper.formats.md import MDWriter

        MDWriter().write(course, output_path, assets_dir=assets_dir)
    elif fmt == OutputFormat.PDF:
        from scraper.formats.pdf import PDFWriter

        PDFWriter(theme=pdf_theme).write(course, output_path, assets_dir=assets_dir)
    else:
        raise ValueError(f'Unsupported format: {fmt}')
