"""
Realistic-ish Solar System Simulator (Turtle)
- Run: python solar_simulator.py
- Controls:
    Space       : Pause / Resume
    + / =       : Speed up simulation time
    - / _       : Slow down simulation time
    o           : Toggle orbit lines
    l           : Toggle labels
    t           : Toggle trails
    r           : Reset view (center + default zoom)
    z           : Zoom in
    x           : Zoom out
    Arrow keys  : Pan view (Left/Right/Up/Down)
    Click planet/moon : Show info panel (auto-hide)
    q or Esc    : Quit
Notes:
- The simulator compresses distances and periods so outer planets are visible and move.
- You can adjust SCALE and TIME_SCALE near the config section for different effects.
"""

import turtle
import math
import random
import time
import sys

# -------------------------
# CONFIGURATION
# -------------------------
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
BACKGROUND = "black"

# Visual scaling: convert astronomical units to pixels (compressed)
AU_TO_PIXELS = 200.0  # base scale (will be adjusted by global zoom)
GLOBAL_SCALE = 1.0    # user-changeable zoom factor

# Time scaling: how many simulation days advance per real second
# Larger -> faster orbits. We'll start with a moderate compression to see outer planets move.
TIME_SCALE = 120.0  # simulation days per real second (user can speed up further)
paused = False

# Trail & visual options
SHOW_ORBITS = True
SHOW_LABELS = True
SHOW_TRAILS = True
USE_SHADING = True  # simulate day/night shading

# Trail length
MAX_TRAIL_POINTS = 120

# Colors for the Sun and background
SUN_COLOR = "#ffd54f"
BG_COLOR = BACKGROUND

# Info display time (ms)
INFO_DISPLAY_MS = 4500

# -------------------------
# PHYSICAL / ORBITAL DATA
# Values are simplified approximations suitable for visualization.
# We'll use: name, semi-major axis (AU), eccentricity, inclination (deg),
# orbital_period (days), radius_km (for relative size), color, axial_tilt (deg), rotation_period_hours
# -------------------------
# Radius is used relatively (we will scale and clamp for visibility)
PLANET_RAW = [
    # name, a, e, inc, period_days, radius_km, color, axial_tilt_deg, rot_hours
    ("Mercury", 0.387, 0.205, 7.0,   87.969, 2439.7, "#9e9e9e", 0.01, 1407.6),
    ("Venus",   0.723, 0.0067, 3.4, 224.701, 6051.8, "#ffcc80", 177.4, -5832.5),
    ("Earth",   1.000, 0.0167, 0.0, 365.256, 6371.0,  "#5ea6ff", 23.44, 24.0),
    ("Mars",    1.524, 0.0934, 1.85,686.980, 3389.5,  "#ff7043", 25.19, 24.6),
    ("Jupiter", 5.203, 0.0484, 1.3,  4332.589,69911.0, "#d6a86b", 3.13, 9.9),
    ("Saturn",  9.537, 0.0541, 2.49,10759.22,58232.0, "#f6e27a", 26.73, 10.7),
    ("Uranus", 19.191, 0.0472, 0.77,30685.4,25362.0, "#ace7ff", 97.77, -17.2),
    ("Neptune",30.07,  0.0086, 1.77,60190.0,24622.0, "#4a6bff", 28.32, 16.1),
    ("Pluto",  39.48,  0.2488,17.16,90560.0,1188.3,  "#ffffff", 119.6, -153.3),
]

# Moons: parent_name, name, semi_major_km (approx from parent), orbital_period_days, radius_km, color, eccentricity, inclination_deg
# Distances given in thousands of km to be scaled later relative to planet distance
MOONS_RAW = [
    ("Earth", "Moon", 384.4, 27.32, 1737.1, "#e6e6e6", 0.0549, 5.145),
    # Jupiter - Galilean (Io, Europa, Ganymede, Callisto)
    ("Jupiter", "Io",     421.8, 1.769, 1821.6, "#ffd59a", 0.0041, 0.04),
    ("Jupiter", "Europa", 671.1, 3.551, 1560.8, "#d8f2ff", 0.009, 0.47),
    ("Jupiter", "Ganymede",1070.4,7.155,2634.1,"#c7b299",0.0013,0.20),
    ("Jupiter", "Callisto",1882.7,16.689,2410.3,"#8f7a66",0.007,0.19),
    # Saturn - Titan
    ("Saturn", "Titan", 1221.8,15.945,2574.7,"#e0cdaa",0.0288,0.33),
    # A couple of Mars's tiny moons (Phobos/Deimos scaled down)
    ("Mars", "Phobos", 9.378, 0.3189,11.2667,"#c2b7a3",0.0151,1.093),
    ("Mars", "Deimos", 23.463, 1.262,6.2,"#d9d0c6",0.0002,0.93),
]

# Rings parameters: parent, inner_km, outer_km, thickness_km, color
RINGS_RAW = [
    ("Saturn", 70000, 140000, 5000, "#d9c88a"),
    ("Uranus", 38000, 51000, 3000, "#cfe7f2"),
    ("Neptune", 24000, 63000, 2000, "#c9e0ff"),
]

# -------------------------
# UTILS & SCALE CALCULATIONS
# -------------------------
def clamp(v, a, b):
    return max(a, min(b, v))

# Convert planet radii (km) into pixels using a non-linear scaling to show differences but keep visibility
def radius_km_to_pixels(radius_km):
    # Non-linear scale: pixels = a * log(radius_km) + b
    a = 2.8
    b = 1.5
    px = a * math.log(max(1.0, radius_km)) + b
    return clamp(px, 3.0, 60.0)

# Convert moon orbital distances (thousand km) to pixels around their parent (scaled relative to parent visual size)
def moon_dist_to_pixels(dist_thousand_km, parent_radius_px):
    # use parent_radius_px as reference: place moon orbits a bit away from parent radius
    base = parent_radius_px * 2.5
    return base + dist_thousand_km * 0.02  # empirical factor

# Convert AU to pixel using AU_TO_PIXELS and GLOBAL_SCALE
def au_to_px(au):
    return au * AU_TO_PIXELS * GLOBAL_SCALE

# Convert a rotation angle (deg) to radians helper
def d2r(deg):
    return math.radians(deg)

# -------------------------
# TURTLE SETUP
# -------------------------
screen = turtle.Screen()
screen.setup(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
screen.title("Realistic-ish Solar System Simulator")
screen.bgcolor(BG_COLOR)
screen.tracer(0, 0)  # manual updates

# Root canvas offset for pan/zoom (we will transform world coords before drawing)
view_offset_x = 0
view_offset_y = 0
DEFAULT_VIEW = (0, 0, 1.0)  # offset_x, offset_y, GLOBAL_SCALE
GLOBAL_SCALE = 1.0

# Central sun drawing turtle (static)
sun_turtle = turtle.Turtle(visible=False)
sun_turtle.hideturtle()
sun_turtle.penup()

# Drawer for static orbit lines
orbit_drawer = turtle.Turtle(visible=False)
orbit_drawer.hideturtle()
orbit_drawer.penup()
orbit_drawer.color("#555555")
orbit_drawer.pensize(1)

# Drawer for rings (to be re-computed when zoom changes)
ring_drawer = turtle.Turtle(visible=False)
ring_drawer.hideturtle()
ring_drawer.penup()
ring_drawer.color("#aaaaaa")

# Info display turtle
info_turtle = turtle.Turtle(visible=False)
info_turtle.hideturtle()
info_turtle.penup()
info_turtle.color("white")

# HUD turtle (fps/time/speed)
hud_turtle = turtle.Turtle(visible=False)
hud_turtle.hideturtle()
hud_turtle.penup()
hud_turtle.color("white")

# -------------------------
# CLASSES: CelestialBody, Planet, Moon
# -------------------------
class CelestialBody:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.turtle = turtle.Turtle(visible=False)
        self.turtle.hideturtle()
        self.turtle.penup()
        self.turtle.shape("circle")
        self.turtle.color(self.color)
        self.trail = []  # list of past positions for trail [ (x_px, y_px) ... ]
        self.show_label = False
        self.label_turtle = None

    def world_to_screen(self, x, y):
        """Convert world (simulation) coordinates (pixels) to screen coords applying pan/zoom."""
        sx = (x + view_offset_x) * GLOBAL_SCALE
        sy = (y + view_offset_y) * GLOBAL_SCALE
        return sx, sy

    def set_screen_pos(self, x, y):
        sx, sy = self.world_to_screen(x, y)
        self.turtle.goto(sx, sy)
        if self.label_turtle:
            self.label_turtle.clear()
            self.label_turtle.goto(sx, sy + 12 * GLOBAL_SCALE)
            self.label_turtle.write(self.name, align="center", font=("Arial", int(9 * GLOBAL_SCALE), "normal"))

    def show_info(self, text):
        info_turtle.clear()
        # position info near object on screen
        sx, sy = self.world_to_screen(self.curr_x, self.curr_y)
        box_w = 260 * GLOBAL_SCALE
        box_h = 70 * GLOBAL_SCALE
        bx = clamp(sx + 30, -SCREEN_WIDTH/2 + 10, SCREEN_WIDTH/2 - box_w - 10)
        by = clamp(sy + 30, -SCREEN_HEIGHT/2 + 10, SCREEN_HEIGHT/2 - box_h - 10)
        info_turtle.penup()
        info_turtle.goto(bx, by)
        info_turtle.pendown()
        info_turtle.fillcolor("#111111")
        info_turtle.begin_fill()
        for _ in range(2):
            info_turtle.forward(box_w)
            info_turtle.right(90)
            info_turtle.forward(box_h)
            info_turtle.right(90)
        info_turtle.end_fill()
        info_turtle.penup()
        info_turtle.goto(bx + 10, by - 20)
        info_turtle.color("white")
        for i, line in enumerate(text.split("\n")):
            info_turtle.goto(bx + 10, by - 10 - i*18)
            info_turtle.write(line, font=("Arial", int(10 * GLOBAL_SCALE), "normal"))
        # schedule clearing
        screen.ontimer(info_turtle.clear, INFO_DISPLAY_MS)

class Planet(CelestialBody):
    def __init__(self, name, a_au, ecc, inc_deg, period_days, radius_km, color, tilt_deg, rot_hours):
        super().__init__(name, color)
        self.a = a_au
        self.e = ecc
        self.inc = inc_deg
        self.period_days = period_days
        self.radius_km = radius_km
        self.radius_px = radius_km_to_pixels(radius_km)
        self.turtle.shapesize(self.radius_px/10.0 * GLOBAL_SCALE, self.radius_px/10.0 * GLOBAL_SCALE)
        self.turtle.color(self.color)
        self.angle_deg = random.uniform(0, 360)  # current true anomaly approx
        self.mean_anomaly = 0.0
        self.omega = 0.0  # argument of perihelion - unused in simplified sim
        self.inclination = inc_deg
        self.axial_tilt = tilt_deg
        self.rotation_hours = rot_hours
        self.curr_x = 0.0
        self.curr_y = 0.0
        self.moons = []
        self.rings = []
        self.show_label = True
        # For shading (day/night)
        self.rotation_angle = random.uniform(0, 360)

    def compute_orbital_position(self, sim_days):
        """Compute elliptical orbit position (approx using parametric ellipse).
           For visualization we compress a lot: we will compute angle proportional to sim_days/period.
        """
        # mean motion (revolutions per day): 1/period
        frac = (sim_days / self.period_days) % 1.0
        # convert fraction to angle around ellipse (0..360)
        theta = frac * 360.0 + self.angle_deg  # degrees
        # parametric ellipse in plane
        a_px = au_to_px(self.a)
        b_px = a_px * math.sqrt(1 - self.e**2)
        rad = math.radians(theta)
        x = a_px * math.cos(rad)
        y = b_px * math.sin(rad)
        # apply small inclination tilt by rotating around x
        inc_rad = math.radians(self.inclination)
        y = y * math.cos(inc_rad)
        # apply axial rotation for visual variety
        self.curr_x = x
        self.curr_y = y
        return x, y

    def update_visual(self):
        # update turtle size in case GLOBAL_SCALE changed
        self.turtle.shapesize((self.radius_px / 10.0) * GLOBAL_SCALE, (self.radius_px / 10.0) * GLOBAL_SCALE)
        self.turtle.color(self.color)

    def draw(self, sim_days, dt_days):
        # compute orbital position
        x, y = self.compute_orbital_position(sim_days)
        self.rotation_angle = (self.rotation_angle + (360.0 * dt_days / (self.rotation_hours / 24.0))) % 360.0 if self.rotation_hours != 0 else self.rotation_angle
        self.curr_x = x
        self.curr_y = y
        sx, sy = self.world_to_screen(x, y)

        # show/hide turtle
        self.turtle.showturtle()
        # position
        self.turtle.goto(sx, sy)

        # draw day/night shading by stamping a darker semicircle overlay (approx)
        if USE_SHADING:
            # We'll simulate a simple shading by drawing a semi-transparent overlay using turtle stamps:
            # Since turtle cannot set alpha, we approximate by drawing a darker circle partially overlapping.
            # Create a separate turtle to draw overlay (per-planet temporary)
            overlay = turtle.Turtle(visible=False)
            overlay.hideturtle()
            overlay.penup()
            overlay.goto(sx, sy)
            overlay.shape("circle")
            # choose darker color
            dark = shade_color(self.color, -0.45)
            overlay.color(dark)
            overlay.shapesize((self.radius_px/10.0) * GLOBAL_SCALE, (self.radius_px/10.0) * GLOBAL_SCALE)
            # rotate overlay by relative sun angle: sun at (0,0) world coords
            # compute vector from planet to sun: sun at (0,0) world:
            dx = -self.curr_x
            dy = -self.curr_y
            sun_angle = math.degrees(math.atan2(dy, dx))
            # shading rotation depends on combined planet rotation and sun angle - just offset to look nice
            # We'll stamp overlay then clear it (so overlay just paints darker semicircle). To approximate semicircle, stamp twice with offset.
            overlay.setheading(sun_angle + 90 + self.rotation_angle * 0.5)
            overlay.stamp()
            overlay.setheading(sun_angle - 90 + self.rotation_angle * 0.5)
            overlay.stamp()
            overlay.clear()
            overlay.hideturtle()
            del overlay

        # trails
        if SHOW_TRAILS:
            self.trail.append((sx, sy))
            if len(self.trail) > MAX_TRAIL_POINTS:
                self.trail.pop(0)
            # draw trail
            for i in range(len(self.trail)-1):
                a = self.trail[i]
                b = self.trail[i+1]
                screen.getcanvas().create_line(a[0], -a[1], b[0], -b[1], fill=self.color, width=max(1, int(1*GLOBAL_SCALE)), stipple="")
        else:
            self.trail = []

        # labels
        if SHOW_LABELS:
            if not self.label_turtle:
                self.label_turtle = turtle.Turtle(visible=False)
                self.label_turtle.hideturtle()
                self.label_turtle.penup()
                self.label_turtle.color("white")
            self.label_turtle.clear()
            self.label_turtle.goto(sx, sy + 12 * GLOBAL_SCALE)
            self.label_turtle.write(self.name, align="center", font=("Arial", int(9 * GLOBAL_SCALE), "normal"))
        else:
            if self.label_turtle:
                self.label_turtle.clear()

        # draw moons
        for m in self.moons:
            m.draw(sim_days, dt_days, parent_x=self.curr_x, parent_y=self.curr_y)

class Moon(CelestialBody):
    def __init__(self, parent_planet, name, dist_thousand_km, period_days, radius_km, color, ecc=0.0, inc_deg=0.0):
        super().__init__(name, color)
        self.parent = parent_planet
        self.dist_thousand_km = dist_thousand_km
        self.orbital_period = period_days
        self.radius_km = radius_km
        self.radius_px = max(2.5, radius_km_to_pixels(radius_km) * 0.45)  # moons smaller
        self.ecc = ecc
        self.incl = inc_deg
        self.angle = random.uniform(0, 360)
        self.curr_x = 0.0
        self.curr_y = 0.0

        self.turtle.shape("circle")
        self.turtle.shapesize(self.radius_px/10.0 * GLOBAL_SCALE, self.radius_px/10.0 * GLOBAL_SCALE)
        self.turtle.color(self.color)

    def draw(self, sim_days, dt_days, parent_x=0.0, parent_y=0.0):
        # compute orbital angle fraction relative to sim_days scaled by orbital_period
        frac = (sim_days / self.orbital_period) % 1.0
        theta = frac * 360.0 + self.angle
        rad = math.radians(theta)
        # convert dist (thousand km) to pixel units around parent using function
        parent_radius_px = self.parent.radius_px
        r_px = moon_dist_to_pixels(self.dist_thousand_km, parent_radius_px)
        x = parent_x + r_px * math.cos(rad)
        y = parent_y + r_px * math.sin(rad) * math.cos(math.radians(self.incl))
        self.curr_x = x
        self.curr_y = y
        sx, sy = self.world_to_screen(x, y)
        self.turtle.showturtle()
        self.turtle.shapesize((self.radius_px/10.0) * GLOBAL_SCALE, (self.radius_px/10.0) * GLOBAL_SCALE)
        self.turtle.goto(sx, sy)

        # trail
        if SHOW_TRAILS:
            self.trail.append((sx, sy))
            if len(self.trail) > MAX_TRAIL_POINTS:
                self.trail.pop(0)
            for i in range(len(self.trail)-1):
                a = self.trail[i]
                b = self.trail[i+1]
                screen.getcanvas().create_line(a[0], -a[1], b[0], -b[1], fill=self.color, width=max(1, int(1*GLOBAL_SCALE)))
        else:
            self.trail = []

        # label small or skip
        if SHOW_LABELS:
            if not self.label_turtle:
                self.label_turtle = turtle.Turtle(visible=False)
                self.label_turtle.hideturtle()
                self.label_turtle.penup()
                self.label_turtle.color("white")
            self.label_turtle.clear()
            self.label_turtle.goto(sx, sy + 8 * GLOBAL_SCALE)
            # small font for moons
            self.label_turtle.write(self.name, align="center", font=("Arial", int(7 * GLOBAL_SCALE), "normal"))
        else:
            if self.label_turtle:
                self.label_turtle.clear()

# -------------------------
# Helper: shade color (darken/lighten hex)
# -------------------------
def shade_color(hex_color, amount=0.0):
    # hex_color like "#RRGGBB"; amount in [-1,1] negative darkens
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    def clamp8(x): return int(max(0, min(255, x)))
    if amount < 0:
        factor = 1.0 + amount
        r, g, b = clamp8(r * factor), clamp8(g * factor), clamp8(b * factor)
    else:
        r = clamp8(r + (255 - r) * amount)
        g = clamp8(g + (255 - g) * amount)
        b = clamp8(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"

# -------------------------
# Build Planets & Moons from raw data
# -------------------------
planets = []
planet_map = {}

for p in PLANET_RAW:
    name, a, e, inc, period, radius_km, color, tilt, rot = p
    planet = Planet(name, a, e, inc, period, radius_km, color, tilt, rot)
    # place initial turtle size & show
    planet.turtle.shapesize((planet.radius_px/10.0) * GLOBAL_SCALE, (planet.radius_px/10.0) * GLOBAL_SCALE)
    planet.turtle.color(planet.color)
    planet.turtle.penup()
    planet.turtle.hideturtle()
    planets.append(planet)
    planet_map[name] = planet

# Attach moons
for m in MOONS_RAW:
    parent_name, moon_name, dist_km, period_days, radius_km, color, ecc, inc = m
    if parent_name in planet_map:
        moon = Moon(planet_map[parent_name], moon_name, dist_km, period_days, radius_km, color, ecc, inc)
        planet_map[parent_name].moons.append(moon)

# Attach rings
for r in RINGS_RAW:
    parent_name, inner_km, outer_km, thickness_km, color = r
    if parent_name in planet_map:
        planet_map[parent_name].rings.append((inner_km, outer_km, thickness_km, color))

# -------------------------
# Draw Orbits (static)
# -------------------------
def draw_orbits():
    orbit_drawer.clear()
    if not SHOW_ORBITS:
        return
    orbit_drawer.penup()
    orbit_drawer.color("#444444")
    orbit_drawer.pensize(max(1, int(1 * GLOBAL_SCALE)))
    for p in planets:
        a_px = au_to_px(p.a)
        b_px = a_px * math.sqrt(1 - p.e**2)
        # draw ellipse by plotting many small segments
        steps = 240
        points = []
        for i in range(steps+1):
            theta = 2 * math.pi * i / steps
            x = a_px * math.cos(theta)
            y = b_px * math.sin(theta) * math.cos(math.radians(p.inclination))
            sx, sy = (x + view_offset_x) * GLOBAL_SCALE, (y + view_offset_y) * GLOBAL_SCALE
            points.append((sx, sy))
        # use canvas for fine grained control
        for i in range(len(points)-1):
            a = points[i]
            b = points[i+1]
            screen.getcanvas().create_line(a[0], -a[1], b[0], -b[1], fill="#444444")

# Draw rings for planets with rings
def draw_rings():
    ring_drawer.clear()
    for p in planets:
        if not p.rings:
            continue
        px, py = p.curr_x, p.curr_y
        sx, sy = (px + view_offset_x) * GLOBAL_SCALE, (py + view_offset_y) * GLOBAL_SCALE
        for (inner_km, outer_km, thickness_km, color) in p.rings:
            # convert km to pixels relative to planet radius and AU scale (very approximate)
            # outer_km ~ 140000 for Saturn as sample -> convert to visual pixels
            base = p.radius_px * 1.5
            inner_px = base + inner_km * 0.0005 * GLOBAL_SCALE
            outer_px = base + outer_km * 0.0005 * GLOBAL_SCALE
            # draw a filled ring by drawing many small lines
            steps = 120
            for i in range(steps):
                angle = 2*math.pi*i/steps
                x1 = sx + inner_px * math.cos(angle)
                y1 = sy + inner_px * math.sin(angle) * math.cos(math.radians(p.inclination))
                x2 = sx + outer_px * math.cos(angle)
                y2 = sy + outer_px * math.sin(angle) * math.cos(math.radians(p.inclination))
                screen.getcanvas().create_line(x1, -y1, x2, -y2, fill=color)

# -------------------------
# Interaction Handlers
# -------------------------
def toggle_pause():
    global paused
    paused = not paused

def speed_up():
    global TIME_SCALE
    TIME_SCALE *= 1.8
    show_hud_message(f"Speed ×{TIME_SCALE:.1f}")

def slow_down():
    global TIME_SCALE
    TIME_SCALE /= 1.8
    show_hud_message(f"Speed ×{TIME_SCALE:.1f}")

def toggle_orbits_action():
    global SHOW_ORBITS
    SHOW_ORBITS = not SHOW_ORBITS
    clear_canvas_drawings()
    draw_orbits()

def toggle_labels_action():
    global SHOW_LABELS
    SHOW_LABELS = not SHOW_LABELS
    for p in planets:
        if not SHOW_LABELS and p.label_turtle:
            p.label_turtle.clear()

def toggle_trails_action():
    global SHOW_TRAILS
    SHOW_TRAILS = not SHOW_TRAILS
    if not SHOW_TRAILS:
        clear_canvas_drawings()

def zoom_in():
    global GLOBAL_SCALE
    GLOBAL_SCALE *= 1.2
    recalc_visuals()
    clear_canvas_drawings()
    draw_orbits()
    draw_rings()

def zoom_out():
    global GLOBAL_SCALE
    GLOBAL_SCALE /= 1.2
    recalc_visuals()
    clear_canvas_drawings()
    draw_orbits()
    draw_rings()

def pan(dx, dy):
    global view_offset_x, view_offset_y
    view_offset_x += dx / GLOBAL_SCALE
    view_offset_y += dy / GLOBAL_SCALE
    clear_canvas_drawings()
    draw_orbits()
    draw_rings()

def reset_view():
    global view_offset_x, view_offset_y, GLOBAL_SCALE
    view_offset_x, view_offset_y, GLOBAL_SCALE = DEFAULT_VIEW
    clear_canvas_drawings()
    recalc_visuals()
    draw_orbits()
    draw_rings()

def quit_sim():
    turtle.bye()
    sys.exit(0)

# Draw a short HUD message
def show_hud_message(msg):
    hud_turtle.clear()
    hud_turtle.goto(-SCREEN_WIDTH/2 + 10, SCREEN_HEIGHT/2 - 30)
    hud_turtle.write(msg, font=("Arial", 12, "bold"))

# Clear canvas low-level drawings (trails/orbits drawn on canvas)
def clear_canvas_drawings():
    # easiest: clear the whole screen canvas and re-draw static things
    canvas = screen.getcanvas()
    canvas.delete("all")

# Click handler to detect planet/moon clicks
def on_click(x, y):
    # convert screen coords to world coords
    wx = x / GLOBAL_SCALE - view_offset_x
    wy = y / GLOBAL_SCALE - view_offset_y
    # note: turtle onscreen coords are relative to center, but Tk canvas y is inverted; turtle passes coords in normal orientation
    # check planets then moons
    for p in planets:
        dist = math.hypot(p.curr_x - wx, p.curr_y - wy)
        # hit radius approx: visual radius px scaled back to world coords
        hit_px = p.radius_px * 1.5
        if dist <= hit_px:
            p.show_info(generate_info_text_for_planet(p))
            return
        for m in p.moons:
            mdist = math.hypot(m.curr_x - wx, m.curr_y - wy)
            if mdist <= max(6, m.radius_px * 1.5):
                m.show_info(generate_info_text_for_moon(m))
                return

def generate_info_text_for_planet(p):
    lines = [
        f"{p.name}",
        f"Semi-major axis: {p.a:.3f} AU",
        f"Eccentricity: {p.e:.4f}  Inclination: {p.incl:.2f}°",
        f"Orbital period: {p.period_days:.1f} days",
        f"Radius (km): {p.radius_km:.0f}  Axial tilt: {p.axial_tilt:.1f}°"
    ]
    return "\n".join(lines)

def generate_info_text_for_moon(m):
    lines = [
        f"{m.name} (moon of {m.parent.name})",
        f"Orbital period: {m.orbital_period:.2f} days",
        f"Distance (thousand km): {m.dist_thousand_km:.1f}",
        f"Radius (km): {m.radius_km:.1f}"
    ]
    return "\n".join(lines)

# -------------------------
# Keyboard bindings
# -------------------------
screen.listen()
screen.onkey(toggle_pause, "space")
screen.onkey(speed_up, "+")
screen.onkey(speed_up, "=")
screen.onkey(slow_down, "-")
screen.onkey(slow_down, "_")
screen.onkey(toggle_orbits_action, "o")
screen.onkey(toggle_labels_action, "l")
screen.onkey(toggle_trails_action, "t")
screen.onkey(zoom_in, "z")
screen.onkey(zoom_out, "x")
screen.onkey(lambda: pan(-40, 0), "Left")
screen.onkey(lambda: pan(40, 0), "Right")
screen.onkey(lambda: pan(0, 40), "Up")
screen.onkey(lambda: pan(0, -40), "Down")
screen.onkey(reset_view, "r")
screen.onkey(quit_sim, "q")
screen.onkey(quit_sim, "Escape")
screen.onclick(on_click)

# -------------------------
# Recalc visuals after zoom/pan
# -------------------------
def recalc_visuals():
    # update shape sizes for planets and moons based on GLOBAL_SCALE
    for p in planets:
        p.turtle.shapesize((p.radius_px/10.0) * GLOBAL_SCALE, (p.radius_px/10.0) * GLOBAL_SCALE)
        for m in p.moons:
            m.turtle.shapesize((m.radius_px/10.0) * GLOBAL_SCALE, (m.radius_px/10.0) * GLOBAL_SCALE)

# -------------------------
# Simulation main loop
# -------------------------
last_time = time.time()
sim_days = 0.0

def main_loop():
    global last_time, sim_days
    # clear static drawings initially
    clear_canvas_drawings()
    draw_orbits()
    draw_rings()
    # draw sun once as static big circle at origin transformed to view
    while True:
        now = time.time()
        dt_real = now - last_time
        last_time = now
        if not paused:
            dt_sim_days = dt_real * TIME_SCALE
            sim_days += dt_sim_days
        else:
            dt_sim_days = 0.0
        # update planets
        # clear per-frame dynamic canvas (but keep static orbits/rings if desired)
        # To avoid clearing orbits, we will clear and re-draw everything each frame via canvas clearing,
        # but re-drawing orbits each frame isn't too costly with this optimization.
        clear_canvas_drawings()
        # draw static orbits (if toggled)
        if SHOW_ORBITS:
            draw_orbits()
        # draw rings (they are drawn near planets so draw later after planet positions computed)
        # draw sun
        sx, sy = (0 + view_offset_x) * GLOBAL_SCALE, (0 + view_offset_y) * GLOBAL_SCALE
        # draw sun using turtle stamp
        sun_px = 25 * GLOBAL_SCALE
        sun_turtle.clear()
        sun_turtle.goto(sx, sy)
        sun_turtle.shape("circle")
        sun_turtle.shapesize(sun_px/10.0, sun_px/10.0)
        sun_turtle.color(SUN_COLOR)
        sun_turtle.showturtle()
        # annotate center with glow via canvas ovals (approx)
        canvas = screen.getcanvas()
        glow_r = sun_px * 1.8
        canvas.create_oval(sx - glow_r, - (sy - glow_r), sx + glow_r, - (sy + glow_r), fill="#221100", outline="")

        # update/draw each planet
        for p in planets:
            p.update_visual()
            p.draw(sim_days, dt_sim_days)
        # after planet positions, draw rings anchored to planets (so rings appear around moving planets)
        draw_rings()

        # HUD
        hud_turtle.clear()
        hud_turtle.goto(-SCREEN_WIDTH/2 + 10, SCREEN_HEIGHT/2 - 20)
        hud_turtle.write(f"Sim days: {sim_days:.1f}   Speed ×{TIME_SCALE:.1f}   Trails: {'On' if SHOW_TRAILS else 'Off'}   Orbits: {'On' if SHOW_ORBITS else 'Off'}", font=("Arial", 11, "normal"))

        # finalize frame
        screen.update()
        # small sleep to limit CPU
        time.sleep(0.016)  # ~60 fps target

try:
    recalc_visuals()
    draw_orbits()
    draw_rings()
    main_loop()
except turtle.Terminator:
    pass
