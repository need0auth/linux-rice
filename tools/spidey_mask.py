"""Shared 24px Spider-Man mask for SVG icons and the Hyprlock PNG panel."""

SIZE = 24
MASK_PALETTE = {
    "mask_ink": "#122743",
    "mask_red": "#e52b3b",
    "mask_shadow": "#a9162f",
    "mask_highlight": "#ff4b4d",
    "mask_white": "#fff8e8",
}


def mask_pixels():
    # The stepped oval is taller than it is wide, ending in a short chin.
    bounds = (
        (9, 14), (6, 17), (5, 18), (4, 19), (3, 20), (3, 20),
        (3, 20), (3, 20), (3, 20), (3, 20), (3, 20), (3, 20),
        (3, 20), (3, 20), (3, 20), (3, 20), (4, 19), (4, 19),
        (5, 18), (6, 17), (8, 15), (10, 13),
    )
    silhouette = {(x, y) for y, (left, right) in enumerate(bounds, 1)
                  for x in range(left, right + 1)}
    pixels = {}
    for x, y in silhouette:
        edge = any((x + dx, y + dy) not in silhouette
                   for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        pixels[x, y] = "mask_ink" if edge else "mask_red"

    def marks(points, color):
        for x, y in points:
            if pixels.get((x, y)) not in (None, "mask_ink"):
                pixels[x, y] = color

    # Dark red webbing leaves the vivid red face and white lenses dominant.
    web = ((11, 3), (11, 4), (11, 5), (11, 6), (11, 7),
           (8, 4), (9, 5), (10, 6), (6, 6), (7, 7), (8, 7),
           (11, 16), (11, 17), (11, 18), (11, 19), (11, 20),
           (6, 16), (7, 17), (8, 18), (9, 19))
    marks(web, "mask_shadow")
    marks(((23 - x, y) for x, y in web), "mask_shadow")
    marks(((8, 3), (9, 3), (10, 3), (13, 3), (14, 3), (15, 3)), "mask_highlight")

    def polygon(points, color):
        for y in range(SIZE):
            for x in range(SIZE):
                inside, previous = False, points[-1]
                for point in points:
                    x0, y0 = previous
                    x1, y1 = point
                    if (y0 > y + .5) != (y1 > y + .5) and x + .5 < (x1 - x0) * (y + .5 - y0) / (y1 - y0) + x0:
                        inside = not inside
                    previous = point
                if inside and (x, y) in silhouette:
                    pixels[x, y] = color

    # Draw one lens, then mirror its pixels rather than rasterizing a second
    # polygon: both eyes remain exactly symmetric on the integer pixel grid.
    polygon(((4, 8), (8, 9), (10, 11), (11, 13), (10, 16), (8, 17), (5, 15), (4, 12)), "mask_ink")
    polygon(((5, 10), (7, 10), (9, 12), (9, 14), (8, 15), (6, 14), (5, 12)), "mask_white")
    for (x, y), color in tuple(pixels.items()):
        if x < SIZE // 2:
            pixels[SIZE - 1 - x, y] = color
    return pixels
