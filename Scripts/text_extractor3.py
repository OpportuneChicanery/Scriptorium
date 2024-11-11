import pandas as pd
from config2 import save_list_to_file


def convert_csv_to_dict(line_df):
    """Convert CSV data to a dictionary format for text processing."""
    text_dict = []
    for _, row in line_df.iterrows():
        line_data = {
            'page_number': row['page_number'],
            'text': row['text'],
            'line_bbox_x1': row['line_bbox_x1'],
            'line_bbox_y1': row['line_bbox_y1'],
            'line_bbox_x2': row['line_bbox_x2'],
            'line_bbox_y2': row['line_bbox_y2'],
            'font_size': row['font_size'],
            'font': row['font'],
            'flags': {
                'bold': row['bold'],
                'italic': row['italic'],
                'toc': row['TOC'],
                'chapter_heading': row['chapter_heading'],
                'split_paragraph': False
            }
        }
        text_dict.append(line_data)
    return text_dict


def group_text_blocks_into_paragraphs(
    text_dict, vertical_threshold=5.0,
    indent_threshold=10.0, font_size_change_threshold=1
):
    """Group lines into paragraphs based on vertical and indent changes."""
    paragraphs = []
    current_paragraph = []
    previous_bottom = previous_indent = \
        previous_font_size = previous_page_number = None

    for line in text_dict:
        line_indent = line['line_bbox_x1']
        line_font_size = line['font_size']
        line_bottom = line['line_bbox_y2']
        line_page_number = line['page_number']

        # Check if the line is a TOC or Chapter Heading
        if line['flags']['toc'] or line['flags']['chapter_heading']:
            if current_paragraph:
                paragraphs.append(current_paragraph)
            paragraphs.append([line])  # Each heading is a separate paragraph
            current_paragraph = []
            previous_bottom = line_bottom
            previous_indent = line_indent
            previous_font_size = line_font_size
            previous_page_number = line_page_number
            continue

        new_paragraph = False
        is_new_page = previous_page_number is not None \
            and line_page_number != previous_page_number

        # Determine if this line starts a new paragraph
        if is_new_page:
            new_paragraph = True
            if line_indent - previous_indent <= indent_threshold:
                line['flags']['split_paragraph'] = True
        elif previous_bottom is not None:
            vertical_gap = line['line_bbox_y1'] - previous_bottom
            indent_change = line_indent - previous_indent if \
                previous_indent is not None else 0
            font_size_change = abs(line_font_size - previous_font_size) if \
                previous_font_size is not None else 0

            if vertical_gap > vertical_threshold or \
                    indent_change > indent_threshold or \
                    font_size_change > font_size_change_threshold:
                new_paragraph = True

        if new_paragraph:
            if current_paragraph:
                paragraphs.append(current_paragraph)
            current_paragraph = [line]
        else:
            current_paragraph.append(line)

        # Update previous line details
        previous_bottom = line_bottom
        previous_indent = line_indent
        previous_font_size = line_font_size
        previous_page_number = line_page_number

    # Append any remaining lines in the last paragraph
    if current_paragraph:
        paragraphs.append(current_paragraph)

    save_list_to_file(paragraphs, filename='paragraphs.json')
    return paragraphs
