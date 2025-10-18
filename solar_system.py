"""
Solar System — Enhanced Turtle Simulation
- Features added:
    * Starfield background
    * Elliptical orbits (eccentricity) and inclination (visual tilt)
    * Kepler-like orbital speed scaling (period ~ a^(1.5)) so outer planets move slower
    * Planet axial rotation (visual spin) and optional rings and moons
    * Moon rendering and independent orbits (example: Earth's Moon, Jupiter's Galilean moons)
    * Click planets to open detailed popups, improved label handling
    * Toggle controls: Pause/Resume, Speed Up/Down, Toggle orbits/labels/moons, Spawn comet, Reset
    * Comet with long fading trail on demand
    * Adjustable realism parameters at top of file

Run with: python solar_system_enhanced.py
Controls:
    Space    : Pause / Resume
    + / -    : Speed up / Slow down simulation
    o        : Toggle orbit lines
    i        : Toggle planet labels
    m        : Toggle moons
    c        : Spawn a comet crossing the system
    r        : Reset simulation (positions back to start)
    s        : Toggle starfield sparkle
    Click a planet : Show a small info popup for that planet

Notes:
- This is a visualization, not a full N-body physics simulation. Orbital motion uses simple parametric equations
  with Kepler-like scaling to feel realistic while remaining viewable.
- Turtle is single-threaded; keep star counts reasonable for performance.
"""

import turtle
import math
import random
import time
from collections import namedtuple

# -------------------------
# USER CONFIGURATION
# -------------------------
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
CENTER = (0, 0)
GLOBAL_SCALE = 0.9            # overall visual scale
AU_PIXELS = 14 * GLOBAL_SCALE # how many pixels per AU (distance scale)
PLANET_SIZE_SCALE = 4.0 * GLOBAL_SCALE
MIN_PLANET_PIXEL = 3
LABEL_OFFSET = 14
FRAME_SLEEP = 0.01            # base sleep per frame
STAR_COUNT = 180             # number of background stars
SPARKLE = True               # star twinkle enabled
COMET_TRAIL_LENGTH = 80

# Realism controls
ECCENTRICITY_VISUAL_SCALE = 0.8   # exaggerate eccentricities for visibility
INCLINATION_VISUAL_SCALE = 0.9    # scale tilt of orbital plane for visual variety
KEPLER_COMPRESSION = 0.9          # compress Kepler's 1.5 exponent slightly for animation speed

# UI toggles default
SHOW_ORBITS = True
SHOW_LABELS = True
SHOW_MOONS = True

# Informational text for popups
PLANET_INFOS = {
    "Mercury": "Mercury\nSmallest planet. Closest to the Sun. Heavy cratering.",
    "Venus": "Venus\nHot, dense CO2 atmosphere. Retrograde rotation.",
    "Earth": "Earth\nOur home. 1 Moon (Luna). Liquid water, life.",
    "Mars": "Mars\nThe red planet. Olympus Mons, Valles Marineris. Two small moons.",
    "Jupiter": "Jupiter\nGas giant. Strong storms. Many moons (4 large Galilean).",
    "Saturn": "Saturn\nGas giant with iconic icy rings. Many moons.",
    "Uranus": "Uranus\nIce giant. Tilted axis (~98°). Faint rings.",
    "Neptune": "Neptune\nIce giant. Strong winds. Triton is large retrograde moon.",
    "Pluto": "Pluto\nDwarf planet. Icy surface and Charon as a big companion."
}

# -------------------------
# PLANETARY DATA
# Each planet: name, semi_major_axis_AU, visual_radius_rel, eccentricity, inclination_deg, color, has_rings, moons_list
# moons_list: tuples (name, distance_rel (to planet), size_rel, period_days)
# Distances and sizes are simplified for visualization.
# -------------------------
PlanetData = namedtuple('PlanetData', 'name a size_ecc incl color rings moons label')

PLANET_RAW = [
    # name, a(AU), size_rel (Earth=1), eccentricity, inclination(deg), color, rings(bool), moons
    ("Mercury", 0.39, 0.38, 0.205, 7.0, "gray", False, []),
    ("Venus",   0.72, 0.95, 0.0067, 3.4, "orange", False, []),
    ("Earth",   1.00, 1.00, 0.0167, 0.0, "dodger blue", False, [("Luna", 0.0026, 0.27, 27.3)]),
    ("Mars",    1.52, 0.53, 0.0934, 1.85, "firebrick", False, [("Phobos", 0.0009, 0.08, 0.3),("Deimos", 0.0016, 0.05, 1.3)]),
    ("Jupiter", 5.20, 11.21, 0.0489, 1.3, "saddle brown", True, [("Io",0.0028,0.2,1.8),("Europa",0.0045,0.17,3.5),("Ganymede",0.0071,0.28,7.1),("Callisto",0.0125,0.25,16.7)]),
    ("Saturn",  9.58, 9.45, 0.0565, 2.5, "gold", True, [("Titan",0.008,0.5,15.9)]),
    ("Uranus", 19.20, 4.01, 0.046, 0.8, "light sky blue", True, []),
    ("Neptune",30.05, 3.88, 0.0097, 1.8, "navy", False, [("Triton",0.004,0.22,5.9)]),
    ("Pluto",   39.48, 0.18, 0.2488, 17.2, "white", False, [("Charon",0.0016,0.18,6.4)])
]

# Convert raw into PlanetData with safe defaults
PLANETS_DATA = []
for raw in PLANET_RAW:
    name, a, size_rel, ecc, incl, color, rings, moons = raw
    PLANETS_DATA.append(PlanetData(name, a, (size_rel, ecc), incl, color, rings, moons, name))  # Added 'label' field

# -------------------------
# Turtle setup
# -------------------------
screen = turtle.Screen()
screen.setup(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
screen.title("Solar System — Enhanced (Turtle)")
screen.bgcolor("black")
screen.tracer(0, 0)

# global drawer turtles
sun = turtle.Turtle()
sun.hideturtle()
sun.penup()
sun.goto(CENTER)
sun.shape("circle")
sun.color("yellow")
sun.shapesize(2.6, 2.6)
sun.showturtle()

orbit_drawer = turtle.Turtle()
orbit_drawer.hideturtle()
orbit_drawer.penup()
orbit_drawer.pensize(1)

ui_turtle = turtle.Turtle()
ui_turtle.hideturtle()
ui_turtle.penup()
ui_turtle.color("white")

info_turtle = turtle.Turtle()
info_turtle.hideturtle()
info_turtle.penup()
info_turtle.color("white")

# starfield turtles (small list for performance)
star_turtles = []

# -------------------------
# Helper functions
# -------------------------

def world_to_screen(x, y):
    # in this visualization world coords are same as screen coords
    return x, y


def kepler_period(a_au):
    """Return a period-like value in arbitrary time units for semi-major axis a (AU).
    Uses simplified Kepler's third law: period ∝ a^(3/2). We'll compress it for animation.
    """
    return (a_au ** (1.5 * KEPLER_COMPRESSION))


def random_starfield(count=STAR_COUNT):
    # Generate stars as tiny dots scattered on screen
    for _ in range(count):
        t = turtle.Turtle()
        t.hideturtle()
        t.penup()
        t.shape('circle')
        t.shapesize(0.08, 0.08)
        t.color(random.choice(['white', 'light gray', 'light yellow']))
        x = random.randint(-SCREEN_WIDTH//2 + 20, SCREEN_WIDTH//2 - 20)
        y = random.randint(-SCREEN_HEIGHT//2 + 20, SCREEN_HEIGHT//2 - 20)
        t.goto(x, y)
        t.showturtle()
        star_turtles.append((t, random.random()))  # store base brightness


# -------------------------
# Planet / Moon / Comet classes
# -------------------------
class Planet:
    def __init__(self, pdata: PlanetData):
        self.name = pdata.name
        self.a = pdata.a  # semi-major axis in AU
        self.ecc = pdata.size_ecc[1]
        self.size_rel = pdata.size_ecc[0]
        self.incl = pdata.incl
        self.color = pdata.color
        self.has_rings = pdata.rings
        self.moons_raw = pdata.moons

        # derived visual properties
        self.distance_px = self.a * AU_PIXELS
        raw_radius = max(MIN_PLANET_PIXEL, self.size_rel * PLANET_SIZE_SCALE)
        self.radius = raw_radius

        # turtle for planet
        self.t = turtle.Turtle()
        self.t.hideturtle()
        self.t.penup()
        self.t.shape('circle')
        size_for_shape = max(0.12, self.radius / 8.0)
        self.t.shapesize(size_for_shape, size_for_shape)
        self.t.color(self.color)
        self.t.showturtle()

        # orbital parameters
        self.angle = random.uniform(0, 360)
        self.omega = 360.0 / (kepler_period(self.a) * 60.0)  # degrees per arbitrary "base frame" unit
        # increase angular speed a bit for inner planets to make animation lively
        self.omega *= (1.0 + (1.0 / max(0.1, self.a)))

        # create moons
        self.moons = []
        for mraw in self.moons_raw:
            m = Moon(mraw[0], mraw[1], mraw[2], mraw[3], parent=self)
            self.moons.append(m)

        # label turtle
        self.label_t = None

    def orbital_position(self, angle_deg=None):
        # parametric ellipse: x = a*(cosE - e), y = b*sinE, where b = a*sqrt(1-e^2)
        angle = angle_deg if angle_deg is not None else self.angle
        rad = math.radians(angle)
        a_px = self.distance_px
        e_vis = min(0.9, self.ecc * ECCENTRICITY_VISUAL_SCALE)
        b_px = a_px * math.sqrt(max(0.0, 1 - e_vis * e_vis))
        # rotate plane by inclination for simple visual effect (scale y)
        x = a_px * math.cos(rad) - (e_vis * a_px)
        y = b_px * math.sin(rad) * (math.cos(math.radians(self.incl * INCLINATION_VISUAL_SCALE)))
        return x, y

    def update(self, dt, speed_multiplier):
        # advance angle according to omega (deg per second-ish)
        self.angle = (self.angle + self.omega * speed_multiplier * dt * 60.0) % 360.0
        x, y = self.orbital_position()
        self.t.goto(x, y)
        if SHOW_LABELS:
            self.show_label(x, y)
        else:
            self.hide_label()
        # update moons
        if SHOW_MOONS:
            for m in self.moons:
                m.update(dt, speed_multiplier)
        else:
            for m in self.moons:
                m.hide()

    def show_label(self, x, y):
        if not self.label_t:
            self.label_t = turtle.Turtle()
            self.label_t.hideturtle()
            self.label_t.penup()
            self.label_t.color('white')
        self.label_t.clear()
        self.label_t.goto(x, y + LABEL_OFFSET)
        self.label_t.write(self.name, align='center', font=('Arial', 9, 'normal'))

    def hide_label(self):
        if self.label_t:
            self.label_t.clear()
            self.label_t.hideturtle()
            self.label_t = None

    def draw_orbit(self):
        if not SHOW_ORBITS:
            return
        orbit_drawer.penup()
        a_px = self.distance_px
        e_vis = min(0.9, self.ecc * ECCENTRICITY_VISUAL_SCALE)
        b_px = a_px * math.sqrt(max(0.0, 1 - e_vis * e_vis))
        # compute an ellipse by drawing many small line segments
        steps = max(120, int(a_px / 2))
        points = []
        for i in range(steps + 1):
            theta = 2 * math.pi * i / steps
            x = a_px * math.cos(theta) - (e_vis * a_px)
            y = b_px * math.sin(theta) * math.cos(math.radians(self.incl * INCLINATION_VISUAL_SCALE))
            points.append((x, y))
        orbit_drawer.color('dim gray')
        orbit_drawer.penup()
        for idx, pt in enumerate(points):
            if idx == 0:
                orbit_drawer.goto(pt)
                orbit_drawer.pendown()
            else:
                orbit_drawer.goto(pt)
        orbit_drawer.penup()

    def is_clicked(self, x, y):
        px, py = self.t.position()
        return math.hypot(px - x, py - y) <= max(10, self.radius)


class Moon:
    def __init__(self, name, dist_rel, size_rel, period_days, parent: Planet):
        self.name = name
        self.dist_rel = dist_rel  # relative to parent planet in "planet radii"
        self.size_rel = size_rel
        self.period = period_days
        self.parent = parent
        self.angle = random.uniform(0, 360)
        # visual distances
        self.orbit_px = max(parent.radius * 1.6, dist_rel * AU_PIXELS * 30)
        raw_radius = max(1.6, self.size_rel * 6)
        self.radius = raw_radius
        self.t = turtle.Turtle()
        self.t.hideturtle()
        self.t.penup()
        self.t.shape('circle')
        self.t.shapesize(max(0.08, self.radius / 6.0), max(0.08, self.radius / 6.0))
        self.t.color('light gray')
        self.t.showturtle()

    def update(self, dt, speed_multiplier):
        # simple circular orbit around parent
        # period influences angular speed
        omega = 360.0 / max(1.0, self.period)  # deg per some unit
        self.angle = (self.angle + omega * speed_multiplier * dt * 60.0) % 360.0
        rad = math.radians(self.angle)
        px, py = self.parent.t.position()
        x = px + math.cos(rad) * self.orbit_px
        y = py + math.sin(rad) * self.orbit_px
        self.t.goto(x, y)

    def hide(self):
        self.t.hideturtle()


class Comet:
    def __init__(self):
        self.t = turtle.Turtle()
        self.t.hideturtle()
        self.t.penup()
        self.t.shape('circle')
        self.t.shapesize(0.12, 0.12)
        self.t.color('white')
        # starting far upper-left
        self.angle = random.uniform(-40, 40)
        # a simple linear path crossing the system; use a long ellipse for curiosity
        self.a = random.uniform(35, 55) * AU_PIXELS
        self.b = random.uniform(6, 18) * AU_PIXELS
        self.t.goto(-self.a, self.b * 0.6)
        self.t.showturtle()
        self.t.pendown()
        self.trail = []
        self.alive = True
        self.speed = random.uniform(120.0, 300.0)  # pixels per second

    def update(self, dt, speed_multiplier):
        if not self.alive:
            return
        # move along x increasing
        px, py = self.t.position()
        new_x = px + self.speed * dt * speed_multiplier
        # make small sinusoidal waver for charm
        new_y = math.sin(new_x / 80.0) * (self.b * 0.6)
        self.t.goto(new_x, new_y)
        # maintain trail
        self.trail.append((new_x, new_y))
        if len(self.trail) > COMET_TRAIL_LENGTH:
            self.trail.pop(0)
        # draw trail by clearing a separate drawer each frame (cheap)
        comet_drawer.clear()
        # fade older points
        for i, (tx, ty) in enumerate(self.trail[-COMET_TRAIL_LENGTH:]):
            alpha = i / max(1, len(self.trail))
            comet_drawer.penup()
            comet_drawer.goto(tx, ty)
            comet_drawer.dot(max(2, 6 * (1 - alpha)))
        # vanish when out of bounds
        if abs(new_x) > SCREEN_WIDTH or abs(new_y) > SCREEN_HEIGHT:
            self.destroy()

    def destroy(self):
        self.t.clear()
        self.t.hideturtle()
        self.alive = False
        comet_drawer.clear()


# -------------------------
# Build world
# -------------------------
planets = []
for pdata in PLANETS_DATA:
    p = Planet(pdata)
    planets.append(p)

# Draw starfield
random_starfield()

# Draw static orbits initially
def draw_all_orbits():
    orbit_drawer.clear()
    for p in planets:
        p.draw_orbit()

if SHOW_ORBITS:
    draw_all_orbits()

# comet drawer (move this up so it's initialized before any comet is spawned)
comet_drawer = turtle.Turtle()
comet_drawer.hideturtle()
comet_drawer.penup()
comet_drawer.pensize(2)

active_comets = []

# -------------------------
# Interaction and UI
# -------------------------
running = True
speed_multiplier = 1.0
star_sparkle = SPARKLE


def toggle_pause():
    global running
    running = not running


def speed_up():
    global speed_multiplier
    speed_multiplier *= 1.4


def slow_down():
    global speed_multiplier
    speed_multiplier /= 1.4


def toggle_orbits():
    global SHOW_ORBITS
    SHOW_ORBITS = not SHOW_ORBITS
    orbit_drawer.clear()
    if SHOW_ORBITS:
        draw_all_orbits()


def toggle_labels():
    global SHOW_LABELS
    SHOW_LABELS = not SHOW_LABELS


def toggle_moons():
    global SHOW_MOONS
    SHOW_MOONS = not SHOW_MOONS


def spawn_comet():
    c = Comet()
    active_comets.append(c)


def reset_sim():
    global planets, active_comets, speed_multiplier
    speed_multiplier = 1.0
    for p in planets:
        p.angle = random.uniform(0, 360)
        p.t.goto(p.orbital_position(p.angle))
        for m in p.moons:
            m.angle = random.uniform(0, 360)
            m.t.goto(p.t.position())  # ensure moon starts at planet
    for c in active_comets:
        c.destroy()
    active_comets.clear()
    orbit_drawer.clear()
    if SHOW_ORBITS:
        draw_all_orbits()


def toggle_star_sparkle():
    global star_sparkle
    star_sparkle = not star_sparkle


def on_click(x, y):
    # check planets
    for p in planets:
        if p.is_clicked(x, y):
            show_info_popup(p)
            return


def show_info_popup(planet: Planet):
    info_turtle.clear()
    px, py = planet.t.position()
    # simple box
    box_w = 220
    box_h = 90
    box_x = px + 20
    box_y = py + 20
    half_w = SCREEN_WIDTH // 2 - 20
    half_h = SCREEN_HEIGHT // 2 - 20
    # Fix: ensure box stays within screen bounds
    box_x = max(-half_w, min(half_w - box_w, box_x))
    box_y = max(-half_h + box_h, min(half_h - 20, box_y))

    info_turtle.penup()
    info_turtle.goto(box_x, box_y)
    info_turtle.pendown()
    info_turtle.fillcolor('black')
    info_turtle.begin_fill()
    for _ in range(2):
        info_turtle.forward(box_w)
        info_turtle.right(90)
        info_turtle.forward(box_h)
        info_turtle.right(90)
    info_turtle.end_fill()
    info_turtle.penup()
    info_turtle.color('white')
    # write text lines
    lines = [planet.name, f"Semi-major axis: {planet.a:.2f} AU", f"Visual radius: {planet.radius:.1f} px"]
    if planet.name in PLANET_INFOS:
        lines += PLANET_INFOS[planet.name].split('\n')
    for i, line in enumerate(lines):
        info_turtle.goto(box_x + 10, box_y - 18 - i * 16)
        info_turtle.write(line, font=('Arial', 10, 'normal'))
    # schedule clearing
    screen.ontimer(lambda: info_turtle.clear(), 4500)

# Bind controls (add more key options for speed up/down for compatibility)
screen.listen()
screen.onkey(toggle_pause, 'space')
screen.onkey(speed_up, '+')
screen.onkey(speed_up, '=')
screen.onkey(speed_up, 'Up')
screen.onkey(slow_down, '-')
screen.onkey(slow_down, 'Down')
screen.onkey(toggle_orbits, 'o')
screen.onkey(toggle_labels, 'i')
screen.onkey(toggle_moons, 'm')
screen.onkey(spawn_comet, 'c')
screen.onkey(reset_sim, 'r')
screen.onkey(toggle_star_sparkle, 's')
screen.onclick(on_click)

# -------------------------
# Main animation loop
# -------------------------
last_time = time.time()
try:
    while True:
        now = time.time()
        dt = now - last_time
        last_time = now
        # Star sparkle (uncomment and fix for performance)
        if star_sparkle:
            for st, base in star_turtles:
                if random.random() < 0.02:
                    st.shapesize(random.uniform(0.06, 0.14))
        if running:
            for p in planets:
                p.update(dt, speed_multiplier)
            for c in list(active_comets):
                if c.alive:
                    c.update(dt, speed_multiplier)
                else:
                    active_comets.remove(c)
        screen.update()
        time.sleep(FRAME_SLEEP)
except turtle.Terminator:
    pass
