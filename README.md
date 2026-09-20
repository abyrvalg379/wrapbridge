# WrapBridge

![WrapBridge](cover.png)

Blender ⇄ Faceform Wrap bridge. Sends your base mesh and scan to Wrap and brings the wrapped result back — without touching Explorer or a single manual path.

*Документация на русском: [README.ru.md](README.ru.md)*

![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange) ![License](https://img.shields.io/badge/License-GPL--3.0-blue)

## What it does

N-panel (**WrapBridge**), three buttons:

- **Send to Wrap** — exports Base + Scan as hot OBJs and opens the project in the Wrap GUI. If Wrap is already running, it just refreshes the files (the paths in the project are constant — recalculating the `LoadGeom` nodes is enough). If the graph template has changed, the fresh project is reopened automatically.
- **Export + Compute** — the same export plus a headless `WrapCmd` run. No GUI at all. For graphs that don't require manual edits (points are stored inside the template).
- **Import Results** — pulls the results of all `SaveGeom` nodes back into the scene.

The panel has **Base** and **Scan** slots; modifiers are applied on export.

## How it works

1. WrapBridge stores a `.wrap` template with your wrapping graph.
2. On every run it rewrites the `LoadGeom` paths to the hot files in `%TEMP%\wrapbridge\` (`base.obj`, `scan.obj`).
3. Anything written by `Save*` nodes is found automatically on import — no hardcoded result names.

The graph itself lives in Wrap: build it once in the GUI (points, FastWrapping, brush — whatever you need), point `LoadGeom` at the hot files and save it as `templates/template.wrap`. Points are stored inside the template, so subsequent runs are fully automatic.

## Installation

**Extension** (Blender 4.2+): download `wrapbridge_v*.zip` from the [latest release](https://github.com/abyrvalg379/wrapbridge/releases/latest), then *Preferences → Get Extensions → ⌄ Install from Disk*.

Legacy zips are no longer supported.

**Requirements:** Faceform Wrap in `C:\Program Files\Faceform\` (the path is the `WRAP_CMD` constant in the source — adjust to taste).

## Build

```
python build.py    # -> ../out/wrapbridge_v*_extension.zip
```

## Notes

- Tested with Faceform Wrap 2025.10.8 (headless `WrapCmd compute` works on the free trial).
- `.wrap` projects are JSON: node connections live inside the parameter plugs (`connectedNodeId`); graph templates are easier to assemble in the Wrap GUI than by hand.

## License

GPL-3.0-or-later. Author: Maksim Kovalev.
