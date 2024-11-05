import traceback
from config2 import (
    pdf_path, output_path, font, new_font_size,
    line_height_ratio, dark_mode
)
from formatting_analyzer3 import extract_data, detect_formatting, export_csv
from text_extractor3 import group_text_blocks_into_paragraphs, convert_csv_to_dict
from text_formatter3 import (
    join_hyphenated_words, clean_paragraphs, reformat_paragraphs,
    calculate_indent_width, merge_consecutive_headings
)
from pdf_handler4 import PDF, create_custom_pdf


def main():
    """Main function to handle PDF processing and text formatting."""
    try:
        # Extract data and detect formatting features
        data = extract_data(pdf_path)
        toc, chapter_headings, original_lines = detect_formatting(data)
        text_with_formatting = export_csv(
            line_df=original_lines,
            toc=toc,
            chapter_headings_df=chapter_headings
        )

        text_list = convert_csv_to_dict(text_with_formatting)
        paragraphs = group_text_blocks_into_paragraphs(text_list)

        # Clean and reformat paragraphs
        cleaned_paragraphs = clean_paragraphs(paragraphs)
        joined_paragraphs = join_hyphenated_words(cleaned_paragraphs)
        merged_paragraphs = merge_consecutive_headings(joined_paragraphs)

        # PDF settings
        page_width_mm = 80  # Should match the width used in PDF initialization
        pdf = PDF(dark_mode=dark_mode, unit='mm', format=(page_width_mm, 2000))
        pdf.set_margins(left=5, top=5, right=5)
        pdf.set_auto_page_break(auto=True, margin=15)

        # Set indent and reformat paragraphs
        new_indent = calculate_indent_width(pdf, font, new_font_size)
        reformatted_paragraphs = reformat_paragraphs(
            pdf, merged_paragraphs, page_width_mm, font,
            new_font_size, line_height_ratio, new_indent
        )

        # Create and save the customized PDF
        create_custom_pdf(
            pdf, reformatted_paragraphs, output_path,
            font, new_indent, base_font_size=new_font_size
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
