"""
scan_xss_candidates.py — narrows the full-codebase XSS sweep down to a
reviewable list, instead of manually reading 250+ unsafe_allow_html blocks.

Heuristic: for every unsafe_allow_html=True call, look at the ~15 lines
above it and flag any that interpolate a variable/dict-key matching a
known free-text field name. This WILL have false positives (some flagged
spots are already escaped, or the value isn't actually user-controlled)
and may have false negatives (a risky field name not in this list). It's
a triage tool, not a guarantee — every hit still needs a human look.

Run: python scan_xss_candidates.py
"""

import re
import os

SUSPECT_FIELDS = [
    "notes", "note", "reason", "message", "msg", "comment", "description",
    "address", "phone", "holder_name", "flag_reason", "override_reason",
    "raw_extracted_text", "document_number", "farm_name", "full_name",
    "company", "username", "other_chem", "flagged_by",
]

SKIP_PREFIXES = ("fix_", "add_", "scope_", "wire_", "group_", "convert_",
                  "style_", "seed_")

field_pattern = re.compile(
    r"\{[^}]*\b(" + "|".join(re.escape(f) for f in SUSPECT_FIELDS) + r")\b[^}]*\}"
)

results = []

for fname in sorted(os.listdir(".")):
    if not fname.endswith(".py"):
        continue
    if fname.startswith(SKIP_PREFIXES) or fname == "scan_xss_candidates.py":
        continue

    try:
        with open(fname, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        continue

    for i, line in enumerate(lines):
        if "unsafe_allow_html=True" not in line:
            continue
        window_start = max(0, i - 15)
        window = lines[window_start:i + 1]
        window_text = "".join(window)

        already_partial = "escape_html(" in window_text

        matches = field_pattern.findall(window_text)
        if matches:
            results.append({
                "file": fname,
                "line": i + 1,
                "fields": sorted(set(matches)),
                "partial": already_partial,
            })

if not results:
    print("No candidates found.")
else:
    print(f"{len(results)} candidate block(s) found across {len(set(r['file'] for r in results))} file(s):\n")
    for r in results:
        flag = " [already has escape_html somewhere in block — verify coverage]" if r["partial"] else ""
        print(f"{r['file']}:{r['line']}  fields={r['fields']}{flag}")

print("\nThis is a candidate list, not a confirmed vulnerability list.")
print("Each hit needs a human look: is the field really user-controlled,")
print("and is it actually unescaped in that specific spot.")
