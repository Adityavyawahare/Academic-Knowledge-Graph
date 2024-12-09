import json
import requests
from io import BytesIO
import PyPDF2
import re

def extract_paper_content_from_url(pdf_url, paper_title):
    """
    Extract content and section headings from PDF using PyPDF2

    Args:
        pdf_url (str): URL of the PDF
        paper_title (str): Manually provided paper title

    Returns:
        dict: Paper title with extracted content and section headings
    """
    try:
        # Fetch the PDF from the URL
        response = requests.get(pdf_url)
        response.raise_for_status()  # Check if the request was successful

        # Read the PDF from the binary content
        pdf_stream = BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)

        content = []
        section_headings = {}
        current_heading = None

        # Regex patterns to detect section headings
        section_pattern = re.compile(r"^\d+(\.\d+)*\s+[A-Z].*", re.MULTILINE)
        # Regex pattern to detect non-numeric, all-uppercase headings
        uppercase_heading_pattern = re.compile(r"^[A-Z\s]+$")  # Matches all-uppercase headings


        # Iterate over each page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()

            # Collect content lines and detect section headings
            for line in text.splitlines():
                line = line.strip()
                if line:
                    # Check for section headings
                    if section_pattern.match(line):
                        current_heading = line  # Start new section
                        section_headings[current_heading] = []
                    elif uppercase_heading_pattern.match(line):
                        current_heading = line # Clean uppercase heading
                        section_headings[current_heading] = []  # Create a new section
                    elif current_heading:
                        # Append content to the current section
                        section_headings[current_heading].append(line)
                    else:
                        content.append(line)

        # Combine section contents into single paragraphs
        for heading in section_headings:
            section_headings[heading] = " ".join(section_headings[heading])

        # Format content and headings
        formatted_content = "\n".join(content)
        structured_content = {
            "title": paper_title,
            "content": formatted_content,
            "sections": section_headings
        }
        return structured_content
    except Exception as e:
        print(f"Error extracting content from URL {pdf_url}: {e}")
        return None
