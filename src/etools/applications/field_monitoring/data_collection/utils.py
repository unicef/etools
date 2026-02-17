import re
from html.parser import HTMLParser


class HTMLTagStripper(HTMLParser):
    """HTML parser that strips all tags and returns clean text."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_data(self):
        return ''.join(self.text)


def clean_narrative_finding(text):
    """
    Clean HTML and MS Word formatting tags from narrative finding text.
    
    Args:
        text: The raw text potentially containing HTML/MS Word formatting
        
    Returns:
        Cleaned text with all formatting tags removed
    """
    if not text:
        return ''
    
    # Strip HTML tags
    stripper = HTMLTagStripper()
    try:
        stripper.feed(text)
        cleaned = stripper.get_data()
    except (ValueError, TypeError):
        # If HTML parsing fails, fall back to regex
        cleaned = text
    
    # Remove common MS Word XML tags and styling
    # Remove XML tags like <w:p>, <w:r>, etc.
    cleaned = re.sub(r'</?w:[^>]+>', '', cleaned)
    
    # Remove remaining HTML/XML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    
    # Remove MS Word specific characters and artifacts
    cleaned = re.sub(r'&nbsp;', ' ', cleaned)
    cleaned = re.sub(r'&[a-zA-Z]+;', '', cleaned)  # Remove HTML entities
    
    # Clean up excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned
