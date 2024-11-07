import re
import logging
from fpdf import FPDF
import json
from config2 import save_list_to_file

logging.basicConfig(
    filename='/Users/emmawatts/Desktop/python_work/scriptorium_tests/reformatted_lengths.log',
    level=logging.INFO
)


def calculate_indent_width(pdf, font, new_font_size, num_spaces=8):
    """Calculate the width for indentation in the PDF."""
    pdf.set_font(font, size=new_font_size)
    return pdf.get_string_width(" ") * num_spaces


def join_hyphenated_words(paragraphs):
    """Join hyphenated words split across lines in paragraphs."""
    for paragraph in paragraphs:
        lines = paragraph
        for i in range(len(lines) - 1):
            current_line, next_line = lines[i], lines[i + 1]
            current_text, next_text = \
                current_line['text'].rstrip(), next_line['text'].lstrip()

            if current_text.endswith('-'):
                current_text = current_text[:-1]
                last_word = current_text.split()[-1] if \
                    current_text.split() else None
                first_word = next_text.split()[0] if \
                    next_text.split() else None
                if last_word and first_word:
                    combined_word = last_word + first_word
                    current_line['text'] = \
                        ' '.join(current_text.split()[:-1] + [combined_word])
                    next_line['text'] = ' '.join(next_text.split()[1:])

    save_list_to_file(paragraphs, filename='de-hyphenated_paragraphs.json')
    return paragraphs


def clean_paragraphs(paragraphs):
    """Clean non-ASCII characters and unwanted whitespace in paragraphs."""
    cleaned_paragraphs = []
    for paragraph in paragraphs:
        if all(line.get('flags', {}).get('toc', 0) == 1 for line in paragraph)\
           or all(line.get('flags', {}).get('chapter_heading', 0) == 1
           for line in paragraph):
            cleaned_paragraphs.extend([[line] for line in paragraph])
            continue

        cleaned_paragraph = []
        for line in paragraph:
            clean_text = re.sub(r'\s+', ' ', ''.join(char if ord(char) < 128
                                else '?' for char in line['text'])).strip()
            line['text'] = clean_text
            cleaned_paragraph.append(line)
        cleaned_paragraphs.append(cleaned_paragraph)

    save_list_to_file(cleaned_paragraphs, filename='cleaned_paragraphs.json')
    return cleaned_paragraphs


def merge_consecutive_headings(paragraphs):
    """Merge consecutive chapter headings into single paragraphs."""
    merged_paragraphs, i = [], 0
    while i < len(paragraphs):
        paragraph = paragraphs[i]
        if not paragraph:
            i += 1
            continue

        first_line = paragraph[0]
        is_heading = first_line.get('flags', {}).get('chapter_heading', 0) == 1

        if is_heading:
            merged_text_lines = []
            while i < len(paragraphs) and (paragraphs[i][0].get('flags', {})
                                           .get('chapter_heading', 0) == 1):
                merged_text_lines.extend(line['text']
                                         for line in paragraphs[i])
                i += 1

            merged_paragraph = [{
                'text': ' '.join(merged_text_lines),
                'flags': first_line.get('flags', {}),
                'page_number': first_line.get('page_number', 1)
            }]
            merged_paragraphs.append(merged_paragraph)
        else:
            merged_paragraphs.append(paragraph)
            i += 1

    return merged_paragraphs


def wrap_text(pdf,
              text,
              font,
              new_font_size,
              max_width,
              indent_width,
              split_paragraph):
    """Wrap text to fit within specified width in the PDF."""
    pdf.set_font(font, size=new_font_size)
    words = text.split()
    lines, current_line = [], ''

    for word in words:
        available_width = max_width - (indent_width + 1 if not lines
                                       and not split_paragraph else 1)
        if pdf.get_string_width(current_line + word + ' ') <= available_width:
            current_line += word + ' '
        else:
            lines.append(current_line.strip())
            current_line = word + ' '
    if current_line:
        lines.append(current_line.strip())

    return lines


def reformat_paragraphs(pdf,
                        paragraphs,
                        page_width_mm,
                        font, new_font_size,
                        line_height_ratio,
                        indent_width):
    """Reformat paragraphs with specified font, size, and alignment options."""
    pdf.set_margins(left=5, top=5, right=5)
    max_width = page_width_mm - pdf.l_margin - pdf.r_margin
    formatted_paragraphs = []

    for paragraph in paragraphs:
        if not paragraph:
            continue

        first_line = paragraph[0]
        style = ''
        style += 'B' if \
            first_line.get('flags', {}).get('bold', 0) == 1 else ''
        style += 'I' if \
            first_line.get('flags', {}).get('italic', 0) == 1 else ''
        is_heading = first_line.get('flags', {}).get('chapter_heading', 0) == 1
        is_toc = first_line.get('flags', {}).get('toc', 0) == 1
        split_paragraph = first_line.get('flags', {}).get('split_paragraph',
                                                          False)

        effective_font_size = new_font_size + 4 if \
            is_heading else new_font_size
        pdf.set_font(font, style=style, size=effective_font_size)
        line_height = effective_font_size * line_height_ratio

        if is_toc:
            formatted_paragraphs.extend(
                [[{'text': line['text'], 'line_height': line_height,
                   'font_size': effective_font_size, 'style': style,
                   'is_heading': is_heading, 'is_toc': is_toc, 'indent': False,
                   'page_number': line.get('page_number', 1)}]
                    for line in paragraph]
            )
            continue

        paragraph_text = re.sub(r'\s+', ' ', ' '.join(line.get('text', '')
                                for line in paragraph)).strip()

        if is_heading:
            formatted_paragraphs.append(
                [{'text': line, 'line_height': line_height,
                  'font_size': effective_font_size, 'style': style,
                  'is_heading': is_heading, 'is_toc': is_toc, 'indent': False,
                  'page_number': first_line.get('page_number', 1)}
                 for line in wrap_text(pdf, paragraph_text, font,
                                       effective_font_size, max_width,
                                       indent_width, False)]
            )
            continue

        new_lines = wrap_text(pdf, paragraph_text, font, effective_font_size,
                              max_width, indent_width, split_paragraph)
        new_paragraph = [
            {'text': line, 'line_height': line_height,
             'font_size': effective_font_size, 'style': style,
             'is_heading': is_heading, 'is_toc': is_toc,
             'indent': idx == 0 and not split_paragraph,
             'page_number': first_line.get('page_number', 1)}
            for idx, line in enumerate(new_lines)
        ]
        formatted_paragraphs.append(new_paragraph)

    save_list_to_file(formatted_paragraphs,
                      filename='formatted_paragraphs.json')
    return formatted_paragraphs
