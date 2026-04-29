#!/usr/bin/env python3
"""Post-processing fixes for constrained-elastic-surface-nets.md"""

import re
from pathlib import Path

# Resolve path relative to this script so it works on any OS
script_dir = Path(__file__).parent
input_file = script_dir / "output" / "constrained-elastic-surface-nets" / "constrained-elastic-surface-nets.md"

if not input_file.exists():
    raise FileNotFoundError(f"Input file not found: {input_file}")

content = input_file.read_text(encoding='utf-8')

original_content = content

# Fix math formulas with spaced numbers
# $5 1 2 \mathrm { x} 5 1 2 \mathrm { x} 8 7$ -> $512 \times 512 \times 87$
content = re.sub(r'\$5 1 2 \\mathrm \{ x\} 5 1 2 \\mathrm \{ x\} 8 7\$', r'$512 \\times 512 \\times 87$', content)

# $0. 2 5 { \bf x} 0. 2 5 ~ \mathrm { m m}$ -> $0.25 \times 0.25$ mm
content = re.sub(r'\$0\. 2 5 \{ \\bf x\} 0\. 2 5 ~ \\mathrm \{ m m\}\$', r'$0.25 \\times 0.25$ mm', content)

# $1. 4 ~ \mathrm { m m}$ -> $1.4$ mm
content = re.sub(r'\$1\. 4 ~ \\mathrm \{ m m\}\$', r'$1.4$ mm', content)

# $1 9 \mathrm { x} 1 9 \mathrm { x} 1 9$ -> $19 \times 19 \times 19$
content = re.sub(r'\$1 9 \\mathrm \{ x\} 1 9 \\mathrm \{ x\} 1 9\$', r'$19 \\times 19 \\times 19$', content)

# Fix 7^3, 13^3, 19^3 formatting (Gaussian filter sizes)
content = re.sub(r'\$7\^\{3\}\$', r'$7^3$', content)
content = re.sub(r'\$1 3\^\{3\}\$', r'$13^3$', content)
content = re.sub(r'\$1 9\^\{3\}\$', r'$19^3$', content)

# Fix typos
content = content.replace('binary-segemented', 'binary-segmented')
content = content.replace('arbitrarilyly', 'arbitrarily')
content = content.replace('artfacts', 'artifacts')

# Fix reference page ranges (numbers run together)
content = content.replace('pages 5766', 'pages 57-66')
content = content.replace('pages 8998', 'pages 89-98')
content = content.replace('pages 5562', 'pages 55-62')
content = content.replace('pages 421428', 'pages 421-428')
content = content.replace('pages 163169', 'pages 163-169')
content = content.replace('pages 91108', 'pages 91-108')
content = content.replace('pages 7884', 'pages 78-84')
content = content.replace('pages 2632', 'pages 26-32')
content = content.replace('pages 2130', 'pages 21-30')

# Fix "relevent" typo
content = content.replace('relevent', 'relevant')

# Write back
input_file.write_text(content, encoding='utf-8')

# Count changes
changes = sum(1 for a, b in zip(original_content, content) if a != b)
print(f"Applied fixes to {input_file}")
print(f"Characters changed: {len(original_content) - len(content)} removed, ~{changes} modified")
