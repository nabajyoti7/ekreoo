import turtle
import random

# Set up the screen
screen = turtle.Screen()
screen.bgcolor("black")
screen.title("Colorful Turtle Spiral")

# Create the turtle
spiral = turtle.Turtle()
spiral.speed(0)
colors = ["red", "orange", "yellow", "green", "blue", "purple", "cyan"]

# Draw spiral pattern
for i in range(360):
    spiral.color(random.choice(colors))
    spiral.width(i % 10 + 1)
    spiral.forward(i * 2)
    spiral.right(121)

# Hide the turtle and keep the window open
spiral.hideturtle()
turtle.done()
