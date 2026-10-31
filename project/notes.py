#!/usr/bin/env python3
"""Review notes for one edit.

Each note has a timestamp in seconds, an issue, a status (open or fixed),
and an optional path to a still that shows the fix.

  python project/notes.py add project_dir --time 4.2 --issue "caption covers the subject"
  python project/notes.py summary project_dir
"""
import argparse, json, os, time

NOTES_NAME = "review_notes.json"

def notes_path(project_dir):
    return os.path.join(project_dir, NOTES_NAME)

def load_notes(project_dir):
    path = notes_path(project_dir)
    if not os.path.exists(path):
        return []
    return json.load(open(path, encoding="utf-8"))

def save_notes(project_dir, notes):
    os.makedirs(project_dir, exist_ok=True)
    json.dump(notes, open(notes_path(project_dir), "w", encoding="utf-8"), indent=2)
    open(notes_path(project_dir), "a", encoding="utf-8").write("\n")

def add_note(project_dir, t, issue, status="open", still=None):
    if status not in ("open", "fixed"):
        raise ValueError("status must be open or fixed")
    notes = load_notes(project_dir)
    note = {
        "id": f"n{len(notes) + 1}",
        "t": round(float(t), 3),
        "issue": issue.strip(),
        "status": status,
        "still": still or "",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    notes.append(note)
    save_notes(project_dir, notes)
    return note

def set_status(project_dir, note_id, status, still=None):
    notes = load_notes(project_dir)
    for note in notes:
        if note["id"] == note_id:
            note["status"] = status
            if still:
                note["still"] = still
            save_notes(project_dir, notes)
            return note
    raise KeyError(note_id)

def summary(project_dir):
    notes = load_notes(project_dir)
    if not notes:
        return "No review notes."
    lines = ["Review notes", ""]
    for note in notes:
        still = f" still: {note['still']}" if note.get("still") else ""
        lines.append(f"{note['id']}  {note['t']:.2f}s  {note['status']:5}  {note['issue']}{still}")
    open_count = sum(1 for n in notes if n["status"] == "open")
    lines.append("")
    lines.append(f"{open_count} open, {len(notes) - open_count} fixed, {len(notes)} total.")
    return "\n".join(lines) + "\n"

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("project_dir")
    add.add_argument("--time", type=float, required=True)
    add.add_argument("--issue", required=True)
    add.add_argument("--status", default="open")
    add.add_argument("--still")
    sm = sub.add_parser("summary")
    sm.add_argument("project_dir")
    fix = sub.add_parser("fix")
    fix.add_argument("project_dir")
    fix.add_argument("note_id")
    fix.add_argument("--still")
    args = ap.parse_args(argv)
    if args.cmd == "add":
        note = add_note(args.project_dir, args.time, args.issue, status=args.status, still=args.still)
        print(note["id"])
    elif args.cmd == "fix":
        set_status(args.project_dir, args.note_id, "fixed", still=args.still)
        print(summary(args.project_dir))
    else:
        print(summary(args.project_dir), end="")

if __name__ == "__main__":
    main()
