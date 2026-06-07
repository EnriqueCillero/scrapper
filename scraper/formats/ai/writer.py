from __future__ import annotations

import re
from pathlib import Path

from scraper.config import OutputFormat
from scraper.formats.base import CourseWriter
from scraper.formats.md import MarkdownBuilder
from scraper.parsers.cleaning import clean_markdown_output


def _escape_frontmatter_value(value: str) -> str:
    return (value or '').replace('"', '\\"')


def _clean_ai_markdown(markdown: str) -> str:
    cleaned = clean_markdown_output(markdown)
    frontmatter = re.match(r'\A---\n(?P<body>.*?)\n---\n?', cleaned, flags=re.S)
    if frontmatter:
        body = '\n'.join(line for line in frontmatter.group('body').splitlines() if line.strip())
        cleaned = f'---\n{body}\n---\n\n{cleaned[frontmatter.end():].lstrip()}'
    cleaned = re.sub(r'(?m)^\s*!\[[^\]]*]\([^)]+\)\s*$', '', cleaned)
    cleaned = re.sub(r'(?m)^\s*<video\b[^\n]*</video>\s*$', '', cleaned)
    cleaned = re.sub(r'(?m)^\s*>\s*\[Link al v[ií]deo]\([^)]+\)\s*$', '', cleaned, flags=re.I)
    cleaned = re.sub(r'(?m)^#{4,6}\s+Video Soluci[oó]n[^\n]*\n+(?=\n|#{1,3}\s)', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip() + '\n'


class AIMarkdownWriter(CourseWriter):
    def write(
        self,
        course,
        output_path: Path,
        assets_dir: Path,
    ) -> None:
        builder = MarkdownBuilder()

        parts: list[str] = [
            '---',
            'format: ai-optimized-notes',
            f'course_title: "{_escape_frontmatter_value(course.title)}"',
            'media: omitted',
            '---',
            '',
            builder.build_heading(1, course.title),
        ]

        for section_idx, section in enumerate(course.sections, start=1):
            parts.extend(
                [
                    '',
                    builder.build_heading(2, f'{section_idx}. {section.title}'),
                ]
            )

            for lesson_idx, lesson in enumerate(section.lessons, start=1):
                lesson_ref = f'{section_idx}.{lesson_idx}'
                lesson_title = _escape_frontmatter_value(lesson.title)
                parts.extend(
                    [
                        '',
                        f'<!-- lesson id="{lesson_ref}" title="{lesson_title}" -->',
                        builder.build_heading(3, f'{lesson_ref} {lesson.title}'),
                    ]
                )

                for block in lesson.blocks:
                    rendered = block.render(fmt=OutputFormat.MD, assets_dir=None)
                    if rendered:
                        parts.extend(['', rendered.strip()])

        output_path.write_text(_clean_ai_markdown('\n\n'.join(parts)), encoding='utf-8')
