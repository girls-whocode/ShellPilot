# Preview System

ShellPilot includes a modular preview system:

## Text / Code
- Shows syntax-highlighted code using Rich

## Images
- Uses Pillow if available
- Falls back to metadata mode otherwise

## Binary Files
- Hex dump preview

## Compressed Archives
- Supports:
  - .gz
  - .bz2
  - .xz
  - .zip (future)
