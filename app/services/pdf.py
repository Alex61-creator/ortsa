import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class PDFGenerator:
    def __init__(self):
        template_dir = Path(__file__).parent.parent / "templates" / "pdf"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

    async def generate(self, template_name: str, context: Dict[str, Any], output_filename: str) -> Path:
        template = self.env.get_template(template_name)
        html_content = template.render(**context)

        output_path = settings.STORAGE_DIR / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _generate():
            html = HTML(string=html_content)
            css = CSS(string="""
                @page { size: A4; margin: 2cm; }
                body { font-family: 'DejaVu Serif', serif; font-size: 12pt; }
                img { max-width: 100%; height: auto; }
            """)
            html.write_pdf(output_path, stylesheets=[css])

        await asyncio.to_thread(_generate)
        logger.info("PDF generated", path=str(output_path))
        return output_path