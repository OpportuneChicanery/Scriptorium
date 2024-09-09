from fpdf import FPDF
from config import font

# the general purpose of this program is to print our result pdf with the users desired formatting.\\
# future improvement will definitely look like richer features to preserve original formatting where\\
# desireable, stuff like bolded and centered chapter-headings, maybe some kind of system to deal\\
# with foot-notes, takes to indicate page-breaks in the source pdf

# this is where we initiallize dark-mode 
class PDF(FPDF):
	def __init__(self, dark_mode=False):
		super().__init__()
		self.dark_mode = dark_mode

	def header(self):
		if self.dark_mode:
			self.set_fill_color(0, 0, 0)
			self.set_text_color(180, 180, 180)
			self.rect(0, 0, 210, 297, 'F')
		self.set_font(font, "B", 12)
		self.cell(0, 10, "Header Title", 0, 1, "C")
		#print("h")

	def footer(self):
		self.set_y(-15)
		if self.dark_mode:
			self.set_text_color(180, 180, 180)
		self.set_font(font, "I", 8)
		self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")
		#print("f")

	def add_page(self, orientation='', format='', same=False):
		super().add_page(orientation, format, same)
		if self.dark_mode:
			self.set_fill_color(0, 0, 0)
			self.set_text_color(180, 180, 180)
			self.rect(0, 0, 210, 297, 'F')

# this is the function that actually prints the new pdf. it works by separating out the first line in each\\
# of our modified paragraphs and printing it specially with an indent. then it prints the remaining\\
# paragraph text from the pages left margin.
def create_custom_pdf(paragraphs, output_path, indent_width, font_size, dark_mode=False):
	pdf = PDF(dark_mode=dark_mode)
	pdf.set_auto_page_break(auto=True, margin=15)
	page_width = pdf.w - 2 * pdf.l_margin
	line_height = font_size + 2
	pdf.add_page()

	pdf.set_font(font, size= font_size)

	for paragraph in paragraphs:
		first_line = paragraph.pop(0)
		pdf.set_x(pdf.l_margin + indent_width)
		pdf.cell(0, line_height, first_line, 0, 1, 'L', fill=False)
		#pdf.multi_cell(page_width - indent_width, line_height, paragraph_text, border=1)
		pdf.set_x(pdf.l_margin)
		remaining_text = " ".join(paragraph)
		#pdf.cell(indent_width, line_height, "", 0, 0)
		pdf.multi_cell(0, line_height, remaining_text, 0, 'L', fill=False)
		pdf.set_x(pdf.l_margin)

	pdf.output(output_path)