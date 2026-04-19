"""
=-=-=-=-=-=-=-=-=-=-=-=-=
File Organizer!
This program will sort the user's downloads folder into smaller, more organized subfolders.

Features:
- Flags duplicates
- Keeps record Logs

Use:
- Ran staright through the terminal (GUI planned)
- Requests user permission before doing anything (default dry-run first)

Logs:
- A simple JSON log, saved to your dowloads folder after every run.
- Can be used to see file movements, and to also manually undo actions

This code is made by KingHyperion (also known as HyperionDoesStuff, or KingHyperion_), licensed under the MIT License
=-=-=-=-=-=-=-=-=-=-=-=-=
"""

# Imports
import os
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime

# Config / Categories
target_folder = Path.home() / "Downloads"

category_map = {
    "Images":       [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", "ico", ".tff", ".tif", ".heic", ".raw"],
    "PDFs":         [".pdf"],
    "Docs":         [".docx", ".doc", ".txt", ".rtf", ".odt", ".xlsx", ".xls", ".ods", ".pptx", ".ppt", ".odp", ".csv", ".md"],
    "Videos":       [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v", ".webm", ".mpeg", ".mpg"],
    "Audio":        [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus"],
    "Archives":     [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
    "Installers":   [".exe", ".msi", ".msix", ".appx"],
    "Code":         [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1", ".sql", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rb", ".php", ".rs"],
    "Shortcuts":    [".lnk", ".url"],
    "3D Models":    [".stl", ".3mf"],
    "MC Modpacks":  [".mrpack"],
    "Misc.":        [],
}

exception_subfolders = set(category_map.keys()) | {"Misc.", "Logs"}

# Optimizers
def get_checksum(filepath: Path, chunk_size: int = 65536) -> str:
    """Return an MD5 hash of a file's contents without loading it all into RAM."""
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        # If file is unable to be read, this is returned:
        return f"UNREADABLE_{filepath.name}"

def get_category(extension: str) -> str:
    """Return the category name for a given file extension (e.g. '.pdf' → 'PDFs')."""
    ext = extension.lower()
    for category, extensions in category_map.items():
        if ext in extensions:
            return category
    return "Misc."

def safe_destination(destination: Path) -> Path:
    """
    If destination already exists, append _2, _3, etc. until the name is free.
    e.g.  report.pdf → report_2.pdf → report_3.pdf
    """
    if not destination.exists():
        return destination
 
    stem   = destination.stem
    suffix = destination.suffix
    parent = destination.parent
    counter = 2
 
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

def is_log_file(filepath: Path) -> bool:
    """Skip log files we created ourselves so we don't try to move them."""
    return filepath.name.startswith("organizer_log_") and filepath.suffix == ".json"

# Organiser
def organize(target_folder: Path, dry_run: bool = True) -> list[dict]:
    """
    Scan target_folder and sort files into category subfolders.
 
    dry_run=True  → plan everything, touch nothing, return the plan.
    dry_run=False → execute the plan and return what actually happened.
 
    Returns a list of log entry dicts, one per file examined.
    """
    log_entries    = []
    seen_checksums = {}   # hash → Path of the first file we saw with that hash
 
    # Collect only direct children that are files (not already-sorted subfolders)
    try:
        all_items = sorted(target_folder.iterdir())
    except PermissionError:
        print(f"\n  ERROR: Cannot access {target_folder}. Check folder permissions.")
        return []
 
    files = [
        item for item in all_items
        if item.is_file()
        and not is_log_file(item)
        and item.name != "desktop.ini"   # Windows system file — leave it alone
    ]
 
    if not files:
        print("\n  No files found to organise.")
        return []
 
    print(f"\n  Scanning {len(files)} file(s) in {target_folder} ...\n")
 
    for filepath in files:
        entry = {
            "file":      filepath.name,
            "original":  str(filepath),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
 
        # 1. Checksum
        checksum = get_checksum(filepath)
 
        # 2. Duplicate check
        if checksum in seen_checksums and not checksum.startswith("UNREADABLE_"):
            original = seen_checksums[checksum]
            entry["action"]     = "DUPLICATE"
            entry["duplicate_of"] = str(original)
            entry["destination"]  = None
            log_entries.append(entry)
            print(f"  ⚠  DUPLICATE  {filepath.name}")
            print(f"          same as: {original.name}\n")
            continue
 
        seen_checksums[checksum] = filepath
 
        # 3. Category & destination
        category    = get_category(filepath.suffix)
        dest_folder = target_folder / category
        destination = safe_destination(dest_folder / filepath.name)
 
        entry["category"]    = category
        entry["destination"] = str(destination)
 
        # 4. Dry-run or real move
        if dry_run:
            entry["action"] = "WOULD_MOVE"
            status_icon     = "→"
        else:
            try:
                dest_folder.mkdir(exist_ok=True)
                shutil.move(str(filepath), destination)
                entry["action"] = "MOVED"
                status_icon     = "✓"
            except (PermissionError, OSError) as e:
                entry["action"] = "ERROR"
                entry["error"]  = str(e)
                status_icon     = "✗"
                print(f"  ✗  ERROR  {filepath.name}: {e}\n")
                log_entries.append(entry)
                continue
 
        log_entries.append(entry)
 
        # Trim long filenames for cleaner console output
        name_display = filepath.name if len(filepath.name) <= 45 else filepath.name[:42] + "..."
        print(f"  {status_icon}  [{category:<12}]  {name_display}")
 
    return log_entries

# Receipt Printer
def print_summary(log_entries: list[dict], dry_run: bool) -> None:
    """Print a clean breakdown of what happened (or what would happen)."""
    if not log_entries:
        return
 
    moves      = [e for e in log_entries if e["action"] in ("MOVED", "WOULD_MOVE")]
    duplicates = [e for e in log_entries if e["action"] == "DUPLICATE"]
    errors     = [e for e in log_entries if e["action"] == "ERROR"]
 
    # Count by category
    category_counts: dict[str, int] = {}
    for entry in moves:
        cat = entry.get("category", "Other")
        category_counts[cat] = category_counts.get(cat, 0) + 1
 
    verb = "Would move" if dry_run else "Moved"
 
    print()
    print("  " + "─" * 46)
    print(f"  {'SUMMARY':^46}")
    print("  " + "─" * 46)
 
    if category_counts:
        for category, count in sorted(category_counts.items()):
            label = f"{verb} → {category}"
            print(f"  {label:<36} {count:>4} file(s)")
    else:
        print(f"  No files to move.")
 
    if duplicates:
        print(f"  {'Duplicates found (skipped)':<36} {len(duplicates):>4} file(s)")
 
    if errors:
        print(f"  {'Errors (check log)':<36} {len(errors):>4} file(s)")
 
    print("  " + "─" * 46)
    total = len(moves) + len(duplicates) + len(errors)
    print(f"  {'Total files examined':<36} {total:>4}")
    print("  " + "─" * 46)
    print()

# Log Librarian
def save_log(log_entries: list[dict], target_folder: Path) -> Path:
    """Save a JSON log file to target_folder. Returns the log file path."""
    log_dir = target_folder / "Logs"
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path  = log_dir / f"organizer_log_{timestamp}.json"
 
    payload = {
        "run_at":      datetime.now().isoformat(timespec="seconds"),
        "target":      str(target_folder),
        "total_files": len(log_entries),
        "entries":     log_entries,
    }
 
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
 
    return log_path

"""
Main Code / Actual Organiser Begins Here:
"""

def main() -> None:
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║           DOWNLOADS FILE ORGANIZER           ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(f"\n  Target folder: {target_folder}\n")
 
    # Sanity-check the folder exists
    if not target_folder.exists():
        print(f"  ERROR: Folder not found: {target_folder}")
        print("  Edit target_folder at the top of this file and try again.")
        input("\n  Press Enter to exit.")
        return
    
    old_logs = [f for f in target_folder.iterdir() if is_log_file(f)]
    if old_logs:
        log_dir = target_folder / "Logs"
        log_dir.mkdir(exist_ok=True)
        for log in old_logs:
            shutil.move(str(log), log_dir / log.name)
        print(f"  i  Moved {len(old_logs)} existing log(s) into the Logs folder.\n")
 
    # Step 1: Always dry-run first
    print("  STEP 1 OF 2 — DRY RUN (nothing will be moved yet)\n")
    print("  " + "─" * 46)
 
    dry_run_log = organize(target_folder, dry_run=True)
 
    if not dry_run_log:
        input("\n  Press Enter to exit.")
        return
 
    print_summary(dry_run_log, dry_run=True)
 
    # Step 2: Ask to proceed
    answer = input("  Proceed with the real move? [y/N]: ").strip().lower()
 
    if answer != "y":
        print("\n  Cancelled. Nothing was moved.")
        input("  Press Enter to exit.")
        return
 
    # Step 3: Real run
    print()
    print("  STEP 2 OF 2 — MOVING FILES\n")
    print("  " + "─" * 46)
 
    real_log = organize(target_folder, dry_run=False)
 
    print_summary(real_log, dry_run=False)
 
    # Step 4: Save log
    if real_log:
        log_path = save_log(real_log, target_folder)
        print(f"  Log saved to:\n  {log_path}\n")
        print("  Open that file to review every action taken.")
        print("  If anything moved incorrectly, you can manually undo it from there.")
 
    input("\n  Done. Press Enter to exit.")
 
 
if __name__ == "__main__":
    main()