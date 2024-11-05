import re
import fitz  # PyMuPDF
import pandas as pd
from fuzzywuzzy import process


def extract_data(pdf_path):
    """Extract text and metadata from a PDF and store it in a DataFrame."""

    doc = fitz.open(pdf_path)

    data = []

    print(f"Processing file: {pdf_path}")

    for page_number in range(doc.page_count):
        page = doc.load_page(page_number)
        width = page.mediabox.width
        height = page.mediabox.height
        # Extract text and metadata (bounding boxes, font sizes, etc.)
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

                        bold = 1 if span["flags"] & 2 else 0
                        italic = 1 if span["flags"] & 1 else 0
                        lone_num = (
                            1 if re.fullmatch(r"\d+",
                                              span["text"].strip()) else 0
                        )

                        data.append(
                            {
                                "page_number": page_number,
                                "width": width,
                                "height": height,
                                "text": span["text"],
                                "x1": bbox[0],
                                "y1": bbox[1],
                                "x2": bbox[2],
                                "y2": bbox[3],
                                "bbox_area": area,
                                "font_size": span["size"],  # Font size
                                "font": span["font"],  # Font family
                                "bold": bold,
                                "italic": italic,
                                "lone_num": lone_num,
                            }
                        )

    df = pd.DataFrame(data)
    print(f"Finished processing {pdf_path}")

    return df


def bunch_lines(df):
    """Sort words into line-groups based on vertical proximity"""
    df = df.sort_values(by=["page_number", "y1", "x1"])

    lines = []  # Store information about each line

    # Group spans by page
    for page_num, page_data in df.groupby("page_number"):
        spans = page_data.to_dict("records")

        # Initialize variables
        current_line = []
        previous_span = None

        for span in spans:
            if previous_span is None:
                current_line.append(span)
            else:
                # check if the current span is on same line as previous_span
                # Calculate the vertical overlap between the spans
                y_top = max(span["y1"], previous_span["y1"])
                y_bottom = min(span["y2"], previous_span["y2"])
                vertical_overlap = y_bottom - y_top

                # Calculate the height of the spans
                span_height = span["y2"] - span["y1"]
                prev_span_height = previous_span["y2"] - previous_span["y1"]
                avg_height = (span_height + prev_span_height) / 2

                # If the vertical overlap is significant, same line
                if vertical_overlap / avg_height > 0.5:
                    current_line.append(span)
                else:
                    # Process the current line and calculate its bounding box
                    lines.append(process_line(current_line, page_num))
                    current_line = [span]  # Start a new line

            previous_span = span

        # Process the last line on the page
        if current_line:
            lines.append(process_line(current_line, page_num))

    # Create a new DataFrame to store lines
    line_df = pd.DataFrame(
        lines,
        columns=[
            "page_number",
            "text",
            "line_bbox_x1",
            "line_bbox_y1",
            "line_bbox_x2",
            "line_bbox_y2",
            "font_size",
            "font",
            "bold",
            "italic",
        ],
    )
    return line_df


def process_line(line, page_num):
    """gathers line metadata"""
    # Calculate the bounding box for the line
    x1_min = min(span["x1"] for span in line)
    y1_min = min(span["y1"] for span in line)
    x2_max = max(span["x2"] for span in line)
    y2_max = max(span["y2"] for span in line)

    # Sort spans by x1 to ensure correct order
    sorted_line = sorted(line, key=lambda span: span["x1"])

    # Join the text of the spans
    line_text = " ".join(span["text"] for span in sorted_line)

    # Get font size, font, bold, and italic attributes
    font_sizes = [span["font_size"] for span in line]
    fonts = [span["font"] for span in line]
    bolds = [span["bold"] for span in line]
    italics = [span["italic"] for span in line]

    # Decide how to aggregate these attributes (e.g., take the most common)
    font_size = max(set(font_sizes), key=font_sizes.count)
    font = max(set(fonts), key=fonts.count)
    bold = max(set(bolds), key=bolds.count)
    italic = max(set(italics), key=italics.count)

    # Return the line data with additional attributes
    return {
        "page_number": page_num,
        "text": line_text,
        "line_bbox_x1": x1_min,
        "line_bbox_y1": y1_min,
        "line_bbox_x2": x2_max,
        "line_bbox_y2": y2_max,
        "font_size": font_size,
        "font": font,
        "bold": bold,
        "italic": italic,
    }


def check_number_density(df, sparsity_df):
    """calculates the ratio of number-text to total text-volume for a page"""
    # Create an empty list to store results
    number_density_results = []

    # Sort values by page number
    df = df.sort_values(by=["page_number"])

    # Loop over each page and calculate total number count and number density
    for page_num, page_df in df.groupby("page_number"):
        # Total number count: Sum the 'lone_num' column
        total_page_num = page_df["lone_num"].sum()

        # Get the sparsity for this page from sparsity_df
        page_sparsity = sparsity_df.loc[
            sparsity_df["page_number"] == page_num, "Sparsity"
        ].values[0]

        # Calculate number density
        page_num_density = total_page_num / page_sparsity if \
            page_sparsity != 0 else 0

        # Append the result as a dictionary to the results list
        number_density_results.append(
            {"page_#": page_num, "page_num_density": page_num_density}
        )

    # Convert the results into a DataFrame
    num_density_df = pd.DataFrame(number_density_results)
    return num_density_df


def calculate_sparsity(df):
    """calulates the ratio of text to empty space of a page"""
    # Group the data by page number, then calculate sparsity per page
    sparsity_per_page = []

    # Group the dataframe by page number
    for page_num, page_df in df.groupby("page_number"):
        # Get page dimensions from the first row of the group
        page_width = page_df["width"].iloc[0]
        page_height = page_df["height"].iloc[0]

        # Calculate the total page area
        total_page_area = page_width * page_height

        # Calculate the total bounding box area for this page
        total_bbox_area = page_df["bbox_area"].sum()

        # Calculate sparsity for this page
        sparsity = (
            (1 - (total_bbox_area / total_page_area)) if total_page_area > 0
            else 0
        )

        # Store the result for this page
        sparsity_per_page.append({"page_number": page_num,
                                  "Sparsity": sparsity})

    # Convert the list of sparsity values into a DataFrame
    sparsity_df = pd.DataFrame(sparsity_per_page)
    return sparsity_df


def is_potential_heading(line_data,
                         line_length_mode,
                         std_line_length,
                         left_margin_mode,
                         off_margin_threshold):
    """Identify potential headings based on line length, margin, etc."""

    line_length = line_data["line_bbox_x2"] - line_data["line_bbox_x1"]
    return (
        line_length < (line_length_mode - 2 * std_line_length)
        or abs(line_data["line_bbox_x1"] - left_margin_mode) >
        off_margin_threshold
    )


def fuzzy_match_heading(extracted_heading, toc_headings, threshold):
    """Use fuzzy matching to check if extracted heading matches text in TOC."""
    best_match, similarity = process.extractOne(extracted_heading,
                                                toc_headings)
    return best_match if similarity >= threshold else None


def detect_formatting(df):
    """uses statistical measures to identify headings, table of contents"""
    toc_candidates = []
    relevant_formatting = []

    # Calculate sparsity per page
    sparsity_per_page = calculate_sparsity(df)
    avg_sparsity = sparsity_per_page["Sparsity"].mean()
    std_sparsity = sparsity_per_page["Sparsity"].std()
    sparsity_mode_series = sparsity_per_page["Sparsity"].mode()
    if not sparsity_mode_series.empty:
        mode_sparsity = sparsity_mode_series.iloc[0]
    else:
        mode_sparsity = avg_sparsity
    sparsity_threshold = (
        ((mode_sparsity - avg_sparsity) / std_sparsity) + 0.5
        if std_sparsity != 0
        else 1
    )

    # Calculate number density per page
    num_density_per_page = check_number_density(df, sparsity_per_page)
    num_density_avg = num_density_per_page["page_num_density"].mean()
    num_density_std = num_density_per_page["page_num_density"].std()
    num_density_mode_series = num_density_per_page["page_num_density"].mode()
    if not num_density_mode_series.empty:
        num_density_mode = num_density_mode_series.iloc[0]
    else:
        num_density_mode = num_density_avg
    num_density_threshold = (
        ((num_density_mode - num_density_avg) / num_density_std) + 4
        if num_density_std != 0
        else 1
    )

    original_lines = bunch_lines(df)
    original_lines_by_page = original_lines.sort_values(by=["page_number"])

    # Initialize lists to store line lengths and margins per page
    l_margin_by_page = []
    line_length_by_page = []

    # Process each page
    for page_num, page_df in original_lines_by_page.groupby("page_number"):
        # Calculate line length average
        line_length_avg = (page_df["line_bbox_x2"] -
                           page_df["line_bbox_x1"]).mean()
        line_length_std = (page_df["line_bbox_x2"] -
                           page_df["line_bbox_x1"]).std()

        page_df["line_bbox_x1_rounded"] = page_df["line_bbox_x1"].round(0)

        # Calculate line position mode
        line_pos_mode_series = page_df["line_bbox_x1_rounded"].mode()

        line_pos_mode_1 = (
            line_pos_mode_series.iloc[0]
            if len(line_pos_mode_series) > 0
            else page_df["line_bbox_x1"].mean()
        )
        line_pos_mode_2 = (
            line_pos_mode_series.iloc[1]
            if len(line_pos_mode_series) > 1
            else page_df["line_bbox_x1"].mean()
        )
        line_pos_mode_3 = (
            line_pos_mode_series.iloc[2]
            if len(line_pos_mode_series) > 2
            else page_df["line_bbox_x1"].mean()
        )
        line_pos_mode_4 = (
            line_pos_mode_series.iloc[3]
            if len(line_pos_mode_series) > 3
            else page_df["line_bbox_x1"].mean()
        )

        # Append to the lists
        line_length_by_page.append(
            {
                "page_number": page_num,
                "line_length_avg_page": line_length_avg,
                "line_length_std_page": line_length_std,
            }
        )

        l_margin_by_page.append(
            {
                "page_number": page_num,
                "page_margin_mode": line_pos_mode_1,
                "page_margin_mode_2": line_pos_mode_2,
                "page_margin_mode_3": line_pos_mode_3,
                "page_margin_mode_4": line_pos_mode_4,
            }
        )

    # Convert lists to DataFrames
    line_length_by_page_df = pd.DataFrame(
        line_length_by_page,
        columns=["page_number",
                 "line_length_avg_page",
                 "line_length_std_page",
                 ]
    ).set_index("page_number")
    l_margin_by_page_df = pd.DataFrame(
        l_margin_by_page,
        columns=[
            "page_number",
            "page_margin_mode",
            "page_margin_mode_2",
            "page_margin_mode_3",
        ],
    ).set_index("page_number")

    # Now, it's safe to check if page_num is in line_length_by_page_df
    for page_num in original_lines_by_page["page_number"].unique():
        page_num = int(page_num)  # Ensure page_num is an integer

        if page_num in line_length_by_page_df.index:
            line_length = line_length_by_page_df.loc[page_num,
                                                     "line_length_avg_page"]
        else:
            continue

    print("Line length and margin stats calculated.")

    # Calculate overall statistics
    line_length_avg_overall = \
        line_length_by_page_df["line_length_avg_page"].mean()

    line_length_std_overall = \
        line_length_by_page_df["line_length_avg_page"].std()

    line_length_mode_series = \
        line_length_by_page_df["line_length_avg_page"].mode()

    if not line_length_mode_series.empty:
        line_length_mode = line_length_mode_series.iloc[0]
    else:
        line_length_mode = line_length_avg_overall
    line_length_threshold = (
        ((line_length_mode - line_length_avg_overall) /
         line_length_std_overall) + 0.1
        if line_length_std_overall != 0 else 1
    )

    l_margin_avg_overall = l_margin_by_page_df["page_margin_mode"].mean()
    l_margin_std_overall = l_margin_by_page_df["page_margin_mode"].std()
    l_margin_mode_series = l_margin_by_page_df["page_margin_mode"].mode()
    if not l_margin_mode_series.empty:
        l_margin_mode = l_margin_mode_series.iloc[0]
    else:
        l_margin_mode = l_margin_avg_overall
    off_margin_threshold = (
        ((l_margin_mode - l_margin_avg_overall) / l_margin_std_overall) + 1
        if l_margin_std_overall != 0
        else 1
    )

    # Now, process each page to identify TOC candidates and relevant formatting
    for page_num in df["page_number"].unique():
        sparsity = \
            sparsity_per_page.set_index("page_number").loc[page_num,
                                                           "Sparsity"]
        num_density = \
            num_density_per_page.set_index("page_#").loc[page_num,
                                                         "page_num_density"]
        line_length = \
            line_length_by_page_df.loc[page_num,
                                       "line_length_avg_page"]
        l_margin = l_margin_by_page_df.loc[page_num, "page_margin_mode"]

        if ((sparsity - avg_sparsity) / std_sparsity) <= sparsity_threshold:
            continue
        elif (num_density >= num_density_threshold) and (
            line_length >= line_length_threshold or
                l_margin >= off_margin_threshold):
            toc_candidates.append(page_num)
        elif line_length >= line_length_threshold or \
                l_margin >= off_margin_threshold:
            relevant_formatting.append(page_num)
        else:
            continue

    # Initialize variables for storing the longest and earliest TOC sequence
    previous_page_num = None
    toc_sequence = []
    longest_toc = []
    earliest_page_num = float("inf")

    for page_num in sorted(toc_candidates):
        if previous_page_num is None or page_num == previous_page_num + 1:
            toc_sequence.append(page_num)
        else:
            if (len(toc_sequence) > len(longest_toc)) or (
                len(toc_sequence) == len(longest_toc)
                and toc_sequence[0] < earliest_page_num
            ):
                longest_toc = toc_sequence.copy()
                earliest_page_num = toc_sequence[0]
            toc_sequence = [page_num]
        previous_page_num = page_num

    if (len(toc_sequence) > len(longest_toc)) or (
        len(toc_sequence) == len(longest_toc) and
        toc_sequence[0] < earliest_page_num
    ):
        longest_toc = toc_sequence

    toc = longest_toc  # List of page numbers in the TOC

    chapter_headings = []

    fuzzy_threshold = 95

    # Iterate through all relevant formatting pages
    for page_num in toc:
        page_df = df[df["page_number"] == page_num]
        toc_text_entries = page_df["text"].tolist()  # Extract TOC headings

        for relevant_page_num in relevant_formatting:
            relevant_page_df = original_lines_by_page[
                original_lines_by_page["page_number"] == relevant_page_num
            ]

            # Extract relevant fields (text and bounding boxes)
            relevant_page_texts = relevant_page_df[
                [
                    "text",
                    "line_bbox_x1",
                    "line_bbox_y1",
                    "line_bbox_x2",
                    "line_bbox_y2",
                    "font_size",
                    "font",
                    "bold",
                    "italic",
                ]
            ].to_dict("records")

            for line in relevant_page_texts:
                if is_potential_heading(
                    line,
                    line_length_mode,
                    line_length_std_overall,
                    l_margin_mode,
                    off_margin_threshold,
                ):
                    # Extract text from line
                    extracted_text = line["text"]

                    # Apply fuzzy matching with TOC
                    matched_heading = fuzzy_match_heading(
                        extracted_text, toc_text_entries, fuzzy_threshold
                    )

                    if matched_heading:
                        chapter_headings.append(
                            {
                                "page_number": relevant_page_num,
                                "text": line["text"],
                                "line_bbox_x1": line["line_bbox_x1"],
                                "line_bbox_y1": line["line_bbox_y1"],
                                "line_bbox_x2": line["line_bbox_x2"],
                                "line_bbox_y2": line["line_bbox_y2"],
                                "font_size": line["font_size"],
                                "font": line["font"],
                                "bold": line["bold"],
                                "italic": line["italic"],
                            }
                        )

    chapter_headings_df = pd.DataFrame(chapter_headings)
    return toc, chapter_headings_df, original_lines


def export_csv(line_df, toc, chapter_headings_df):
    """takes metadata and flagged formatting and saves it as a CSV file"""
    # Initialize flags
    line_df["TOC"] = 0
    line_df["chapter_heading"] = 0

    # Flag lines in TOC pages
    line_df.loc[line_df["page_number"].isin(toc), "TOC"] = 1

    # Create a unique key for matching
    line_df["line_key"] = (
        line_df["page_number"].astype(str)
        + "_"
        + line_df["line_bbox_x1"].astype(str)
        + "_"
        + line_df["line_bbox_y1"].astype(str)
        + "_"
        + line_df["text"].str.strip()
    )

    chapter_headings_df["line_key"] = (
        chapter_headings_df["page_number"].astype(str)
        + "_"
        + chapter_headings_df["line_bbox_x1"].astype(str)
        + "_"
        + chapter_headings_df["line_bbox_y1"].astype(str)
        + "_"
        + chapter_headings_df["text"].str.strip()
    )

    # Flag lines that are chapter headings
    line_df.loc[
        line_df["line_key"].isin(chapter_headings_df["line_key"]),
        "chapter_heading"
    ] = 1

    # Optionally remove the 'line_key' columns
    line_df.drop(columns=["line_key"], inplace=True)
    chapter_headings_df.drop(columns=["line_key"], inplace=True)

    return line_df
