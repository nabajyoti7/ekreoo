import turtle
import math
import random

# Set up screen
screen = turtle.Screen()
screen.setup(800, 800)
screen.colormode(255)
screen.bgcolor('black')

t = turtle.Turtle()
t.hideturtle()
t.speed(0)
t.width(2)

# Draw color wheel to pick colors
def draw_color_wheel(radius=280):
    wheel_turtle = turtle.Turtle()
    wheel_turtle.hideturtle()
    wheel_turtle.speed(0)
    n = 360
    for i in range(n):
        wheel_turtle.penup()
        wheel_turtle.goto(0, 0)
        wheel_turtle.seth(i)
        wheel_turtle.pendown()
        r = int(128 + 127 * math.cos(math.radians(i)))
        g = int(128 + 127 * math.cos(math.radians(i - 120)))
        b = int(128 + 127 * math.cos(math.radians(i - 240)))
        wheel_turtle.pencolor(r, g, b)
        wheel_turtle.forward(radius)
    wheel_turtle.pencolor("white")
    wheel_turtle.penup()

draw_color_wheel()

positions = []
colors = []  # Store selected colors

# Get color under x, y position on wheel
def get_color(x, y):
    angle = math.degrees(math.atan2(y, x))
    angle = (angle + 360) % 360
    r = int(128 + 127 * math.cos(math.radians(angle)))
    g = int(128 + 127 * math.cos(math.radians(angle - 120)))
    b = int(128 + 127 * math.cos(math.radians(angle - 240)))
    return (r, g, b)

# Blend two RGB colors
def blend(c1, c2):
    return tuple((c1[i] + c2[i]) // 2 for i in range(3))

# Draw flower at a location with a blended color
def draw_flower(x, y, color):
    petal_count = 8
    petal_radius = 70
    t.penup()
    t.goto(x, y)
    t.pendown()
    t.color(color)
    for i in range(petal_count):
        t.penup()
        t.goto(x, y)
        t.pendown()
        t.setheading(i * 360/petal_count)
        t.circle(petal_radius, 60)
    t.penup()
    t.goto(x, y)
    t.dot(40, 'yellow')
    t.goto(0, 0)

def on_click(x, y):
    if len(colors) < 2:
        color = get_color(x, y)
        positions.append((x, y))
        colors.append(color)
        t.penup()
        t.goto(x, y)
        t.pendown()
        t.dot(30, color)
    if len(colors) == 2:
        mix_color = blend(colors[0], colors[1])
        mx = (positions[0][0] + positions[1][0]) // 2
        my = (positions[0][1] + positions[1][1]) // 2
        draw_flower(mx, my, mix_color)
        colors.clear()
        positions.clear()

screen.onscreenclick(on_click)
turtle.done()
