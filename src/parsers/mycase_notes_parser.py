from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re

def parse_notes_html(html: str) -> List[Dict[str, Any]]:
    """
    Parses the HTML of the MyCase notes page and extracts note data.
    
    Args:
        html: The HTML content of the page (after clicking "Read more" buttons).
        
    Returns:
        A list of dictionaries, each representing a note.
    """
    soup = BeautifulSoup(html, "html.parser")
    notes = []
    
    # Target rows based on the user requirement: tr.notes_item
    note_rows = soup.select("tr.notes_item")
    
    for row in note_rows:
        try:
            # 1. ID - Extraído del atributo data-id
            note_id = row.get("data-id")
            
            # 2. Subject - Texto dentro de .note-subject
            subject_el = row.select_one(".note-subject")
            subject = subject_el.get_text(strip=True) if subject_el else ""
            
            # 3. Body - Texto del div .note-item-full-content (limpio de etiquetas HTML)
            body_el = row.select_one(".note-item-full-content")
            # If not expanded, this might be empty or missing. 
            # The scraping logic should ensure it's visible.
            body = body_el.get_text(separator="\n", strip=True) if body_el else ""
            
            # 4. Date - Texto de la celda .last_child.note_display
            date_el = row.select_one(".last_child.note_display")
            date = date_el.get_text(strip=True) if date_el else ""
            
            # 5. Author - Texto dentro de .text-muted.small.font-italic
            author_el = row.select_one(".text-muted.small.font-italic")
            author = ""
            if author_el:
                # Omitiendo etiquetas de fecha si es posible.
                # Author element often contains time/date info in spans.
                # We can try to get only the text directly inside the element or remove spans.
                author_text = author_el.get_text(strip=True)
                # Simple cleanup: often it looks like "John Doe - 10/10/2023" or has sub-elements.
                # If there are sub-elements with dates, we can remove them.
                for sub in author_el.find_all(["span", "time"]):
                    sub.decompose()
                author = author_el.get_text(strip=True)
                
            notes.append({
                "id": note_id,
                "subject": subject,
                "body": body,
                "date": date,
                "author": author
            })
            
        except Exception as e:
            # Log error or skip? We'll skip this row for now but ideally log it.
            continue
            
    return notes
