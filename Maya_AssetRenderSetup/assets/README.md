# Assets

| File | Purpose | In repo |
|------|---------|---------|
| `banner.png` | README hero image | Yes |
| `shelf_icon.png` | Custom shelf button (`install/install.py`) | Yes |
| `demo_AssetRenderSetup.mp4` | Demo walkthrough (~10.6 MB) | Yes |

Re-run `install/install.py` in Maya after replacing `shelf_icon.png` or moving the repository.

## Demo video in README

The root `README.md` embeds the MP4 with a **relative** path (`assets/demo_AssetRenderSetup.mp4`) so it plays on GitHub **after you push** — no drag-and-drop on github.com.

Commit `demo_AssetRenderSetup.mp4` together with the rest of the tool (git allows files well above 10 MB; the 10 MB limit only applies to the web README uploader).

### Alternative (UE_AssetAuditor_Tool style)

Drag-and-drop `demo_AssetRenderSetup.mp4` into the README editor on GitHub to get a  
`https://github.com/user-attachments/assets/…` URL (file must be **under 10 MB** for the web uploader; this file is ~10.6 MB). Replace the `<video src="raw.githubusercontent.com/…">` block if you prefer that CDN.
