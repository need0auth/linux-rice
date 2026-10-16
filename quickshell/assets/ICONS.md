# Tracker pixel sprites

These original, hand-drawn sprites use a 24 × 24 integer grid and a shared
pastel palette. They are illustrated UI stickers: navy outlines, coral masks,
peach device buttons, mint markers, and cyan instruments. They do not depend
on an icon font or an external theme.

Use `icons/<name>.svg` at 24, 48, or 72 logical pixels when possible. Keep
image smoothing disabled in QML so the stepped silhouettes stay crisp.
`spider-mint`, `spider-coral`, and `spider-gray` are map markers;
`spider` is the peach spider badge and `mask` is the coral face sticker.

The four spider badges share a mirrored chest-emblem silhouette: a distinct
small head, a one-pixel thorax, a long pointed abdomen, and eight angular
legs. Open space between the leg pairs keeps the emblem legible in the top
bar and on the map. The sprites remain sharp at small sizes; the review
sheet at [`docs/spider-icons.png`](../../docs/spider-icons.png) includes actual
20, 24, 32, and 40 pixel samples as well as enlarged grid previews.

Rebuild from the repository root:

```sh
python3 tools/generate-icons.py
```

The generator needs only Python's standard library. It writes only this
theme's `assets/icons/` directory; it does not require an image library.
