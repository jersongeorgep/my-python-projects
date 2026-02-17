# lib/html_parser.py
import re


def clean_html(html: str | None) -> str:
    """
    Ensure we always pass a clean HTML string to quill & docx.
    Removes null bytes and ensures type is str.
    """
    if html is None:
        return ""
    s = str(html)
    s = s.replace("\x00", "")
    return s


def html_to_plain(html: str | None) -> str:
    """
    Strip HTML tags – used only if we want plain text somewhere.
    """
    if html is None:
        return ""
    s = str(html).replace("\x00", "")
    return re.sub(r"<[^>]+>", "", s)
