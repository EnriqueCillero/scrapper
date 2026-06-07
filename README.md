# Blackboard SCORM Scraper

Scrapes SCORM content from U-TAD Blackboard and exports it as Markdown or PDF.

## Requirements

- **Python**: 3.9 or higher (below 4.0)

## Installation

1. Clone the repository and enter the project directory:
   ```bash
   git clone <repository-url>
   cd u-tad_blackboard-scorm-scraper
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Install Playwright browsers (Chromium):
   ```bash
   playwright install chromium
   ```

## Execution

1. Run the scraper:
   ```bash
   python main.py
   ```

2. A setup wizard will guide you through configuring:
   - Base URL (default: U-TAD Blackboard)
   - Course name and output path
   - Output formats (Markdown, PDF, AI optimized Markdown, or multiple)

3. A Chromium browser window will open. **Log in to Blackboard** and open the SCORM content in pop-up mode.

4. When prompted, press **ENTER** after the SCORM popup is open. The scraper will extract the content and write it to the configured output directory.

Output files are written to `./output/<course_name>/<topic_name>/` with topic-local assets in `./output/<course_name>/<topic_name>/assets/` (or under the path you configured). The AI optimized Markdown format writes a lighter `.ai.md` file with media omitted.
