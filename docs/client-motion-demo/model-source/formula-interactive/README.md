# Interactive formula demo

Independent local viewer for the supplied Daily Emulsion and Body Oil 02 filled GLBs. Drag to orbit, wheel to zoom, empty/filled toggle, quarter-turn and reset. The production site remains client1.35 with empty packaging.

Build the standalone offline viewer with `node build.mjs <demo-output-directory>`. Then `python3 build_inline.py <demo-output-directory> <fragment-directory>` creates one self-contained Codex visualization per product. Run `python3 verify.py <demo-output-directory> <fragment-directory>` to validate original model bytes, embedded textures, script syntax and the 1 MB fragment limit.

The inline previews contain compressed Three.js, its existing GLTFLoader and original GLB bytes. The renderer uses two ordered transmission passes for approximate nested liquid and glass; the formula is a static mesh. No external model or library fetch is needed. Browser checks and limits are recorded in verification.json.
