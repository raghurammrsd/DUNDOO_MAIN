import re

def extract_number(text):
    match = re.search(r'\d+', text)
    if match:
        return int(match.group())
    return None


def extract_product_name(text):

    text = re.sub(r'\d+\s*(kg|g|gm|litre|l|pcs)?', '', text.lower())

    remove_words = [
        "add","product","create","new",
        "of","the","price","quantity"
    ]

    words = text.split()
    cleaned = [w for w in words if w not in remove_words]

    if cleaned:
        return cleaned[-1].title()

    return None