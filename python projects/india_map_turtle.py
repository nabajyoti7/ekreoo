"""
India Map (detailed) — Turtle map drawer with realistic outline and labeled points (Guwahati etc.)

Usage:
    python india_map_turtle.py

What it does:
 - Attempts to download a GeoJSON for India (several stable raw GitHub sources as fallbacks).
 - Parses polygons (MultiPolygon / Polygon).
 - Projects lat/lon to screen coordinates, rescales to fit canvas.
 - Densifies the polygon points (inserts interpolated points) so the turtle traces
   thousands of segments (very detailed outline).
 - Draws coastline / outline with smooth strokes, fills states/coastline in subtle colors,
   and marks major cities including Guwahati (GHY).
 - Provides keyboard controls: zoom, pan, toggle fill/labels, save image (PostScript).
 - Exports a .ps snapshot you can convert to PNG (optional instruction included).
 - All in standard library (no external packages required).
"""

import turtle
import urllib.request
import json
import math
import os
import sys
import time

# ----------------------
# Configuration
# ----------------------
SCREEN_W, SCREEN_H = 1400, 900
BG_COLOR = "#0a0a0a"
COASTLINE_COLOR = "#f2f2f2"
COASTLINE_PEN = 1.6
FILL_COLOR = "#0b3d91"
LAND_COLOR = "#e6e0c8"
STATE_LINE_COLOR = "#b0a894"
CITY_COLOR = "#ffdd44"
CITY_LABEL_COLOR = "#ffffff"
DENSE_FACTOR = 6
MARGIN = 40
DEFAULT_ZOOM = 1.0

CITIES = [
    ("New Delhi", 28.6139, 77.2090, "DEL"),
    ("Mumbai", 19.0760, 72.8777, "BOM"),
    ("Kolkata", 22.5726, 88.3639, "CCU"),
    ("Chennai", 13.0827, 80.2707, "MAA"),
    ("Bengaluru", 12.9716, 77.5946, "BLR"),
    ("Hyderabad", 17.3850, 78.4867, "HYD"),
    ("Guwahati", 26.1445, 91.7362, "GHY"),
    ("Ahmedabad", 23.0225, 72.5714, "AMD"),
    ("Pune", 18.5204, 73.8567, "PNQ"),
    ("Lucknow", 26.8467, 80.9462, "LKO"),
]

GEOJSON_URLS = [
    "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/IND.geo.json",
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
    "https://raw.githubusercontent.com/geohacker/india/master/state/india_states.geojson",
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
]

LOCAL_GEOJSON = "india.geojson"  # local fallback

# ----------------------
# Utility functions
# ----------------------

def try_download_geojson():
    if os.path.exists(LOCAL_GEOJSON):
        print("Using local GeoJSON:", LOCAL_GEOJSON)
        with open(LOCAL_GEOJSON, "r", encoding="utf-8") as f:
            return json.load(f)
    for url in GEOJSON_URLS:
        try:
            print(f"Trying to download GeoJSON from {url} ...")
            with urllib.request.urlopen(url, timeout=12) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if is_india_feature(data):
                    print("Downloaded India GeoJSON (single feature).")
                    return data
                if data.get("type", "").lower() == "featurecollection":
                    india_feature = find_india_feature_in_collection(data)
                    if india_feature:
                        print("Extracted India feature from feature collection.")
                        return {"type": "FeatureCollection", "features": [india_feature]}
                    if any("state" in (feat.get("properties") or {}) for feat in data.get("features", [])):
                        print("GeoJSON appears to contain states — returning whole collection for parsing.")
                        return data
                print("Downloaded GeoJSON; will attempt to parse (may contain India).")
                return data
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
    raise RuntimeError("Could not download GeoJSON and no local file found. Please provide 'india.geojson' in the script directory.")

def is_india_feature(obj):
    if not obj:
        return False
    if obj.get("type", "").lower() == "feature":
        props = obj.get("properties", {})
        if props.get("ADMIN") == "India" or props.get("NAME") == "India" or props.get("ISO_A3") == "IND":
            return True
    if obj.get("type", "").lower() == "featurecollection" and len(obj.get("features", [])) == 1:
        props = obj["features"][0].get("properties", {})
        if props.get("ADMIN") == "India" or props.get("NAME") == "India" or props.get("ISO_A3") == "IND":
            return True
    return False

def find_india_feature_in_collection(collection):
    for feat in collection.get("features", []):
        props = feat.get("properties", {}) or {}
        name = (props.get("ADMIN") or props.get("NAME") or props.get("country") or props.get("name") or "").lower()
        iso = (props.get("ISO_A3") or props.get("iso_a3") or props.get("ISO3") or "").upper()
        if "india" in name or iso == "IND":
            return feat
    return None

# ----------------------
# GeoJSON parsing
# ----------------------

def extract_polygons_from_geojson(gj):
    polygons = []
    gt = gj.get("type", "").lower()
    if gt == "featurecollection":
        for feat in gj.get("features", []):
            geom = feat.get("geometry") or feat.get("geom") or {}
            if not geom:
                continue
            geom_type = geom.get("type", "").lower()
            coords = geom.get("coordinates", [])
            if geom_type == "polygon":
                polygons.append(coords)
            elif geom_type == "multipolygon":
                for p in coords:
                    polygons.append(p)
    elif gt == "feature":
        geom = gj.get("geometry", {})
        geom_type = geom.get("type", "").lower()
        coords = geom.get("coordinates", [])
        if geom_type == "polygon":
            polygons.append(coords)
        elif geom_type == "multipolygon":
            for p in coords:
                polygons.append(p)
    elif gt == "multipolygon":
        for p in gj.get("coordinates", []):
            polygons.append(p)
    elif gt == "polygon":
        polygons.append(gj.get("coordinates", []))
    else:
        if "coordinates" in gj:
            coords = gj["coordinates"]
            if isinstance(coords, list) and coords and isinstance(coords[0][0][0], (list, tuple)):
                for p in coords:
                    polygons.append(p)
            else:
                polygons.append(coords)
    return polygons

# ----------------------
# Projection & scaling
# ----------------------

def lonlat_to_xy_equirectangular(lon, lat):
    x = lon
    y = lat
    return x, y

def compute_bounds(polygons):
    minlon = 1e9
    minlat = 1e9
    maxlon = -1e9
    maxlat = -1e9
    for poly in polygons:
        for ring in poly:
            for lon, lat in ring:
                minlon = min(minlon, lon)
                maxlon = max(maxlon, lon)
                minlat = min(minlat, lat)
                maxlat = max(maxlat, lat)
    return minlon, minlat, maxlon, maxlat

def project_and_scale_polygons(polygons, screen_w, screen_h, margin_px=MARGIN):
    minlon, minlat, maxlon, maxlat = compute_bounds(polygons)
    minx, miny = lonlat_to_xy_equirectangular(minlon, minlat)
    maxx, maxy = lonlat_to_xy_equirectangular(maxlon, maxlat)
    dx = maxx - minx
    dy = maxy - miny
    available_w = screen_w - 2 * margin_px
    available_h = screen_h - 2 * margin_px
    if dx == 0 or dy == 0:
        scale = 1.0
    else:
        sx = available_w / dx
        sy = available_h / dy
        scale = min(sx, sy) * DEFAULT_ZOOM
    def lonlat_to_screen(lon, lat):
        x_raw, y_raw = lonlat_to_xy_equirectangular(lon, lat)
        cx = (x_raw - (minx + maxx) / 2.0) * scale
        cy = (y_raw - (miny + maxlat) / 2.0) * scale
        return cx, cy
    projected = []
    for poly in polygons:
        proj_poly = []
        for ring in poly:
            proj_ring = []
            for lon, lat in ring:
                proj_ring.append(lonlat_to_screen(lon, lat))
            proj_poly.append(proj_ring)
        projected.append(proj_poly)
    return projected, lonlat_to_screen, scale

# ----------------------
# Densification
# ----------------------

def densify_ring(ring, factor=DENSE_FACTOR):
    if factor <= 1:
        return ring[:]
    dense = []
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        dense.append((x1, y1))
        for k in range(1, factor):
            t = k / float(factor)
            xi = x1 + (x2 - x1) * t
            yi = y1 + (y2 - y1) * t
            dense.append((xi, yi))
    return dense

def densify_polygons(polygons, factor=DENSE_FACTOR):
    dense_polys = []
    for poly in polygons:
        dense_poly = []
        for ring in poly:
            dense_poly.append(densify_ring(ring, factor=factor))
        dense_polys.append(dense_poly)
    return dense_polys

# ----------------------
# Turtle drawing helpers
# ----------------------

def setup_turtle_canvas(width=SCREEN_W, height=SCREEN_H, bg=BG_COLOR):
    scr = turtle.Screen()
    scr.setup(width=width, height=height)
    scr.title("India — Detailed Map (turtle)")
    scr.bgcolor(bg)
    scr.tracer(0, 0)
    return scr

def save_snapshot(screen, filename="india_map.ps"):
    try:
        canvas = screen.getcanvas()
        print("Saving snapshot to", filename)
        canvas.postscript(file=filename)
        print("Saved. You can convert .ps to .png with ImageMagick: convert india_map.ps india_map.png")
    except Exception as e:
        print("Failed to save snapshot:", e)

def main():
    try:
        gj = try_download_geojson()
    except RuntimeError as e:
        print("ERROR:", e)
        return
    polygons = extract_polygons_from_geojson(gj)
    if not polygons:
        print("No polygons found in GeoJSON — exiting.")
        return
    print("Densifying polygons with factor", DENSE_FACTOR, "— this will produce many segments (be patient)...")
    polygons_dense = densify_polygons(polygons, factor=DENSE_FACTOR)
    print("Projecting and scaling polygons to screen coordinates...")
    proj_polys, lonlat_to_screen_func, scale_used = project_and_scale_polygons(polygons_dense, SCREEN_W, SCREEN_H)
    print("Scale used:", scale_used)
    screen = setup_turtle_canvas(SCREEN_W, SCREEN_H, BG_COLOR)
    drawer = turtle.Turtle(visible=False)
    drawer.hideturtle()
    drawer.speed(0)
    drawer.penup()
    state = {
        "fill": True,
        "labels": True,
        "zoom": DEFAULT_ZOOM,
        "offset_x": 0,
        "offset_y": 0,
        "screen": screen,
        "drawer": drawer,
        "proj_polys": proj_polys,
        "lonlat_to_screen": lonlat_to_screen_func,
    }
    def draw_scene():
        drawer.clear()
        try:
            screen.getcanvas().delete("all")
        except Exception:
            pass
        drawer.pensize(COASTLINE_PEN)
        try:
            cvs = screen.getcanvas()
            w = SCREEN_W
            h = SCREEN_H
            cvs.create_rectangle(-w/2, -h/2, w/2, h/2, fill=BG_COLOR, outline=BG_COLOR)
        except Exception:
            pass
        if state["fill"]:
            drawer.color(COASTLINE_COLOR)
            for p in state["proj_polys"]:
                try:
                    outer = p[0]
                    if not outer:
                        continue
                    drawer.penup()
                    drawer.goto(outer[0])
                    drawer.pendown()
                    drawer.fillcolor(LAND_COLOR)
                    drawer.begin_fill()
                    for x, y in outer:
                        drawer.goto(x, y)
                    drawer.goto(outer[0])
                    drawer.end_fill()
                except Exception:
                    continue
        drawer.color(COASTLINE_COLOR)
        drawer.pensize(COASTLINE_PEN)
        for p in state["proj_polys"]:
            outer = p[0]
            if not outer:
                continue
            drawer.penup()
            drawer.goto(outer[0])
            drawer.pendown()
            for (x, y) in outer[1:]:
                drawer.goto(x, y)
            for hole in p[1:]:
                drawer.penup()
                drawer.goto(hole[0])
                drawer.pendown()
                drawer.color(STATE_LINE_COLOR)
                for x, y in hole[1:]:
                    drawer.goto(x, y)
                drawer.color(COASTLINE_COLOR)
        for name, lat, lon, short in CITIES:
            sx, sy = state["lonlat_to_screen"](lon, lat)
            try:
                cvs = screen.getcanvas()
                r = max(3, 4)
                cvs.create_oval(sx - r, - (sy - r), sx + r, - (sy + r), fill=CITY_COLOR, outline="")
                if state["labels"]:
                    cvs.create_text(sx + 12, -sy - 6, text=f"{name} ({short})", fill=CITY_LABEL_COLOR, anchor="w", font=("Arial", 11))
            except Exception:
                drawer.penup()
                drawer.goto(sx, sy)
                drawer.dot(6, CITY_COLOR)
                if state["labels"]:
                    drawer.goto(sx + 8, sy + 6)
                    drawer.color(CITY_LABEL_COLOR)
                    drawer.write(f"{name} ({short})", font=("Arial", 10, "normal"))
                    drawer.color(COASTLINE_COLOR)
        try:
            gh_lat, gh_lon = None, None
            for nm, lat, lon, short in CITIES:
                if short == "GHY" or "Guwahati".lower() in nm.lower():
                    gh_lat, gh_lon = lat, lon
                    break
            if gh_lat is not None:
                ghx, ghy = state["lonlat_to_screen"](gh_lon, gh_lat)
                for nm, lat, lon, short in CITIES:
                    if short == "GHY":
                        continue
                    sx, sy = state["lonlat_to_screen"](lon, lat)
                    dx = (ghx - sx)
                    dy = (ghy - sy)
                    steps = 60
                    for i in range(steps):
                        x1 = sx + dx * (i / steps)
                        y1 = sy + dy * (i / steps)
                        x2 = sx + dx * ((i + 1) / steps)
                        y2 = sy + dy * ((i + 1) / steps)
                        if i % 2 == 0:
                            cvs.create_line(x1, -y1, x2, -y2, fill="#ffcc66", width=1)
        except Exception:
            pass
        try:
            cvs.create_text(-SCREEN_W/2 + 120, -SCREEN_H/2 + 20, text="India — Detailed Map (press s to save snapshot)", fill="#cccccc", anchor="w", font=("Arial", 10))
        except Exception:
            drawer.penup()
            drawer.goto(-SCREEN_W/2 + 20, -SCREEN_H/2 + 20)
            drawer.color("#cccccc")
            drawer.write("India — Detailed Map (press s to save snapshot)", font=("Arial", 10, "normal"))
            drawer.color(COASTLINE_COLOR)
        screen.update()
        print("Scene drawn.")
    draw_scene()
    def on_zoom_in():
        nonlocal state
        global DEFAULT_ZOOM
        DEFAULT_ZOOM *= 1.15
        print("Zoom in requested — recomputing layout...")
        proj_polys_new, lonlat_to_screen_new, scale_new = project_and_scale_polygons(polygons_dense, SCREEN_W, SCREEN_H)
        state["proj_polys"] = proj_polys_new
        state["lonlat_to_screen"] = lonlat_to_screen_new
        draw_scene()
    def on_zoom_out():
        nonlocal state
        global DEFAULT_ZOOM
        DEFAULT_ZOOM /= 1.15
        print("Zoom out requested — recomputing layout...")
        proj_polys_new, lonlat_to_screen_new, scale_new = project_and_scale_polygons(polygons_dense, SCREEN_W, SCREEN_H)
        state["proj_polys"] = proj_polys_new
        state["lonlat_to_screen"] = lonlat_to_screen_new
        draw_scene()
    def on_toggle_fill():
        state["fill"] = not state["fill"]
        print("Fill toggled:", state["fill"])
        draw_scene()
    def on_toggle_labels():
        state["labels"] = not state["labels"]
        print("Labels toggled:", state["labels"])
        draw_scene()
    def on_save_snapshot():
        fname = f"india_map_{int(time.time())}.ps"
        save_snapshot(screen, fname)
    def on_quit():
        print("Quitting...")
        turtle.bye()
        sys.exit(0)
    screen.listen()
    screen.onkey(on_zoom_in, "+")
    screen.onkey(on_zoom_in, "=")
    screen.onkey(on_zoom_out, "-")
    screen.onkey(on_toggle_fill, "f")
    screen.onkey(on_toggle_labels, "l")
    screen.onkey(on_save_snapshot, "s")
    screen.onkey(on_quit, "q")
    screen.onkey(on_quit, "Escape")
    PAN_STEP = 20
    def pan_left():
        for i, p in enumerate(state["proj_polys"]):
            newpoly = []
            for ring in p:
                newring = [(x + PAN_STEP, y) for x, y in ring]
                newpoly.append(newring)
            state["proj_polys"][i] = newpoly
        draw_scene()
    def pan_right():
        for i, p in enumerate(state["proj_polys"]):
            newpoly = []
            for ring in p:
                newring = [(x - PAN_STEP, y) for x, y in ring]
                newpoly.append(newring)
            state["proj_polys"][i] = newpoly
        draw_scene()
    def pan_up():
        for i, p in enumerate(state["proj_polys"]):
            newpoly = []
            for ring in p:
                newring = [(x, y - PAN_STEP) for x, y in ring]
                newpoly.append(newring)
            state["proj_polys"][i] = newpoly
        draw_scene()
    def pan_down():
        for i, p in enumerate(state["proj_polys"]):
            newpoly = []
            for ring in p:
                newring = [(x, y + PAN_STEP) for x, y in ring]
                newpoly.append(newring)
            state["proj_polys"][i] = newpoly
        draw_scene()
    screen.onkey(pan_left, "Left")
    screen.onkey(pan_right, "Right")
    screen.onkey(pan_up, "Up")
    screen.onkey(pan_down, "Down")
    turtle.mainloop()

if __name__ == "__main__":
    main()
