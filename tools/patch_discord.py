"""Patch discord.py-self to add global_name support"""

import discord
import inspect
import shutil
from pathlib import Path

# Get the path to user.py
source_file = inspect.getsourcefile(discord.User)
if not source_file:
    print("Error: Could not find discord User source file")
    exit(1)
user_py_path = Path(source_file)
print(f"Found discord user.py at: {user_py_path}")

# Backup the original
backup_path = user_py_path.with_suffix('.py.backup')
if not backup_path.exists():
    shutil.copy(user_py_path, backup_path)
    print(f"Created backup at: {backup_path}")
else:
    print(f"Backup already exists at: {backup_path}")

# Read the current file
content = user_py_path.read_text()

# Check if already patched
if 'self.global_name' in content:
    print("\n✓ File is already patched with global_name support!")
    exit(0)

print("\nApplying patches...")

# Patch 1: Add global_name to __slots__
old_slots = "__slots__ = ('name', 'id', 'discriminator', 'avatar', 'bot', 'system', '_public_flags', '_state')"
new_slots = "__slots__ = ('name', 'id', 'discriminator', 'avatar', 'bot', 'system', '_public_flags', '_state', 'global_name')"

if old_slots in content:
    content = content.replace(old_slots, new_slots)
    print("✓ Patch 1: Added global_name to __slots__")
else:
    print("✗ Patch 1: Could not find __slots__ definition")
    exit(1)

# Patch 2: Add global_name parsing to _update method
old_update = """    def _update(self, data):
        self.name = data['username']
        self.id = int(data['id'])
        self.discriminator = data['discriminator']
        self.avatar = data['avatar']
        self._public_flags = data.get('public_flags', 0)
        self.bot = data.get('bot', False)
        self.system = data.get('system', False)"""

new_update = """    def _update(self, data):
        self.name = data['username']
        self.id = int(data['id'])
        self.discriminator = data['discriminator']
        self.avatar = data['avatar']
        self._public_flags = data.get('public_flags', 0)
        self.bot = data.get('bot', False)
        self.system = data.get('system', False)
        self.global_name = data.get('global_name')"""

if old_update in content:
    content = content.replace(old_update, new_update)
    print("✓ Patch 2: Added global_name parsing to _update()")
else:
    print("✗ Patch 2: Could not find _update() method")
    exit(1)

# Patch 3: Update existing display_name property to use global_name
old_display_name = """    @property
    def display_name(self):
        """:class:`str`: Returns the user's display name.

        For regular users this is just their username, but
        if they have a guild specific nickname then that
        is returned instead.
        """
        return self.name"""

new_display_name = """    @property
    def display_name(self):
        """:class:`str`: Returns the user's display name.

        For regular users this is their global_name (if set) or username.
        If they have a guild specific nickname then that is returned instead.
        """
        return self.global_name if self.global_name else self.name"""

if old_display_name in content:
    content = content.replace(old_display_name, new_display_name)
    print("✓ Patch 3: Updated display_name property to use global_name")
else:
    print("✗ Patch 3: Could not find display_name property")
    exit(1)

# Write the patched content
user_py_path.write_text(content)
print(f"\n✓ Successfully patched {user_py_path}")
print("\nThe discord.py-self library now supports global_name!")
print("message.author.display_name will now return:")
print("  - global_name (if set by Discord)")
print("  - username (if global_name not set)")
print("\nRestart your bot to use the new feature.")
