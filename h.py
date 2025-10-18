import turtle
import colorsys

# Setup screen
screen = turtle.Screen()
screen.bgcolor("black")
screen.title("Creative Rainbow Spiral")

# Setup turtle
t = turtle.Turtle()
t.speed(0)
turtle.colormode(255)

# Generate rainbow colors
n = 36
h = 0
colors = []
for i in range(n):
    col = colorsys.hsv_to_rgb(h, 1, 1)
    colors.append((int(col[0]*255), int(col[1]*255), int(col[2]*255)))
    h += 1/n

# Draw spiral
t.width(2)
for i in range(360):
    t.pencolor(colors[i % n])
    t.forward(i*2)
    t.right(59)   # try changing this angle for wild effects
    t.circle(60)

turtle.done()
