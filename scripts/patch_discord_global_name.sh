#!/bin/bash

# Patch discord.py-self to add global_name support
# This patches the venv's discord installation

set -e

VENV_DISCORD="venv/lib/python3.10/site-packages/discord/user.py"

if [ ! -f "$VENV_DISCORD" ]; then
    echo "Error: $VENV_DISCORD not found"
    echo "Make sure venv exists and discord.py-self is installed"
    exit 1
fi

echo "Patching discord.py-self to add global_name support..."

# Check if already patched
if grep -q "self.global_name" "$VENV_DISCORD"; then
    echo "✓ Already patched!"
    exit 0
fi

# Backup
cp "$VENV_DISCORD" "${VENV_DISCORD}.backup"
echo "✓ Created backup at ${VENV_DISCORD}.backup"

# Apply patches using Python
./venv/bin/python3 << 'EOPYTHON'
from pathlib import Path

user_py = Path('venv/lib/python3.10/site-packages/discord/user.py')
content = user_py.read_text()

# Patch 1: Add global_name to __slots__
old_slots = """    __slots__ = (
        'name',
        'id',
        'discriminator',
        '_avatar',
        '_avatar_decoration',
        '_banner',
        '_accent_colour',
        'bot',
        'system',
        '_public_flags',
        '_cs_note',
        '_state',
    )"""

new_slots = """    __slots__ = (
        'name',
        'id',
        'discriminator',
        '_avatar',
        '_avatar_decoration',
        '_banner',
        '_accent_colour',
        'bot',
        'system',
        '_public_flags',
        '_cs_note',
        '_state',
        'global_name',
    )"""

content = content.replace(old_slots, new_slots)
print("✓ Patch 1: Added global_name to __slots__")

# Patch 2: Add global_name to _update
content = content.replace(
    "        self.system = data.get('system', False)",
    "        self.system = data.get('system', False)\n        self.global_name = data.get('global_name')"
)
print("✓ Patch 2: Added global_name parsing to _update()")

# Patch 3: Update display_name
content = content.replace(
    "        return self.name\n\n    @cached_slot_property('_cs_note')",
    "        return self.global_name if self.global_name else self.name\n\n    @cached_slot_property('_cs_note')"
)
print("✓ Patch 3: Updated display_name to use global_name")

# Patch 4: Update _copy
old_copy = """        self.bot = user.bot
        self.system = user.system
        self._state = user._state

        return self"""

new_copy = """        self.bot = user.bot
        self.system = user.system
        self._state = user._state
        self.global_name = user.global_name

        return self"""

content = content.replace(old_copy, new_copy)
print("✓ Patch 4: Added global_name to _copy()")

user_py.write_text(content)
EOPYTHON

# Clear Python cache
find venv/lib/python3.10/site-packages/discord -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "✅ Successfully patched discord.py-self!"
echo "The bot will now use Discord display names (global_name) instead of account names."
