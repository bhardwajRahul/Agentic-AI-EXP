import re
import html


def clean_email_body(text: str) -> str:
    # 1. Decode HTML entities (e.g., convert &#39; to ')
    text = html.unescape(text)

    # 2. Strip ZWNJ and other invisible junk
    text = re.sub(r"[^\x20-\x7e]", r"", text)

    # 3. Remove repeated special characters (like those divider lines -----)
    text = re.sub(r"[-*=_]{3,}", " ", text)

    # 4. Normalize whitespace
    text = " ".join(text.split())

    text = re.sub(r"\(mailto:[^)]*\)", "", text)

    # Optional: Clean up the [Awesome], [Decent] text left behind
    text = re.sub(r"\[Awesome\]|\[Decent\]|\[Not Great\]", "", text)

    return text
