"""
Solar System (9 planets) - Turtle animation
- Run with: python solar_system.py
- Controls:
    Spacebar : Pause / Resume
    +        : Speed up simulation
    -        : Slow down simulation
    o        : Toggle orbit lines on/off
    i        : Toggle planet info labels on/off
    Click a planet : Show a small info popup for that planet
"""

import turtle
import math
import time

# -------------------------
# Configuration (tweakable)
# -------------------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
CENTER = (0, 0)
SCALE = 0.9  # global scale for distances/sizes
TIME_STEP = 0.5  # base timestep (used to control orbital speed)
SHOW_ORBITS = True
SHOW_LABELS = True

# A small set of descriptive info for each planet
PLANET_INFOS = {
    "Mercury": "Mercury\nSmallest planet. Closest to the Sun.",
    "Venus": "Venus\nHot, thick atmosphere. Earth's twin in size.",
    "Earth": "Earth\nOur home. 1 moon (Luna).",
    "Mars": "Mars\nThe red planet. Two small moons.",
    "Jupiter": "Jupiter\nLargest planet. Famous for the Great Red Spot.",
    "Saturn": "Saturn\nFamous rings made of ice & rock.",
    "Uranus": "Uranus\nIce giant, tilted on its side.",
    "Neptune": "Neptune\nFarthest giant planet (by orbit).",
    "Pluto": "Pluto\nDwarf planet. Cold and distant."
}

# -------------------------
# Planet data
# Distances (AU) and sizes (relative) are simplified and scaled for visualization.
# Orbital periods are in Earth days (used to set angular speed).
# Colors chosen to look pretty on black background.
# -------------------------
PLANETS = [
    # name, distance_AU, size_rel, orbital_period_days, color
    ("Mercury", 0.39, 0.38, 88,    "gray"),
    ("Venus",   0.72, 0.95, 225,   "orange"),
    ("Earth",   1.00, 1.00, 365,   "blue"),
    ("Mars",    1.52, 0.53, 687,   "red"),
    ("Jupiter", 5.20, 11.21, 4333, "saddle brown"),
    ("Saturn",  9.58, 9.45, 10759, "gold"),
    ("Uranus", 19.20, 4.01, 30687, "light blue"),
    ("Neptune",30.05, 3.88, 60190, "dark blue"),
    ("Pluto",   39.48, 0.18, 90560, "white")
]

# Visual scaling constants (for turtle window)
AU_PIXELS = 12 * SCALE       # 1 AU corresponds to this many pixels
PLANET_SIZE_SCALE = 3.5 * SCALE  # multiplier to convert relative sizes to pixels
MIN_PLANET_PIXEL = 4         # smallest visible planet radius in pixels
LABEL_OFFSET = 12

# -------------------------
# Turtle setup
# -------------------------
screen = turtle.Screen()
screen.setup(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
screen.bgcolor("black")
screen.title("Solar System — 9 Planets (Turtle Simulation)")
screen.tracer(0, 0)  # turn off automatic updates for smooth animation

# Draw the Sun at center
sun = turtle.Turtle()
sun.hideturtle()
sun.penup()
sun.goto(CENTER)
sun.shape("circle")
sun.color("yellow")
sun.shapesize(2.2, 2.2)  # Sun drawn larger
sun.showturtle()

# For orbit lines (single turtle we can use to draw static orbit circles)
orbit_drawer = turtle.Turtle()
orbit_drawer.hideturtle()
orbit_drawer.penup()
orbit_drawer.color("dim gray")
orbit_drawer.pensize(1)

# A text turtle to display info popups
info_turtle = turtle.Turtle()
info_turtle.hideturtle()
info_turtle.penup()
info_turtle.color("white")

# Container for planet objects
class Planet:
    def __init__(self, name, distance_au, size_rel, period_days, color):
        self.name = name
        self.distance = distance_au * AU_PIXELS  # convert to pixels
        # Ensure visibility for very small planets
        self.radius = max(MIN_PLANET_PIXEL, size_rel * PLANET_SIZE_SCALE)
        self.period = period_days
        self.color = color
        # create turtle
        self.turtle = turtle.Turtle()
        self.turtle.hideturtle()
        self.turtle.penup()
        self.turtle.shape("circle")
        # shapesize uses diameter scaling, so radius/10 yields reasonable look
        size_for_shape = max(0.15, self.radius / 10.0)
        self.turtle.shapesize(size_for_shape, size_for_shape)
        self.turtle.color(self.color)
        self.turtle.goto(self.distance, 0)
        self.turtle.showturtle()
        self.angle = 0.0  # degrees from +x
        self.label = None

    def update_position(self, angular_speed_deg):
        """Update angle & position using the provided angular speed (deg per frame)."""
        self.angle = (self.angle + angular_speed_deg) % 360.0
        rad = math.radians(self.angle)
        x = math.cos(rad) * self.distance
        y = math.sin(rad) * self.distance
        self.turtle.goto(x, y)
        if SHOW_LABELS:
            self._show_label(x, y)
        else:
            self._hide_label()

    def _show_label(self, x, y):
        # simple label that follows the planet
        if not self.label:
            self.label = turtle.Turtle()
            self.label.hideturtle()
            self.label.penup()
            self.label.color("white")
            self.label.goto(x, y + LABEL_OFFSET)
            self.label.write(self.name, align="center", font=("Arial", 9, "normal"))
            self.label.showturtle()
        else:
            self.label.clear()
            self.label.goto(x, y + LABEL_OFFSET)
            self.label.write(self.name, align="center", font=("Arial", 9, "normal"))

    def _hide_label(self):
        if self.label:
            self.label.clear()
            self.label.hideturtle()
            self.label = None

    def is_clicked(self, x, y):
        """Return True if given coordinate (screen coords) is within the planet's visible radius."""
        px, py = self.turtle.position()
        return math.hypot(px - x, py - y) <= max(12, self.radius)

# Create Planet instances
planets = []
for data in PLANETS:
    p = Planet(*data)
    planets.append(p)

# Draw orbits function
def draw_orbits():
    orbit_drawer.clear()
    orbit_drawer.penup()
    orbit_drawer.color("dim gray")
    for p in planets:
        orbit_drawer.goto(0, -p.distance)
        orbit_drawer.pendown()
        orbit_drawer.setheading(0)
        orbit_drawer.circle(p.distance)
        orbit_drawer.penup()

if SHOW_ORBITS:
    draw_orbits()

# -------------------------
# Simulation control state
# -------------------------
running = True
speed_multiplier = 1.0
SHOW_ORBITS_FLAG = SHOW_ORBITS
SHOW_LABELS_FLAG = SHOW_LABELS

# Map planetary period (days) to angular speed per frame:
# We want shorter period → faster angular increment.
# Base scale: choose a number of frames to complete one Earth-year orbit at base TIME_STEP.
EARTH_BASE_FRAMES = 360.0 / (TIME_STEP)  # arbitrary baseline
# We'll compute angular speed (deg per frame) as 360 / (period_in_frames)
def angular_speed_for_period(period_days):
    # Map orbital period (in days) to frames: shorter period -> fewer frames
    # We'll scale so Earth's period (365d) corresponds to a reasonable rotation speed.
    # period_frames = period_days / 365 * EARTH_BASE_FRAMES
    # To make outer planets visibly move we compress periods with a power factor.
    compression = 0.32  # Compress orbital period differences so outer planets still move
    period_frames = (period_days ** compression) / (365 ** compression) * EARTH_BASE_FRAMES
    if period_frames <= 0:
        return 0.1
    return 360.0 / period_frames

# Precompute angular speeds
base_angular_speeds = [angular_speed_for_period(p.period) for p in planets]

# -------------------------
# Interaction handlers
# -------------------------
def toggle_pause():
    global running
    running = not running

def speed_up():
    global speed_multiplier
    speed_multiplier *= 1.35

def slow_down():
    global speed_multiplier
    speed_multiplier /= 1.35

def toggle_orbits():
    global SHOW_ORBITS_FLAG
    SHOW_ORBITS_FLAG = not SHOW_ORBITS_FLAG
    orbit_drawer.clear()
    if SHOW_ORBITS_FLAG:
        draw_orbits()

def toggle_labels():
    global SHOW_LABELS_FLAG
    SHOW_LABELS_FLAG = not SHOW_LABELS_FLAG
    for p in planets:
        if SHOW_LABELS_FLAG:
            # force redraw on next loop
            p._show_label(*p.turtle.position())
        else:
            p._hide_label()

def on_click(x, y):
    # Convert click coords are already in screen coordinates matching turtle coords
    # Check each planet, show info popup for the first one clicked
    for p in planets:
        if p.is_clicked(x, y):
            show_info_popup(p)
            break

def show_info_popup(planet):
    # Clear previous info
    info_turtle.clear()
    px, py = planet.turtle.position()
    # draw a simple rectangle background
    box_w = 180
    box_h = 70
    box_x = px + 20
    box_y = py + 10

    # Ensure box stays on screen (basic clamp)
    half_w = SCREEN_WIDTH//2 - 20
    half_h = SCREEN_HEIGHT//2 - 20
    box_x = max(-half_w, min(half_w - box_w, box_x))
    box_y = max(-half_h + box_h, min(half_h - 20, box_y))

    info_turtle.penup()
    info_turtle.goto(box_x, box_y)
    info_turtle.pendown()
    info_turtle.fillcolor("black")
    info_turtle.begin_fill()
    for _ in range(2):
        info_turtle.forward(box_w)
        info_turtle.right(90)
        info_turtle.forward(box_h)
        info_turtle.right(90)
    info_turtle.end_fill()
    info_turtle.penup()
    info_turtle.goto(box_x + 10, box_y - 20)
    info_turtle.color("white")
    text = PLANET_INFOS.get(planet.name, f"{planet.name}")
    # write multi-line text
    for i, line in enumerate(text.split("\n")):
        info_turtle.goto(box_x + 10, box_y - 10 - i*18)
        info_turtle.write(line, font=("Arial", 10, "normal"))

    # schedule clearing popup after a few seconds
    screen.ontimer(lambda: info_turtle.clear(), 3500)

# Bind keys and click
screen.listen()
screen.onkey(toggle_pause, "space")
screen.onkey(speed_up, "+")
screen.onkey(speed_up, "plus")
screen.onkey(slow_down, "-")
screen.onkey(toggle_orbits, "o")
screen.onkey(toggle_labels, "i")
screen.onclick(on_click)

# -------------------------
# Animation main loop
# -------------------------
def main_loop():
    global running
    global speed_multiplier
    frame = 0
    last_time = time.time()
    while True:
        # compute time delta to keep animation time-consistent
        now = time.time()
        dt = now - last_time
        last_time = now

        if running:
            for idx, p in enumerate(planets):
                # angular speed scaled by base speed, global speed_multiplier, and dt
                angular_speed = base_angular_speeds[idx] * speed_multiplier * (TIME_STEP * (dt / 0.03))
                p.update_position(angular_speed)

            # optionally redraw orbit lines if toggled on (they are static, so only draw when toggled)
            if SHOW_ORBITS_FLAG:
                # orbits drawn once already; no need to re-draw every frame to save time.
                pass

        # Update screen once per loop for smoothness
        screen.update()
        frame += 1
        # small sleep to reduce CPU usage but keep animation smooth
        time.sleep(0.01)

# Start
try:
    main_loop()
except turtle.Terminator:
    # gracefully handle window close
    pass
