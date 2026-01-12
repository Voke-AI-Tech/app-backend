from fpdf import FPDF
import io
import logging
from datetime import datetime
from pathlib import Path

REPORT_TEMPLATES_DIR = Path(__file__).parent / "templates"
logger = logging.getLogger(__name__)

def encode_image_to_base64(image_path: Path) -> str:
    import base64
    try:
        if not image_path.exists():
            logger.warning(f"Image not found at {image_path}")
            return ""
        with open(image_path, "rb") as img:
            return f"data:image/png;base64,{base64.b64encode(img.read()).decode()}"
    except Exception as e:
        logger.error(f"Error encoding image from {image_path}: {e}")
        return ""

logo_base64 = encode_image_to_base64(REPORT_TEMPLATES_DIR / "Logo.png")

def get_score_color_class(score) -> str:
    try:
        score = int(float(score))
    except (ValueError, TypeError):
        return "red"

    if score >= 90: return "emerald"
    elif score >= 80: return "green"
    elif score >= 70: return "blue"
    elif score >= 60: return "purple"
    elif score >= 50: return "orange"
    else: return "red"

class ReportPdf(FPDF):
    def header(self):
        if logo_base64:
            try:
                self.image(logo_base64, x=10, y=8, w=30)
            except Exception as e:
                logger.error(f"Error adding logo to PDF: {e}")
        self.set_font("helvetica", "B", 16)
        self.cell(0, 10, "VokeAI Communication Report", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title):
        self.set_font("helvetica", "B", 12)
        self.set_fill_color(230, 230, 250)
        self.cell(0, 10, title, ln=True, fill=True)
        self.ln(4)

    def add_score_section(self, label, score, level):
        self.set_font("helvetica", "B", 12)
        self.cell(60, 8, f"{label}:", border=0)
        self.set_font("helvetica", "", 12)
        self.cell(40, 8, f"{score}", border=0)
        self.cell(40, 8, f"({level})", ln=True)

    def add_summary(self, summary_html):
        self.set_font("helvetica", "", 10)
        try:
            self.write_html(summary_html)
        except Exception as e:
            logger.warning(f"Error writing HTML to PDF, falling back to plain text: {e}")
            clean_text = summary_html.replace("<ul>", "").replace("</ul>", "").replace("<li>", "- ").replace("</li>", "\n")
            self.multi_cell(0, 10, clean_text)

async def generate_report(candidateName: str, grammarScore: float, grammarLevel: str, vocabularyScore: float, vocabularyLevel: str, fluencyScore: float, fluencyLevel: str,
                    pronunciationScore: float, pronunciationLevel: str, overallScore: float, overallLevel: str, fillerWordScore: float, fillerWordLevel: str, chart_url: str, plot_url: str, summary_html: str) -> tuple[io.BytesIO | None, str | None]:
    
    try:
        logger.info(f"Starting PDF generation for {candidateName}...")
        pdf = ReportPdf()
        pdf.add_page()

        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, f"Report for: {candidateName}", ln=True)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(10)

        pdf.chapter_title("Overall Performance")
        pdf.add_score_section("Overall Score", overallScore, overallLevel)
        pdf.ln(5)

        pdf.chapter_title("Skill-wise Breakdown")
        pdf.add_score_section("Grammar", grammarScore, grammarLevel)
        pdf.add_score_section("Vocabulary", vocabularyScore, vocabularyLevel)
        pdf.add_score_section("Fluency", fluencyScore, fluencyLevel)
        pdf.add_score_section("Pronunciation", pronunciationScore, pronunciationLevel)
        
        filler_display_score = 100 - int(fillerWordScore)
        pdf.add_score_section("Filler Words", filler_display_score, fillerWordLevel)
        pdf.ln(10)

        if chart_url:
            try:
                pdf.image(chart_url, w=150)
                pdf.ln(10)
            except Exception as e:
                logger.error(f"Error adding chart to PDF: {e}")
                
        if plot_url:
            try:
                pdf.image(plot_url, w=150)
                pdf.ln(10)
            except Exception as e:
                logger.error(f"Error adding plot to PDF: {e}")

        pdf.chapter_title("Summary & Recommendations")
        pdf.add_summary(summary_html)
        pdf.ln(10)

        pdf_bytes = pdf.output()
        pdf_bytes_io = io.BytesIO(pdf_bytes)

        safe_name = candidateName.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        pdf_filename = f"report_{safe_name}_{timestamp}.pdf"

        logger.info("PDF generation completed successfully.")
        return pdf_bytes_io, pdf_filename
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return None, None
