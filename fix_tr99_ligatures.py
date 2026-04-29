#!/usr/bin/env python3
"""Post-processing fixes for TR99-09.md - fixing OCR ligature issues"""

import re
from pathlib import Path

# Resolve path relative to this script so it works on any OS
script_dir = Path(__file__).parent
input_file = script_dir / "output" / "TR99-09" / "TR99-09.md"

if not input_file.exists():
    raise FileNotFoundError(f"Input file not found: {input_file}")

content = input_file.read_text(encoding='utf-8')

original_content = content

# Fix OCR ligature issues where 'fi', 'fl', 'ff' ligatures are broken

# Common patterns with broken ligatures:
# "rst" at word boundaries often means "first"
# Split patterns like "ob ject" -> "object", "dif ferent" -> "different"

# Fix common broken words
replacements = [
    # fi ligature breaks
    (r'\brst\b', 'first'),
    (r'\bde ned\b', 'defined'),  
    (r'\bde ne\b', 'define'),
    (r'\bde nition\b', 'definition'),
    (r'\bspeci c\b', 'specific'),
    (r'\bspeci ed\b', 'specified'),
    (r'\bsigni cant\b', 'significant'),
    (r'\bclassi cation\b', 'classification'),
    (r'\bclassi ed\b', 'classified'),
    (r'\bclassi er\b', 'classifier'),
    (r'\bveri ed\b', 'verified'),
    (r'\bveri cation\b', 'verification'),
    (r'\bsimpli ed\b', 'simplified'),
    (r'\bidenti ed\b', 'identified'),
    (r'\bidenti cation\b', 'identification'),
    (r'\bquanti ed\b', 'quantified'),
    
    # fl ligature breaks
    (r'\b ow\b', 'flow'),
    (r'\b oat\b', 'float'),
    (r'\b uid\b', 'fluid'),
    (r'\bre ection\b', 'reflection'),
    (r'\bre ected\b', 'reflected'),
    (r'\bin uence\b', 'influence'),
    (r'\bin uenced\b', 'influenced'),
    (r'\bcon ict\b', 'conflict'),
    
    # ff ligature breaks  
    (r'\bdi erent\b', 'different'),
    (r'\bdi erence\b', 'difference'),
    (r'\bdi cult\b', 'difficult'),
    (r'\be ect\b', 'effect'),
    (r'\be ective\b', 'effective'),
    (r'\be iciency\b', 'efficiency'),
    (r'\be icient\b', 'efficient'),
    (r'\ba ect\b', 'affect'),
    (r'\ba ected\b', 'affected'),
    (r'\bo er\b', 'offer'),
    (r'\bo ered\b', 'offered'),
    (r'\bsu er\b', 'suffer'),
    (r'\bsu ered\b', 'suffered'),
    
    # Split words with spaces
    (r'\bob ject\b', 'object'),
    (r'\bsub ject\b', 'subject'),
    (r'\bpro ject\b', 'project'),
    
    # Common OCR artifacts
    (r'\bgure\b', 'figure'),  # "fi" lost at start
    (r'\ble\b(?=\s+\d)', 'file'),  # file before numbers
]

# Apply regex replacements
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

# Fix Figure references: "Figure" where "gure" was fixed
content = re.sub(r'\bFigure\s+(\d)', r'Figure \1', content)

# Fix any remaining spacing issues around punctuation
content = re.sub(r'\s+([,.])', r'\1', content)

# Write back
input_file.write_text(content, encoding='utf-8')

print(f"Applied ligature fixes to {input_file}")
print(f"Original length: {len(original_content)}, New length: {len(content)}")
