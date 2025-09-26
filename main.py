import json
from datetime import date

# In-memory storage for user notes
user_notes = {}

def create_note(username: str, title: str, content: str) -> str:
    """
    Create a new note for a given user.
    
    Args:
        username (str): The username who owns the note.
        title (str): Title of the note. Must be unique per user.
        content (str): Content of the note.

    Returns:
        str: JSON response indicating success or failure.
    """
    if username not in user_notes:
        user_notes[username] = []
    for note in user_notes[username]:
        if note["title"] == title:
            return json.dumps({"success": False, "message": "Note title already exists"})
    user_notes[username].append({
        "id": len(user_notes[username]) + 1,
        "date": str(date.today()),
        "title": title,
        "content": content
    })
    return json.dumps({"success": True, "message": "Note created"})

def get_note(username: str, title: str) -> str:
    """
    Retrieve a note by title for a given user.
    
    Args:
        username (str): The username who owns the note.
        title (str): Title of the note to retrieve.
    
    Returns:
        str: JSON response with note data or error message.
    """
    for note in user_notes.get(username, []):
        if note["title"] == title:
            return json.dumps({"success": True, "note": note})
    return json.dumps({"success": False, "message": "Note not found"})

def list_notes(username: str) -> str:
    """
    List all notes belonging to a given user.
    
    Args:
        username (str): The username whose notes should be listed.
    
    Returns:
        str: JSON response containing list of notes (id, title, date).
    """
    notes = [
        {"id": n["id"], "title": n["title"], "date": n["date"]}
        for n in user_notes.get(username, [])
    ]
    return json.dumps({"success": True, "notes": notes})

def delete_note(username: str, title: str) -> str:
    """
    Delete a specific note by title for a given user.
    
    Args:
        username (str): The username who owns the note.
        title (str): Title of the note to delete.
    
    Returns:
        str: JSON response confirming deletion or error message.
    """
    notes = user_notes.get(username, [])
    for i, note in enumerate(notes):
        if note["title"] == title:
            del notes[i]
            return json.dumps({"success": True, "message": "Note deleted"})
    return json.dumps({"success": False, "message": "Note not found"})


if __name__ == "__main__":
    user = "demo"

    print("== Create Notes ==")
    print(create_note(user, "Sport Cars", "Top 10 new sport cars"))
    print(create_note(user, "Luxury Cars", "Top 10 new luxury cars"))

    print("\n== List Notes ==")
    print(list_notes(user))

    print("\n== Get a Note ==")
    print(get_note(user, "Sport Cars"))

    print("\n== Delete a Note ==")
    print(delete_note(user, "Luxury Cars"))

    print("\n== List Notes After Deletion ==")
    print(list_notes(user))
