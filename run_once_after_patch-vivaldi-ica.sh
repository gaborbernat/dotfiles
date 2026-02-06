#!/bin/bash
set -euo pipefail

PREFS="$HOME/Library/Application Support/Vivaldi/Default/Preferences"

if [[ ! -f "$PREFS" ]]; then
    echo "Vivaldi preferences not found, skipping"
    exit 0
fi

if grep -q '"extensions_to_open".*ica' "$PREFS" 2>/dev/null; then
    echo "Vivaldi ica auto-open already configured"
    exit 0
fi

echo "Patching Vivaldi to auto-open .ica files..."
python3 -c "
import json
from pathlib import Path

prefs_path = Path('$PREFS')
prefs = json.loads(prefs_path.read_text())

download = prefs.setdefault('download', {})
extensions = download.get('extensions_to_open', '')
if 'ica' not in extensions:
    download['extensions_to_open'] = 'ica' if not extensions else f'{extensions}:ica'
    prefs_path.write_text(json.dumps(prefs))
    print('Patched Vivaldi to auto-open .ica files')
else:
    print('Already configured')
"
