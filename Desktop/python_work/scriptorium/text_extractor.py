import fitz  # PyMuPDF

# general purpose of this program is to grab the text from the source PDF and store it in a useful format


# left to its own devices our text-extraction module fitz will extract the text from a PDF as a nested//
# hierarchical dictionary in the form: [book:[page:[block:[line:[span],[],...],[],...],[],...],[],...]//
# this becomes a problem because it preserves more structure than we actually want-- we just want the//
# paragraphs. To deal with this while preserving the structure-infromation that allows us to detect //
# paragraphs, we pre-process all of the text-blocks and store them as a list
def extract_text_blocks_from_pages(pdf_path):
	doc = fitz.open(pdf_path)
	all_blocks = []

	for page_num in range(doc.page_count):
		page = doc.load_page(page_num)
		text_dict = page.get_text("dict")
		for block in text_dict.get("blocks", []):
			all_blocks.append(block)

	return all_blocks


# diagnostic tool I made to figure out when and why paragraph breaks are happening.\\
# the paragraph-checking logic here is the same as used in group_text_blocks_into_paragraphs\\
# and is helps to check if the problem is with our paragraph logic or some other technical thing
def check_paragraph_break(line, previous_text, previous_bbox, previous_bottom, previous_indent, previous_font_size, is_new_page, vertical_threshold, indent_threshold, font_size_change_threshold):
	current_bbox = line['bbox']
	current_text = " ".join(span["text"] for span in line.get("spans", []))
	current_indent = current_bbox[0] 
	current_font_size = max(span["size"] for span in line.get("spans", []))  #

	horizontal_break = False
	vertical_break = False
	font_break = False


	if previous_bottom is not None and current_bbox[1] - previous_bottom > vertical_threshold and not is_new_page:
		vertical_break = True
	if previous_indent is not None and current_indent - previous_indent > indent_threshold:	
		horizontal_break = True
	if previous_font_size is not None and abs(current_font_size - previous_font_size) > font_size_change_threshold:
		font_break = True

	report = {"previous_bbox" : f"{previous_bbox}", "current_bbox" : f"{current_bbox}",
	 			"previous_text" : f"{previous_text}","line_text" : f"{current_text}" , 
	 			"P_break" : f"H:{horizontal_break}, V:{vertical_break}, F:{font_break}"}

	return report, previous_text, previous_bbox, previous_bottom, previous_indent, previous_font_size

# This function takes our sequential list of blocks and cycles through them to produce a sequential list\\
# of paragraphs. the paragraphs that we assemble here are the paragraphs we will edit and then print.\\
# This code contains multiple lines of code that are commented out, I have left them in place for\\
# ease of use when troubleshooting
def group_text_blocks_into_paragraphs(all_blocks, vertical_threshold=5.0, indent_threshold=10.0, font_size_change_threshold = 2):
	paragraphs = []
	paragraph_breaks = []
	current_paragraph = ""
	previous_bottom = None
	previous_indent = None
	previous_font_size = None
	i = 1
	#previous_bbox = None
	#previous_text = None

	for block in all_blocks:
		if block["type"] == 0:  # Text block
			# here we leverage the remaining structure-information from the text-dictionary still left\\
			# in our sequential list of blocks. we assemble the spans (small groups of charecters) into\\
			# lines of text. the text dictionary is still keeping track of the x&y coordinates of each\\
			# line. We use that position infromation to determine when a paragraph break has occured.
			for line in block.get("lines", []):

				line_bbox = line['bbox']
				line_text = " ".join(span["text"] for span in line.get("spans", []))
				#print(f"box_#:{i} ,pos:{line_bbox}, text:{line_text}")
				i += 1
				line_indent = line_bbox[0] 
				line_font_size = max(span["size"] for span in line.get("spans", []))  # Max font size in line

				# below is the logic that checks for paragraphs. It starts from the assumption that a\\
				# paragraph break has not happened, and then checks each line in our list of blocks to\\
				# see if any of the following conditions are met. if any of them are met, we conclude a\\
				# paragraph has occured
				new_paragraph = False

				is_new_page = previous_bottom is not None and line_bbox[1] < previous_bottom

				if ((previous_bottom is not None and line_bbox[1] - previous_bottom > vertical_threshold and not is_new_page) or \
					(previous_indent is not None and line_indent - previous_indent > indent_threshold) or \
					(previous_font_size is not None and abs(line_font_size - previous_font_size) > font_size_change_threshold)) and \
					line_bbox[3] != previous_bottom:
					new_paragraph = True

				# the conditions above will trigger a paragraph break if the horizontal position of a new\\
				# line is too different from the previous line (an indent), if there is a large vertical \\
				# gap between lines, or if there is a significant change in the font size of a lines text \\
				# compared to the previous line

				if new_paragraph:
					#report, previous_text, previous_bbox, previous_bottom, previous_indent, previous_font_size = check_paragraph_break(line, previous_text, previous_bbox, previous_bottom, previous_indent, previous_font_size, is_new_page, vertical_threshold, indent_threshold, font_size_change_threshold)
					#print(report)
					if current_paragraph:
						#print(f"{current_paragraph}")
						paragraphs.append(current_paragraph.strip())
					current_paragraph = line_text
				else:
					current_paragraph += " " + line_text

				previous_bottom = line_bbox[3]
				previous_indent = line_indent
				previous_font_size = line_font_size
				#previous_text = line_text
				#previous_bbox = line_bbox

	if current_paragraph:
		paragraphs.append(current_paragraph.strip())

	return paragraphs
