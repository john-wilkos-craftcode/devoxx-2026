# Third-party material

## Venue model: Ghost Light

`venue.json` is generated from `src/venue/kinepolis.ts` in
[LoMagnette/ghost-light](https://github.com/LoMagnette/ghost-light), an entry in the Devoxx Robot
Games 2026.

MIT License

Copyright (c) 2026 Loïc Magnette

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Look and feel

Materials, colours and signage follow the photo-checked notes in
[Smirne/devoxx-gauntlet-m](https://github.com/Smirne/devoxx-gauntlet-m) by Michele Giacobazzi
(MIT) and reference photos of the venue. No photos are shipped.

## Renders: textures, models and type

The cinema page's stills and walks (`site/cinema/media/`) are rendered in Blender by `scripts/blender/build_scene.py`
from the venue model above. Nothing below is shipped as a file; it only appears in the rendered images.

- Textures from [ambientCG](https://ambientcg.com) (Carpet016) and [Poly Haven](https://polyhaven.com) (terlenka),
  CC0, fetched by `scripts/fetch_textures.py`.
- Potted plants from Poly Haven: `pachira_aquatica_01` and `calathea_orbifolia_01`, CC0, fetched by
  `scripts/fetch_models.py`.
- People: the [Microsoft Rocketbox](https://github.com/microsoft/Microsoft-Rocketbox) avatars and their motion
  capture, MIT licence.
- Backpacks: "Oakley Kitchen Sink Backpack Model" by
  [qkuslic1](https://sketchfab.com/3d-models/oakley-kitchen-sink-backpack-model-c2440ae21b14485095ba3da4d947f1ee),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), modified (simplified, refitted to a wearer, recoloured).
- Type: Archivo Black and Big Shoulders Display, SIL Open Font License 1.1 (`scripts/blender/fonts/`, licences
  beside them).
