from fpdf import FPDF
from config import font, font_size

# The general purpose of this program is to take our sequential list of paragraphs and format it\\
# correctly. if we skip this step then the result pdf will retain that same text-per-line as the\\
# original, as opposed to creating a new layout that according to user specificaltion.

# this function calulates an indent size preportional to the target font-size. we need this info\\
# to effectively calculate the width of an indented line in the line-construction process 
def calculate_indent_width(pdf, font_size, num_spaces=16):
	pdf.set_font(font, size=font_size)
	width_of_space = pdf.get_string_width(" ")  # Width of a single space character
	indent_width = width_of_space * num_spaces  # Width of the indent (4 spaces)
	return indent_width

# Our source pdf will frequently have hyphens that look out of place when the text of the pdfs\\
# lines are moved around. to fix this we remove the hyphen from words at the end of a line
def join_hyphenated_words(words):
	i = 0

	while i < len(words) - 1:
		# Check if the current word ends with a hyphen
		if words[i].endswith('-'):
			# Join the current word (without the hyphen) with the next word
			words[i] = words[i][:-1] + words[i + 1]
			# Remove the next word from the list as it's now part of the previous one
			words.pop(i + 1)
		else:
			# Move to the next word
			i += 1

	return words

# Here we make new lines for each paragraph that will fill that page of the result pdf taking into\\
# target font-size, font, and padge-width. future improvement might include adding our own logic\\
# for word hyphenation, b/c at large font sizes or on narrow pages the lines don't look great
def reformat_paragraphs(paragraphs, pdf, page_width, indent_width, font_size, font):
	reformatted_paragraphs = []

	for paragraph in paragraphs:
		lines = []
		current_line = ""
		old_words = paragraph.split()
		words = join_hyphenated_words(old_words)
		#print(f"un-remformatted lines:{words}")
		pdf.set_font(font, size= font_size)
		for word in words:

			if lines == []:
				if pdf.get_string_width(current_line + word + " ") + (2 * indent_width) <= page_width:
					current_line += (word + " ")
				else:
					lines.append(current_line.strip())
					current_line = word + " "
			else:
				if pdf.get_string_width(current_line + word + " " ) <= page_width:
					current_line += (word + " ")
				else:
					lines.append(current_line.strip())
					current_line = word + " "

		if current_line:
			lines.append(current_line.strip())

		reformatted_paragraphs.append(lines)
	#print(f"{reformatted_paragraphs}")	
	return reformatted_paragraphs

# if we try to print special charecters into fonts that don't have those charecters the program will\\
# crash. for now we replace any and all special charecters with question marks
def clean_paragraphs(paragraphs):
	cleaned_paragraphs = []
	for paragraph in paragraphs:
		# Clean each word in the paragraph using list comprehension
		cleaned_words = [''.join([char if ord(char) < 128 else '?' for char in word]) for word in paragraph.split()]

		# Join the cleaned words back into a single paragraph string
		clean_paragraph = " ".join(cleaned_words)

		# Append the cleaned paragraph to the list
		cleaned_paragraphs.append(clean_paragraph)
		#print(f"un-remformatted lines:{clean_paragraph}")

	return cleaned_paragraphs

