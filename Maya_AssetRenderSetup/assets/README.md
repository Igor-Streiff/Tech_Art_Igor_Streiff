# Assets

| File | Purpose | In repo |
|------|---------|---------|
| `banner.png` | README hero image | Yes |
| `shelf_icon.png` | Custom shelf button (`install/install.py`) | Yes |
| `demo_AssetRenderSetup.mp4` | Demo walkthrough (~10.6 MB) | Yes |

Re-run `install/install.py` in Maya after replacing `shelf_icon.png` or moving the repository.

## Demo video in README

GitHub **strips `<video>` tags** in README (relative paths and `raw.githubusercontent.com` both fail). What works:

1. **Bare URL on its own line** (blank line above) — same pattern as repo MP4s:
   `https://github.com/Igor-Streiff/Tech_Art_Igor_Streiff/raw/main/Maya_AssetRenderSetup/assets/demo_AssetRenderSetup.mp4`
2. **`user-attachments` URL** — drag-and-drop in the GitHub README editor (UE_AssetAuditor style). File must be **under 10 MB**; this demo is ~10.6 MB, so compress first or use option 1.

Commit `demo_AssetRenderSetup.mp4` in git (no 10 MB limit for repo files; the 10 MB cap is only for the web README uploader).
