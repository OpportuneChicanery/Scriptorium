from fpdf import FPDF
from config2 import font, line_height_ratio

# Define mobile-friendly page dimensions
PAGE_WIDTH_MM = 80  # Adjust as needed
PAGE_HEIGHT_MM = 150  # Adjust as needed or use a standard size

# Base font settings
BASE_FONT_SIZE = 12
FONT_NAME = font  # Use the font defined in your config
LINE_HEIGHT_RATIO = line_height_ratio  # Line height multiplier


class PDF(FPDF):
    """Custom PDF class with optional dark mode support."""

    def __init__(
        self, dark_mode=False, unit="mm",
        page_format=(PAGE_WIDTH_MM, PAGE_HEIGHT_MM)
    ):
        super().__init__(unit=unit, format=page_format)
        self.dark_mode = dark_mode
        self.set_margins(left=5, top=5, right=5)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """setting for the header"""
        if self.dark_mode:
            self.set_fill_color(0, 0, 0)
            self.rect(0, 0, self.w, 5, "F")  # Fill the top with black
            self.set_text_color(180, 180, 180)  # Set text color to light gray
        self.set_font(FONT_NAME, "B", size=8)

    def footer(self):
        """setting for the footer"""
        self.set_y(-5)
        if self.dark_mode:
            self.set_text_color(180, 180, 180)
        self.set_font(FONT_NAME, "I", size=8)
        self.cell(0, 1, f"Page {self.page_no()}", 0, 0, "C")

    def add_page(self, orientation="", page_format="", same=False):
        """method for creating a new page"""
        super().add_page(orientation=orientation,
                         format=page_format, same=same)
        if self.dark_mode:
            self.set_fill_color(0, 0, 0)
            self.rect(0, 0, self.w, self.h, "F")
            self.set_text_color(180, 180, 180)


def create_custom_pdf(
    pdf,
    formatted_paragraphs,
    output_path,
    new_font,
    indent_width,
    base_font_size=BASE_FONT_SIZE,
):
    """Render paragraphs into a custom PDF with optional dark mode"""

    pdf.set_font(new_font, size=base_font_size)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    previous_original_page_number = None
    previous_formatting = None
    pdf.add_page()

    for paragraph in formatted_paragraphs:
        if not paragraph:
            continue

        is_toc = paragraph[0].get("is_toc", False)

        if is_toc:
            if previous_formatting != "is_toc":
                pdf.cell(
                    0, LINE_HEIGHT_RATIO * base_font_size, txt=" ",
                    ln=1, align="C"
                )

            pdf.set_font(
                new_font, size=paragraph[0]["font_size"],
                style=paragraph[0]["style"]
            )
            for line in paragraph:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(
                    available_width, line["line_height"],
                    txt=line["text"], align="L"
                )
            previous_formatting = "is_toc"
            continue

        for line in paragraph:
            line_height = line["line_height"]
            effective_font_size = line["font_size"]
            style = line["style"]
            text = line["text"]
            is_heading = line.get("is_heading", False)
            indent = line.get("indent", False)
            original_page_number = line.get("page_number")

            pdf.set_font(new_font, style=style, size=effective_font_size)

            # Draw separator line if there's a page break in the original text
            if (
                previous_original_page_number is not None
                and original_page_number != previous_original_page_number
            ):
                pdf.set_draw_color(128, 128, 128)
                pdf.set_line_width(0.1)
                y_position = pdf.get_y() + line_height / 2
                pdf.line(pdf.l_margin, y_position,
                         pdf.w - pdf.r_margin, y_position)
                pdf.ln(6)
                pdf.set_draw_color(0, 0, 0)

            previous_original_page_number = original_page_number

            # Check for page overflow and add a new page if needed
            if pdf.get_y() + line_height > pdf.h - pdf.b_margin:
                pdf.add_page()

            pdf.set_x(pdf.l_margin)

            # Render headings as centered text
            if is_heading:
                if previous_formatting != "is_heading":
                    pdf.cell(0, line_height, txt=" ", ln=1, align="C")
                pdf.cell(0, line_height, txt=text, ln=1, align="C")
                previous_formatting = "is_heading"
            elif indent and line == paragraph[0]:
                pdf.set_x(pdf.l_margin + indent_width)
                pdf.cell(0, line_height, txt=text, ln=1, align="L")
                previous_formatting = "body_text"
            else:
                pdf.multi_cell(available_width, line_height,
                               txt=text, align="L")
                previous_formatting = "body_text"

    pdf.output(output_path)
