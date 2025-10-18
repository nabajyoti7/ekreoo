import tkinter as tk
from tkinter import colorchooser

def blend_colors(color1, color2):
    # Converts hex color to RGB tuple
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # Converts RGB tuple to hex color
    def rgb_to_hex(rgb_color):
        return '#%02x%02x%02x' % rgb_color

    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    blended = tuple((c1 + c2) // 2 for c1, c2 in zip(rgb1, rgb2))
    return rgb_to_hex(blended)

class ColorMixFlowerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Educational Color Mixer")

        self.selected_colors = [None, None]
        self.color_labels = []

        frame = tk.Frame(root)
        frame.pack(padx=10, pady=10)

        # Color palette buttons
        self.palette = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080']
        for i, color in enumerate(self.palette):
            btn = tk.Button(frame, bg=color, width=4, height=2,
                            command=lambda c=color, idx=i%2: self.select_color(c, idx))
            btn.grid(row=0, column=i, padx=3, pady=5)

        # Dynamic color display
        self.flower_canvas = tk.Canvas(root, width=200, height=200, bg='white')
        self.flower_canvas.pack(pady=10)

        # Buttons to choose first and second color and see output
        for i in range(2):
            lbl = tk.Label(root, text=f"Selected Color {i+1}: None", bg='white')
            lbl.pack()
            self.color_labels.append(lbl)

        self.mix_button = tk.Button(root, text="Mix Colors!", command=self.show_flower)
        self.mix_button.pack(pady=5)

        self.result_label = tk.Label(root, text="Blended Color: None", bg='white')
        self.result_label.pack()

    def select_color(self, color, idx):
        self.selected_colors[idx] = color
        self.color_labels[idx].config(text=f"Selected Color {idx+1}: {color}", bg=color)
        self.show_flower()

    def show_flower(self):
        if self.selected_colors[0] and self.selected_colors[1]:
            blended = blend_colors(self.selected_colors[0], self.selected_colors[1])
            self.result_label.config(text=f"Blended Color: {blended}", bg=blended)
            self.draw_flower(blended)
        else:
            self.result_label.config(text="Blended Color: None", bg='white')
            self.flower_canvas.delete("all")

    def draw_flower(self, color):
        self.flower_canvas.delete("all")
        # Draw simple flower petals
        x0, y0 = 100, 100
        for angle in range(0, 360, 60):
            x1 = x0 + 50 * tk.math.cos(tk.math.radians(angle))
            y1 = y0 + 50 * tk.math.sin(tk.math.radians(angle))
            self.flower_canvas.create_oval(x1-30, y1-30, x1+30, y1+30,
                                           fill=color, outline=color)
        # Draw center
        self.flower_canvas.create_oval(x0-25, y0-25, x0+25, y0+25, fill='yellow')

if __name__ == "__main__":
    root = tk.Tk()
    app = ColorMixFlowerApp(root)
    root.mainloop()
