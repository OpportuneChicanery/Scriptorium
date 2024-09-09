from config import pdf_path, output_path, font_size, dark_mode, font
#from formatting_analyser import extract_x_coordinates, analyze_x_coordinates
from text_extractor import extract_text_blocks_from_pages, group_text_blocks_into_paragraphs, check_paragraph_break
from text_formatter import calculate_indent_width, clean_paragraphs, reformat_paragraphs, join_hyphenated_words
from pdf_handler_2 import create_custom_pdf
from fpdf import FPDF

# general purpose of this program is to tie everything together and execute

def main():
	pdf = FPDF()
	#formatting_data = extract_x_coordinates(pdf_path, num_elements=10000)
	#left_margin, indent = analyze_x_coordinates(formatting_data)
	extracted_blocks = extract_text_blocks_from_pages(pdf_path) # get sequential list of text
	paragraphs = group_text_blocks_into_paragraphs(extracted_blocks) # identify paragraph groups within that list
	cleaned_paragraphs = clean_paragraphs(paragraphs) # remove special charecters
	new_indent = calculate_indent_width(pdf, font_size) # find indent for target font-size
	page_width = pdf.w - 2 * pdf.l_margin # calculate page width of new document
	new_paragraphs = reformat_paragraphs(cleaned_paragraphs, pdf, page_width, new_indent, font_size, font) # create new lines to fit result documents from list of paragraphs according to config spec.
	create_custom_pdf(new_paragraphs, output_path, new_indent, font_size=font_size, dark_mode=dark_mode) # create new document 

if __name__ == "__main__":
	main()