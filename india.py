"""
India Map (detailed) — Turtle map drawer with realistic outline and labeled points (Guwahati etc.)

Usage:
    python india_map_turtle.py

What it does:
 - Attempts to download a GeoJSON for India (several stable raw GitHub sources as fallbacks).
 - Parses polygons (MultiPolygon / Polygon).
 - Projects lat/lon to screen coordinates, rescales to fit canvas.
 - Densifies edges (inserts intermediate points) to produce thousands of drawing segments.
 - Draws coastline / outline with high detail, optional fill.
 - Marks major cities (Delhi, Mumbai, Kolkata, Chennai, Hyderabad, Guwahati, Bengaluru, etc.)
 - Keyboard:
    + / = : zoom in
    -     : zoom out
    Arrow keys : pan
    f     : toggle fill
    l     : toggle labels
    s     : save snapshot to india_map.ps
    q/Esc : quit
Notes:
 - If offline, place a GeoJSON file named 'india.geojson' next to script; the script will use it.
 - The script uses only Python standard library (urllib, json, turtle, math).
"""

import turtle
import urllib.request
import json
import math
import os
import sys
import time
from functools import lru_cache

# ----------------------
# Configuration
# ----------------------
SCREEN_W, SCREEN_H = 1400, 900
BG_COLOR = "#0a0a0a"
COASTLINE_COLOR = "#f2f2f2"
COASTLINE_PEN = 1.6
FILL_COLOR = "#0b3d91"   # subtle filled ocean/land contrast
LAND_COLOR = "#e6e0c8"   # optional fill for land
STATE_LINE_COLOR = "#b0a894"
CITY_COLOR = "#ffdd44"
CITY_LABEL_COLOR = "#ffffff"
DENSE_FACTOR = 6  # how many interpolated points to insert between each polygon vertex (higher => more segments)
MARGIN = 40       # px around map when scaling to screen
DEFAULT_ZOOM = 1.0

# City list (name, lat, lon, label_short)
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

# Fallback GeoJSON URLs (raw GitHub files that contain India polygon)
GEOJSON_URLS = [
    # Single-country GeoJSON for India
    "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/IND.geo.json",
    # Natural Earth derived list
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
    # A GeoJSON specifically for India (geohacker repo)
    "https://raw.githubusercontent.com/geohacker/india/master/state/india_states.geojson",
    # Another fallback - global countries (we'll search for India inside)
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
]

LOCAL_GEOJSON = "india.geojson"  # if placed locally, will be used without download

# ----------------------
# Utility functions
# ----------------------

def try_download_geojson():
    """
    Attempt to download a GeoJSON for India. If the returned file contains multiple countries,
    we will extract the India feature by ISO_A3 or 'India' name.
    """
    # If local file exists, prefer that (useful offline)
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
                # If single feature representing India directly, return it
                if is_india_feature(data):
                    print("Downloaded India GeoJSON (single feature).")
                    return data
                # If it is a FeatureCollection containing many countries/states, try to find India
                if data.get("type", "").lower() == "featurecollection":
                    india_feature = find_india_feature_in_collection(data)
                    if india_feature:
                        print("Extracted India feature from feature collection.")
                        return {"type": "FeatureCollection", "features": [india_feature]}
                    else:
                        # In some repos the file is states; if states exist, we can merge polygons for India
                        if any("state" in (feat.get("properties") or {}) for feat in data.get("features", [])):
                            print("GeoJSON appears to contain states — returning whole collection for parsing.")
                            return data
                # else maybe the file is a single Feature already (but not obviously India) - return as-is and attempt to parse
                print("Downloaded GeoJSON; will attempt to parse (may contain India).")
                return data
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
    # final fallback: if nothing downloaded, error out
    raise RuntimeError("Could not download GeoJSON and no local file found. Please provide 'india.geojson' in the script directory.")

def is_india_feature(obj):
    """Quick heuristic: single Feature with properties name 'India' or id 'IND'."""
    if not obj:
        return False
    if obj.get("type", "").lower() == "feature":
        props = obj.get("properties", {})
        if props.get("ADMIN") == "India" or props.get("NAME") == "India" or props.get("ISO_A3") == "IND":
            return True
    # some files use FeatureCollection with single feature
    if obj.get("type", "").lower() == "featurecollection" and len(obj.get("features", [])) == 1:
        props = obj["features"][0].get("properties", {})
        if props.get("ADMIN") == "India" or props.get("NAME") == "India" or props.get("ISO_A3") == "IND":
            return True
    return False

def find_india_feature_in_collection(collection):
    """Search a FeatureCollection for a feature referencing India via name or ISO code."""
    for feat in collection.get("features", []):
        props = feat.get("properties", {}) or {}
        name = (props.get("ADMIN") or props.get("NAME") or props.get("country") or props.get("name") or "").lower()
        iso = (props.get("ISO_A3") or props.get("iso_a3") or props.get("ISO3") or "").upper()
        if "india" in name or iso == "IND":
            return feat
    # attempt deeper check: maybe state-level geojson (like geohacker) — in that case we'll accept the full collection
    # but keep None so calling code can handle
    return None

# ----------------------
# GeoJSON parsing
# ----------------------

def extract_polygons_from_geojson(gj):
    """
    Return a list of polygons. Each polygon is a list of rings; each ring is a list of (lon, lat) points.
    We normalize to list of polygons where each polygon contains one or more linear rings (first is outer ring).
    """
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
                # coords is [ [ [lon,lat], ... ], [hole], ... ]
                polygons.append(coords)
            elif geom_type == "multipolygon":
                # coords is [ [ [ring], ... ], [ [ring], ... ], ... ]
                for p in coords:
                    polygons.append(p)
            # else ignore points/lines
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
        # Unknown shape; attempt to look for 'coordinates' key
        if "coordinates" in gj:
            coords = gj["coordinates"]
            # guess type: if nested 4 deep -> multipolygon
            if isinstance(coords, list) and coords and isinstance(coords[0][0][0], (list, tuple)):
                # multipolygon
                for p in coords:
                    polygons.append(p)
            else:
                # polygon
                polygons.append(coords)
    return polygons

# ----------------------
# Projection & scaling
# ----------------------

def lonlat_to_xy_equirectangular(lon, lat):
    """
    Simple equirectangular projection (lon, lat in degrees) -> (x,y) in projection units.
    This is fine for a country-scale map like India.
    """
    # we will keep lon increasing to the right and lat increasing up
    x = lon
    y = lat
    return x, y

def compute_bounds(polygons):
    """
    Given list of polygons (each polygon is list of rings of (lon,lat)), compute min/max lon/lat.
    """
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
    """
    Convert lon/lat polygons -> screen pixel coordinates (centered) using equirectangular projection.
    Returns list of polygons where each vertex is (x_px, y_px).
    Also returns a transform function lonlat -> screen coords for marking cities.
    """
    # First compute lon/lat bounds
    minlon, minlat, maxlon, maxlat = compute_bounds(polygons)
    # project bounds to raw x,y
    minx, miny = lonlat_to_xy_equirectangular(minlon, minlat)
    maxx, maxy = lonlat_to_xy_equirectangular(maxlon, maxlat)
    dx = maxx - minx
    dy = maxy - miny
    # determine scale to fit screen with margin
    available_w = screen_w - 2 * margin_px
    available_h = screen_h - 2 * margin_px
    if dx == 0 or dy == 0:
        scale = 1.0
    else:
        sx = available_w / dx
        sy = available_h / dy
        scale = min(sx, sy) * DEFAULT_ZOOM
    # we want to place center at screen center (0,0 for turtle)
    # compute offsets so that minx maps to left margin and miny maps to bottom margin (but centered)
    # We'll map to turtle coordinates where center is (0,0), y positive up.
    def lonlat_to_screen(lon, lat):
        x_raw, y_raw = lonlat_to_xy_equirectangular(lon, lat)
        # normalized position relative to center
        cx = (x_raw - (minx + maxx) / 2.0) * scale
        cy = (y_raw - (miny + maxy) / 2.0) * scale
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
# Densification (interpolation)
# ----------------------

def densify_ring(ring, factor=DENSE_FACTOR):
    """
    Given a ring: list of (x,y) points, insert 'factor' interpolated points between each adjacent pair
    (linear interpolation in lon/lat space is fine for small segments).
    """
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
    screen = turtle.Screen()
    screen.setup(width=width, height=height)
    screen.title("India — Detailed Map (turtle)")
    screen.bgcolor(bg)
    screen.tracer(0, 0)  # manual updates
    return screen

def draw_polygon_with_fill(t, polygon, pen_color=COASTLINE_COLOR, fill_color=None, pen_size=COASTLINE_PEN):
    """
    polygon: list of rings; ring: list of (x_px, y_px)
    draw outer ring then holes if any.
    """
    # Draw fill if requested (turtle fill works, but for complex polygons with holes it is tricky)
    # We'll implement a simple fill: stamp many horizontal lines between min/max x for each scanline.
    # But that's expensive; instead we'll use turtle.begin_fill for outer ring only (holes get ignored).
    outer = polygon[0]
    t.color(pen_color)
    t.pensize(pen_size)
    if fill_color:
        try:
            t.fillcolor(fill_color)
            t.begin_fill()
            t.penup()
            t.goto(outer[0])
            t.pendown()
            for x, y in outer[1:]:
                t.goto(x, y)
            t.goto(outer[0])
            t.end_fill()
        except Exception:
            # fallback to stroking only
            t.penup()
            t.goto(outer[0])
            t.pendown()
            for x, y in outer[1:]:
                t.goto(x, y)
    else:
        # just stroke the outer ring
        t.penup()
        t.goto(outer[0])
        t.pendown()
        for x, y in outer[1:]:
            t.goto(x, y)
    # draw holes as light strokes
    if len(polygon) > 1:
        t.pencolor(STATE_LINE_COLOR)
        for hole in polygon[1:]:
            t.penup()
            t.goto(hole[0])
            t.pendown()
            for x, y in hole[1:]:
                t.goto(x, y)

def stamp_city(t, lonlat_to_screen_func, lat, lon, color=CITY_COLOR, label=None):
    x, y = lonlat_to_screen_func(lon, lat)
    t.penup()
    t.goto(x, y)
    # draw a small circle marker using stamp
    marker = turtle.Turtle(visible=False)
    marker.hideturtle()
    marker.penup()
    marker.goto(x, y)
    marker.shape("circle")
    marker.shapesize(0.45, 0.45)
    marker.color(color)
    marker.showturtle()
    marker.stamp()
    marker.clear()
    marker.hideturtle()
    # label
    if label:
        labeler = turtle.Turtle(visible=False)
        labeler.hideturtle()
        labeler.penup()
        labeler.goto(x + 6, y + 6)
        labeler.color(CITY_LABEL_COLOR)
        labeler.write(label, font=("Arial", 11, "normal"))

# ----------------------
# Save snapshot (PostScript) helper
# ----------------------
def save_snapshot(screen, filename="india_map.ps"):
    try:
        canvas = screen.getcanvas()
        # PostScript coordinates: canvas.postscript writes in points; set pagewidth/pageheight to canvas size
        print("Saving snapshot to", filename)
        canvas.postscript(file=filename)
        print("Saved. You can convert .ps to .png with ImageMagick: convert india_map.ps india_map.png")
    except Exception as e:
        print("Failed to save snapshot:", e)

# ----------------------
# Main drawing routine
# ----------------------
def main():
    # 1) Download / load geojson
    try:
        gj = try_download_geojson()
    except RuntimeError as e:
        print("ERROR:", e)
        return

    # 2) extract polygons
    polygons = extract_polygons_from_geojson(gj)
    if not polygons:
        print("No polygons found in GeoJSON — exiting.")
        return

    # In many state-level GeoJSONs, each feature is one state polygon; if we received multiple features (many states),
    # merge them into a single list of polygons preserving rings. We'll treat each feature as a polygon.
    # polygons currently is list of polygon coords with rings as lon/lat pairs.

    # 3) densify in lon/lat space (interpolate)
    print("Densifying polygons with factor", DENSE_FACTOR, "— this will produce many segments (be patient)...")
    polygons_dense = densify_polygons(polygons, factor=DENSE_FACTOR)

    # 4) project and scale to screen coords
    print("Projecting and scaling polygons to screen coordinates...")
    proj_polys, lonlat_to_screen_func, scale_used = project_and_scale_polygons(polygons_dense, SCREEN_W, SCREEN_H)
    print("Scale used:", scale_used)

    # 5) setup turtle
    screen = setup_turtle_canvas(SCREEN_W, SCREEN_H, BG_COLOR)
    drawer = turtle.Turtle(visible=False)
    drawer.hideturtle()
    drawer.speed(0)
    drawer.penup()

    # controls state
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

    # helper for redrawing full scene (so keyboard can trigger it)
    def draw_scene():
        drawer.clear()
        # Clear low-level canvas completely to avoid overdraw artifacts
        try:
            screen.getcanvas().delete("all")
        except Exception:
            pass
        # draw each polygon (outer ring fill + stroke)
        drawer.pensize(COASTLINE_PEN)
        # Fill background (ocean) — create a rectangle background on canvas for crisp fill
        try:
            cvs = screen.getcanvas()
            # background rectangle, center at (0,0) in turtle coords -> canvas coords have inverted y
            w = SCREEN_W
            h = SCREEN_H
            cvs.create_rectangle(-w/2, -h/2, w/2, h/2, fill=BG_COLOR, outline=BG_COLOR)
        except Exception:
            pass

        # Draw filled land first (if enabled)
        if state["fill"]:
            # draw polygons filled (outer ring only) using turtle begin_fill (approx)
            drawer.color(COASTLINE_COLOR)
            for p in state["proj_polys"]:
                try:
                    # p is list of rings; use the outer ring for fill
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

        # Draw coastline / strokes
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
            # draw holes lightly if any
            for hole in p[1:]:
                drawer.penup()
                drawer.goto(hole[0])
                drawer.pendown()
                drawer.color(STATE_LINE_COLOR)
                for x, y in hole[1:]:
                    drawer.goto(x, y)
                drawer.color(COASTLINE_COLOR)

        # Mark cities
        for name, lat, lon, short in CITIES:
            # Convert using lonlat_to_screen (we built it earlier)
            sx, sy = state["lonlat_to_screen"](lon, lat)
            # draw a small circle using canvas for crispness
            try:
                cvs = screen.getcanvas()
                r = max(3, 4)
                cvs.create_oval(sx - r, - (sy - r), sx + r, - (sy + r), fill=CITY_COLOR, outline="")
                if state["labels"]:
                    cvs.create_text(sx + 12, -sy - 6, text=f"{name} ({short})", fill=CITY_LABEL_COLOR, anchor="w", font=("Arial", 11))
            except Exception:
                # fallback to turtle
                drawer.penup()
                drawer.goto(sx, sy)
                drawer.dot(6, CITY_COLOR)
                if state["labels"]:
                    drawer.goto(sx + 8, sy + 6)
                    drawer.color(CITY_LABEL_COLOR)
                    drawer.write(f"{name} ({short})", font=("Arial", 10, "normal"))
                    drawer.color(COASTLINE_COLOR)

        # Draw connecting lines to Guwahati (GHY) to emphasize point
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
                    # draw a thin dashed line using many small segments
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

        # HUD text
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

    # initial draw
    draw_scene()

    # ----------------------
    # Interaction callbacks
    # ----------------------
    def on_zoom_in():
        nonlocal state
        global DEFAULT_ZOOM
        DEFAULT_ZOOM *= 1.15
        # recompute projection at new zoom by re-projecting original lon/lat dense polygons
        # Reprojecting requires original lon/lat data; we can reconstruct from proj_polys / scale used: simpler approach: recompute full pipeline
        print("Zoom in requested — recomputing layout...")
        # Reverse engineer: we have 'polygons_dense' in lon/lat earlier; reproject with new DEFAULT_ZOOM
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

    # keyboard bindings
    screen.listen()
    screen.onkey(on_zoom_in, "+")
    screen.onkey(on_zoom_in, "=")
    screen.onkey(on_zoom_out, "-")
    screen.onkey(on_toggle_fill, "f")
    screen.onkey(on_toggle_labels, "l")
    screen.onkey(on_save_snapshot, "s")
    screen.onkey(on_quit, "q")
    screen.onkey(on_quit, "Escape")

    # arrow pan (adjusts by moving the projected polygons by an offset)
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

    # Keep window open
    turtle.mainloop()

if __name__ == "__main__":
    main()
