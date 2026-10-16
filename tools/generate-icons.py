#!/usr/bin/env python3
"""Build the tracker theme's illustrated 24 × 24 pixel sprites.

Only Python's standard library is used. All drawing happens on an integer
pixel canvas, so the resulting SVGs remain sharp at any integer scale.
Run from any directory; generated SVGs are written to quickshell/assets/icons.
"""
from collections import defaultdict
from pathlib import Path

SIZE = 24
PALETTE = {
    "ink": "#122743", "coral": "#ff958d", "red": "#ed6e72",
    "peach": "#ffd39a", "paper": "#fff0cc", "mint": "#78ecb6",
    "green": "#34cf8b", "cyan": "#49c7f4", "ice": "#8ceaff",
    "blue": "#348cd5", "purple": "#7888dc", "gray": "#a9becb",
}


class Sprite:
    def __init__(self):
        self.pixels = {}

    def rect(self, x, y, w, h, color):
        for py in range(y, y + h):
            for px in range(x, x + w):
                if 0 <= px < SIZE and 0 <= py < SIZE:
                    self.pixels[px, py] = color
        return self

    def poly(self, points, color):
        # Rasterize polygon edges at pixel centers. No vector anti-aliasing.
        for py in range(SIZE):
            for px in range(SIZE):
                x, y = px + .5, py + .5
                inside = False
                j = len(points) - 1
                for i, (xi, yi) in enumerate(points):
                    xj, yj = points[j]
                    if (yi > y) != (yj > y) and x < (xj-xi) * (y-yi) / (yj-yi) + xi:
                        inside = not inside
                    j = i
                if inside:
                    self.pixels[px, py] = color
        return self

    def octagon(self, x, y, w, h, corner, color):
        return self.poly([(x+corner,y), (x+w-corner,y), (x+w,y+corner),
                          (x+w,y+h-corner), (x+w-corner,y+h),
                          (x+corner,y+h), (x,y+h-corner), (x,y+corner)], color)

    def svg(self, name):
        paths = defaultdict(list)
        # Merge horizontal runs, keeping every coordinate on the 24px grid.
        for y in range(SIZE):
            x = 0
            while x < SIZE:
                color = self.pixels.get((x, y))
                end = x + 1
                while end < SIZE and self.pixels.get((end, y)) == color:
                    end += 1
                if color:
                    paths[color].append(f"M{x} {y}h{end-x}v1H{x}z")
                x = end
        body = "".join(f'<path fill="{PALETTE[color]}" d="{"".join(runs)}"/>'
                       for color, runs in paths.items())
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                f'width="24" height="24" shape-rendering="crispEdges" '
                f'role="img" aria-label="{name.replace("-", " ")}">'
                f'{body}</svg>\n')


SPIDER_ROWS = (
    "....##....##....",
    "....##.##.##....",
    ".##.##.##.##.##.",
    ".##..######..##.",
    ".###.######.###.",
    "..############..",
    "....########....",
    "....########....",
    "..############..",
    ".###.######.###.",
    ".##..######..##.",
    ".##.########.##.",
    "....##.##.##....",
    "....##....##....",
)


def spider_emblem(s):
    """The reference badge's squat body and eight short, thick stepped legs.

    Keep the silhouette on a fixed integer grid so every badge uses the same
    compact shape and the notches between its legs survive at small sizes.
    """
    for y, row in enumerate(SPIDER_ROWS, start=5):
        for x, pixel in enumerate(row, start=4):
            if pixel == "#":
                s.rect(x, y, 1, 1, "ink")


def plate(base="peach", shade="red"):
    s = Sprite()
    s.rect(4,3,18,20,"ink").rect(2,1,18,20,"ink")
    s.rect(3,2,16,18,base).rect(3,18,16,2,shade)
    s.rect(4,3,13,1,"paper").rect(3,4,1,12,"paper")
    return s


def marker(base):
    s = Sprite().octagon(1,2,22,22,6,"ink")
    s.octagon(2,2,20,20,5,base).rect(7,3,7,1,"paper")
    spider_emblem(s)
    return s


def create_icons():
    icons = {}
    s = Sprite().rect(2,1,22,23,"ink").rect(1,0,22,23,"ink")
    s.rect(2,1,20,21,"peach").rect(2,20,20,2,"red")
    s.rect(3,1,17,1,"paper").rect(2,2,1,16,"paper")
    spider_emblem(s); icons["spider"] = s

    s = Sprite().octagon(1,1,22,22,6,"ink")
    s.octagon(3,2,18,19,5,"coral")
    s.poly([(3,14),(7,18),(17,18),(21,14),(21,18),(18,21),(6,21),(3,18)],"red")
    # Sparse web lines keep the friendly cream eyes legible at bar size.
    s.rect(11,2,2,7,"red").rect(11,17,2,4,"red")
    s.rect(5,5,3,1,"red").rect(16,5,3,1,"red")
    s.poly([(4,8),(10,10),(11,15),(8,17),(4,14)],"ink")
    s.poly([(20,8),(14,10),(13,15),(16,17),(20,14)],"ink")
    s.poly([(5,10),(9,11),(9,14),(7,15),(5,13)],"paper")
    s.poly([(19,10),(15,11),(15,14),(17,15),(19,13)],"paper")
    s.rect(8,3,3,1,"paper")
    icons["mask"] = s

    for name, color in (("spider-mint","mint"),("spider-coral","coral"),("spider-gray","gray")):
        icons[name] = marker(color)

    s = Sprite().octagon(1,1,22,22,6,"ink")
    s.octagon(3,3,18,18,5,"blue").octagon(5,5,14,14,4,"cyan")
    s.octagon(7,7,10,10,3,"blue")
    s.rect(11,3,1,18,"ice").rect(3,11,18,1,"ice")
    s.poly([(12,12),(12,4),(18,6),(21,11)],"green")
    s.rect(10,10,3,3,"paper").rect(16,7,2,2,"mint")
    s.rect(6,15,2,2,"mint"); icons["radar"] = s

    s = Sprite().rect(2,3,20,18,"ink")
    s.rect(3,4,18,15,"coral").rect(3,17,18,2,"red")
    s.rect(5,7,14,9,"ink").rect(6,8,12,7,"mint")
    s.rect(4,5,2,1,"paper").rect(8,5,2,1,"peach")
    s.poly([(8,9),(10,11),(10,12),(8,14),(7,13),(9,11),(7,10)],"ink")
    s.rect(12,13,4,1,"ink"); icons["terminal"] = s

    s = Sprite().octagon(1,1,22,22,6,"ink")
    s.octagon(3,3,18,18,5,"purple")
    s.rect(4,8,16,1,"ink").rect(3,14,18,1,"ink")
    s.poly([(10,3),(8,7),(7,15),(10,21),(8,21),(5,15),(6,7),(8,3)],"ink")
    s.poly([(14,3),(16,7),(17,15),(14,21),(16,21),(19,15),(18,7),(16,3)],"ink")
    s.rect(10,4,3,3,"ice").rect(8,9,7,4,"cyan").rect(10,15,3,4,"blue")
    s.rect(4,10,2,2,"ice"); icons["browser"] = s

    s = Sprite().poly([(1,5),(9,5),(11,8),(22,8),(22,21),(1,21)],"ink")
    s.poly([(3,6),(8,6),(10,9),(20,9),(20,19),(3,19)],"red")
    s.rect(2,10,21,11,"ink").rect(3,11,19,8,"peach")
    s.rect(4,12,16,1,"paper").rect(4,17,15,2,"coral")
    s.rect(16,14,3,2,"paper"); icons["files"] = s

    s = Sprite()
    for x,y,color in ((2,2,"coral"),(13,2,"peach"),(2,13,"cyan"),(13,13,"mint")):
        s.rect(x,y,9,9,"ink").rect(x+1,y+1,7,6,color)
        s.rect(x+2,y+2,4,1,"paper")
    icons["grid"] = s

    s = Sprite()
    for p in (5,9,13,17):
        s.rect(p,1,2,22,"ink").rect(1,p,22,2,"ink")
    s.rect(4,4,16,16,"ink").rect(6,6,12,12,"coral")
    s.rect(8,8,8,8,"ink").rect(9,9,6,6,"mint")
    s.rect(10,10,2,2,"paper").rect(6,16,12,2,"red")
    icons["cpu"] = s

    for muted in (False, True):
        s = Sprite().poly([(2,8),(7,8),(13,3),(15,3),(15,21),(13,21),(7,16),(2,16)],"ink")
        s.poly([(4,10),(8,10),(13,6),(13,18),(8,14),(4,14)],"peach")
        s.rect(4,13,3,1,"coral").rect(11,9,2,7,"coral")
        if muted:
            s.poly([(17,7),(19,9),(21,7),(23,9),(21,11),(23,13),(21,15),(19,13),(17,15),(15,13),(17,11),(15,9)],"ink")
            s.rect(18,10,2,2,"red")
        else:
            s.rect(17,8,2,8,"ink").rect(20,5,2,14,"ink")
            s.rect(17,9,1,6,"mint").rect(20,7,1,10,"mint")
        icons["muted" if muted else "volume"] = s

    for offline in (False, True):
        s = Sprite()
        for x,y,w,h in ((6,3,12,2),(3,5,3,2),(18,5,3,2),(1,7,2,2),
                        (21,7,2,2),(7,8,10,2),(5,10,2,2),(17,10,2,2),
                        (9,13,6,2),(7,15,2,2),(15,15,2,2)):
            s.rect(x,y,w,h,"ink")
            s.rect(x,y,w,1,"gray" if offline else "cyan")
        s.rect(10,18,4,4,"ink").rect(11,18,2,2,"coral" if offline else "mint")
        if offline:
            s.poly([(4,2),(22,20),(20,22),(2,4)],"ink")
            s.poly([(4,3),(21,20),(20,21),(3,4)],"coral")
        icons["offline" if offline else "wifi"] = s

    s = Sprite().rect(8,1,8,3,"ink").rect(5,3,14,20,"ink")
    s.rect(6,4,12,17,"cyan").rect(8,6,8,13,"ink")
    for y in (7,11,15): s.rect(9,y,6,3,"mint")
    s.rect(6,4,1,16,"ice").rect(7,21,10,1,"blue")
    icons["battery"] = s

    s = Sprite().rect(6,1,3,7,"ink").rect(15,1,3,7,"ink")
    s.rect(7,2,1,5,"paper").rect(16,2,1,5,"paper")
    s.poly([(3,6),(21,6),(21,13),(17,17),(14,17),(14,22),(10,22),(10,17),(7,17),(3,13)],"ink")
    s.poly([(5,8),(19,8),(19,12),(15,15),(9,15),(5,12)],"peach")
    s.rect(6,9,12,2,"paper").rect(11,17,2,4,"mint")
    icons["plug"] = s

    s = Sprite()
    for x,y,w,h in ((11,0,2,4),(11,20,2,4),(0,11,4,2),(20,11,4,2),
                    (3,3,3,3),(18,3,3,3),(3,18,3,3),(18,18,3,3)):
        s.rect(x,y,w,h,"ink")
    s.octagon(5,5,14,14,4,"ink").octagon(7,7,10,10,3,"peach")
    s.rect(9,8,5,2,"paper").rect(9,15,6,2,"coral")
    icons["brightness"] = s

    for name in ("play","pause","next","previous"):
        s = Sprite().octagon(1,2,22,21,3,"ink")
        s.octagon(2,2,20,18,2,"mint").rect(4,3,15,1,"paper")
        s.rect(4,19,16,2,"green")
        if name == "play":
            s.poly([(9,5),(18,11),(9,17)],"ink")
            s.rect(10,8,1,5,"paper")
        elif name == "pause":
            s.rect(7,6,4,11,"ink").rect(14,6,4,11,"ink")
            s.rect(8,7,1,8,"paper").rect(15,7,1,8,"paper")
        elif name == "next":
            s.poly([(6,5),(15,11),(6,17)],"ink").rect(16,5,3,12,"ink")
        else:
            s.poly([(18,5),(9,11),(18,17)],"ink").rect(5,5,3,12,"ink")
        icons[name] = s

    s = Sprite().octagon(6,1,12,15,4,"ink")
    s.octagon(8,3,8,11,2,"ice").rect(10,5,4,7,"ink")
    s.rect(3,10,18,13,"ink").rect(5,11,14,10,"peach")
    s.rect(5,19,14,2,"coral").rect(6,12,11,1,"paper")
    s.rect(10,14,4,3,"ink").rect(11,17,2,2,"ink")
    icons["lock"] = s

    s = Sprite().poly([(2,7),(7,7),(9,3),(15,3),(17,7),(22,7),(22,21),(2,21)],"ink")
    s.poly([(4,8),(8,8),(10,5),(14,5),(16,8),(20,8),(20,19),(4,19)],"coral")
    s.rect(5,10,3,2,"peach").octagon(9,9,10,10,3,"ink")
    s.octagon(11,11,6,6,2,"cyan").rect(12,11,2,2,"paper")
    s.rect(4,18,5,1,"red"); icons["screenshot"] = s

    for name, base in (("close","coral"),("minus","peach"),("plus","mint")):
        s = plate(base, "green" if name == "plus" else "red")
        if name == "close":
            s.poly([(6,6),(8,6),(11,9),(14,6),(16,6),(16,8),(13,11),(16,14),(16,16),(14,16),(11,13),(8,16),(6,16),(6,14),(9,11),(6,8)],"ink")
        else:
            s.rect(6,10,10,3,"ink")
            if name == "plus": s.rect(10,6,3,11,"ink")
        icons[name] = s

    s = Sprite().poly([(9,1),(15,1),(15,4),(18,5),(21,4),(24,9),(21,11),
                       (21,14),(24,16),(21,21),(18,20),(15,21),(15,24),
                       (9,24),(9,21),(6,20),(3,21),(0,16),(3,14),
                       (3,11),(0,9),(3,4),(6,5),(9,4)],"ink")
    s.octagon(4,4,16,16,4,"purple")
    s.rect(10,2,4,4,"purple").rect(10,19,4,3,"purple")
    s.octagon(7,7,10,10,3,"ink").octagon(9,9,6,6,2,"cyan")
    s.rect(10,9,3,2,"paper"); icons["settings"] = s

    s = Sprite().octagon(3,3,18,18,5,"ink")
    s.octagon(5,5,14,14,4,"cyan").octagon(7,7,10,10,3,"ink")
    s.octagon(8,8,8,8,2,"ice")
    s.rect(10,0,4,7,"ink").rect(10,17,4,7,"ink")
    s.rect(0,10,7,4,"ink").rect(17,10,7,4,"ink")
    s.rect(11,1,2,5,"mint").rect(11,18,2,5,"mint")
    s.rect(1,11,5,2,"mint").rect(18,11,5,2,"mint")
    s.rect(11,11,2,2,"red"); icons["crosshair"] = s
    return icons


def main():
    target = Path(__file__).resolve().parents[1] / "quickshell/assets/icons"
    target.mkdir(parents=True, exist_ok=True)
    icons = create_icons()
    for name, sprite in sorted(icons.items()):
        (target / f"{name}.svg").write_text(sprite.svg(name), encoding="utf-8")
    print(f"Generated {len(icons)} illustrated pixel sprites in {target}")


if __name__ == "__main__":
    main()
