import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, filedialog
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont
import io
import json

class MindMapTool:
    def __init__(self, root):
        self.root = root
        self.root.title("HackMap")

        # Modernes Design für Hacker-Look
        self.dark_mode = True
        self.bg_color = "#1e1e1e"  # Dunkles Grau für Hintergrund
        self.node_color = "#00ff00"  # Neon-Grün für Knoten
        self.text_color = "#000000"  # Neon-Grün für Text

        # Initialisieren des Canvas
        self.canvas = tk.Canvas(root, bg=self.bg_color, width=800, height=600, bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.nodes = []
        self.lines = []
        self.groups = []
        self.selected_node = None
        self.drawing_line = False
        self.start_x = None
        self.start_y = None
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0

        # Undo/Redo Stacks
        self.undo_stack = []
        self.redo_stack = []

        # Menüleiste im Hacker-Look
        self.menu_bar = tk.Menu(root, bg="#2d2d2d", fg="#00ff00", activebackground="#00ff00", activeforeground="#2d2d2d")
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#1e1e1e", fg="#00ff00", activebackground="#00ff00", activeforeground="#1e1e1e")
        self.file_menu.add_command(label="Neu", command=self.new_map)
        self.file_menu.add_command(label="Speichern", command=self.save_map)
        self.file_menu.add_command(label="Laden", command=self.load_map)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export als PDF", command=self.export_as_pdf)
        self.file_menu.add_command(label="Export als Bild", command=self.export_as_image)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Beenden", command=root.quit)
        self.menu_bar.add_cascade(label="Datei", menu=self.file_menu)

        self.view_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#1e1e1e", fg="#00ff00", activebackground="#00ff00", activeforeground="#1e1e1e")
        self.view_menu.add_command(label="Dark Mode", command=self.toggle_dark_mode)
        self.view_menu.add_command(label="Zoom In", command=self.zoom_in)
        self.view_menu.add_command(label="Zoom Out", command=self.zoom_out)
        self.view_menu.add_command(label="Pan", command=self.start_pan_mode)
        self.view_menu.add_command(label="Automatisches Layout", command=self.apply_auto_layout)
        self.menu_bar.add_cascade(label="Ansicht", menu=self.view_menu)

        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#1e1e1e", fg="#00ff00", activebackground="#00ff00", activeforeground="#1e1e1e")
        self.edit_menu.add_command(label="Undo", command=self.undo)
        self.edit_menu.add_command(label="Redo", command=self.redo)
        self.menu_bar.add_cascade(label="Bearbeiten", menu=self.edit_menu)

        root.config(menu=self.menu_bar)

        # Binden von Events
        self.canvas.bind("<Button-1>", self.add_node)
        self.canvas.bind("<B1-Motion>", self.move_node_or_draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.end_move_node_or_draw_line)
        self.canvas.bind("<Double-1>", self.edit_node)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<MouseWheel>", self.zoom)

        # Kontextmenü für Knoten
        self.context_menu = tk.Menu(root, tearoff=0, bg="#1e1e1e", fg="#00ff00", activebackground="#00ff00", activeforeground="#1e1e1e")
        self.context_menu.add_command(label="Bearbeiten", command=self.edit_node)
        self.context_menu.add_command(label="Löschen", command=self.delete_node)
        self.context_menu.add_command(label="Farbe ändern", command=self.change_color)
        self.context_menu.add_command(label="Text formatieren", command=self.format_text)
        self.context_menu.add_command(label="Gruppieren", command=self.group_nodes)
        self.context_menu.add_command(label="Ungruppieren", command=self.ungroup_nodes)

    def new_map(self):
        self.undo_stack.append(('new_map', []))  # Store the state before clearing
        self.canvas.delete("all")
        self.nodes.clear()
        self.lines.clear()
        self.groups.clear()
        self.redo_stack.clear()

    def save_map(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        
        map_data = []
        for node, text in self.nodes:
            x1, y1, x2, y2 = self.canvas.coords(node)
            node_data = {
                "x": (x1 + x2) / 2,
                "y": (y1 + y2) / 2,
                "text": self.canvas.itemcget(text, "text"),
                "color": self.canvas.itemcget(node, "fill")
            }
            map_data.append(node_data)
        
        with open(file_path, 'w') as f:
            json.dump(map_data, f)
        messagebox.showinfo("Erfolg", "Mind-Map erfolgreich gespeichert!")

    def load_map(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        
        with open(file_path, 'r') as f:
            map_data = json.load(f)

        self.new_map()
        for node_data in map_data:
            x, y = node_data["x"], node_data["y"]
            node = self.canvas.create_oval(x-30, y-30, x+30, y+30, fill=node_data["color"], outline=self.text_color)
            text = self.canvas.create_text(x, y, text=node_data["text"], font=("Consolas", 12), fill=self.text_color)
            self.nodes.append((node, text))

    def add_node(self, event):
        if self.drawing_line:
            return
        x, y = event.x, event.y
        node = self.canvas.create_oval(x-30, y-30, x+30, y+30, fill=self.node_color, outline=self.text_color)
        text = self.canvas.create_text(x, y, text="Idee", font=("Consolas", 12), fill=self.text_color)
        self.nodes.append((node, text))
        self.select_node(event)
        self.undo_stack.append(('add_node', (node, text)))

    def move_node_or_draw_line(self, event):
        if self.drawing_line:
            self.canvas.delete("line_temp")
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill=self.text_color, tags="line_temp")
        elif self.selected_node:
            x, y = event.x, event.y
            self.canvas.coords(self.selected_node[0], x-30, y-30, x+30, y+30)
            self.canvas.coords(self.selected_node[1], x, y)

    def end_move_node_or_draw_line(self, event):
        if self.drawing_line:
            x1, y1 = self.start_x, self.start_y
            x2, y2 = event.x, event.y
            self.canvas.create_line(x1, y1, x2, y2, fill=self.text_color)
            self.lines.append((x1, y1, x2, y2))
            self.drawing_line = False
        else:
            self.deselect_node(event)

    def start_pan_mode(self):
        self.last_x = self.canvas.winfo_pointerx()
        self.last_y = self.canvas.winfo_pointery()
        self.canvas.bind("<B1-Motion>", self.pan_canvas)

    def pan_canvas(self, event):
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        self.canvas.move("all", dx, dy)
        self.last_x = event.x
        self.last_y = event.y

    def zoom(self, event):
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_factor *= zoom_factor
        self.canvas.scale("all", event.x, event.y, zoom_factor, zoom_factor)

    def zoom_in(self):
        self.canvas.scale("all", 0, 0, 1.2, 1.2)

    def zoom_out(self):
        self.canvas.scale("all", 0, 0, 0.8, 0.8)

    def apply_auto_layout(self):
        # Platzhalter für automatische Layout-Funktionalität
        pass

    def export_as_pdf(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return
        
        c = canvas.Canvas(file_path, pagesize=letter)
        
        for node, text in self.nodes:
            x1, y1, x2, y2 = self.canvas.coords(node)
            x, y = (x1 + x2) / 2, (y1 + y2) / 2
            node_text = self.canvas.itemcget(text, "text")
            color = self.canvas.itemcget(node, "fill")
            
            c.setFillColor(color)
            c.circle(x, 750 - y, 30, stroke=1, fill=1)
            c.setFillColor("black")
            c.drawCentredString(x, 750 - y + 5, node_text)

        c.showPage()
        c.save()
        messagebox.showinfo("Erfolg", "Mind-Map erfolgreich als PDF gespeichert!")

    def export_as_image(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not file_path:
            return

        # Erstellen eines Bildes mit PIL
        ps = self.canvas.postscript(colormode='color')
        img = Image.open(io.BytesIO(ps.encode('utf-8')))
        img.save(file_path)
        messagebox.showinfo("Erfolg", "Mind-Map erfolgreich als Bild gespeichert!")

    def format_text(self):
        if self.selected_node:
            text = self.selected_node[1]
            formats = ["bold", "italic", "underline"]
            format_choice = simpledialog.askstring("Text formatieren", "Wählen Sie eine Formatierung: " + ", ".join(formats))
            if format_choice in formats:
                current_font = self.canvas.itemcget(text, "font")
                font_styles = {
                    "bold": "bold",
                    "italic": "italic",
                    "underline": "underline"
                }
                new_font = f"Consolas 12 {font_styles.get(format_choice, '')}"
                self.canvas.itemconfig(text, font=new_font)

    def group_nodes(self):
        if self.selected_node:
            group = [self.selected_node]
            for node in self.nodes:
                if node != self.selected_node:
                    coords = self.canvas.coords(node[0])
                    if (coords[0] < self.canvas.coords(self.selected_node[0])[2] and
                        coords[2] > self.canvas.coords(self.selected_node[0])[0] and
                        coords[1] < self.canvas.coords(self.selected_node[0])[3] and
                        coords[3] > self.canvas.coords(self.selected_node[0])[1]):
                        group.append(node)
            if group:
                self.groups.append(group)
                self.selected_node = None
                messagebox.showinfo("Erfolg", "Knoten gruppiert!")

    def ungroup_nodes(self):
        if self.groups:
            self.groups.pop()
            messagebox.showinfo("Erfolg", "Letzte Gruppe aufgelöst!")

    def undo(self):
        if self.undo_stack:
            action = self.undo_stack.pop()
            self.redo_stack.append(action)
            self.perform_undo(action)

    def redo(self):
        if self.redo_stack:
            action = self.redo_stack.pop()
            self.undo_stack.append(action)
            self.perform_redo(action)

    def perform_undo(self, action):
        if action[0] == 'add_node':
            node, text = action[1]
            self.canvas.delete(node)
            self.canvas.delete(text)
            self.nodes.remove((node, text))
        elif action[0] == 'new_map':
            self.canvas.delete("all")
            for node, text in action[1]:
                self.canvas.create_oval(*self.canvas.coords(node), fill=self.canvas.itemcget(node, "fill"))
                self.canvas.create_text(*self.canvas.coords(text), text=self.canvas.itemcget(text, "text"))
            self.nodes = action[1]

    def perform_redo(self, action):
        if action[0] == 'add_node':
            node, text = action[1]
            self.nodes.append((node, text))
            self.canvas.create_oval(*self.canvas.coords(node), fill=self.canvas.itemcget(node, "fill"))
            self.canvas.create_text(*self.canvas.coords(text), text=self.canvas.itemcget(text, "text"))
        elif action[0] == 'new_map':
            self.new_map()

    def search_nodes(self, query):
        for node, text in self.nodes:
            if query.lower() in self.canvas.itemcget(text, "text").lower():
                self.canvas.itemconfig(text, fill="red")
            else:
                self.canvas.itemconfig(text, fill=self.text_color)

    def show_context_menu(self, event):
        self.select_node(event)
        if self.selected_node:
            self.context_menu.post(event.x_root, event.y_root)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.bg_color = "#1e1e1e" if self.dark_mode else "white"
        self.node_color = "#00ff00" if self.dark_mode else "lightblue"
        self.text_color = "#00ff00" if self.dark_mode else "black"

        self.canvas.config(bg=self.bg_color)
        for node, text in self.nodes:
            self.canvas.itemconfig(node, fill=self.node_color, outline=self.text_color)
            self.canvas.itemconfig(text, fill=self.text_color)

    def select_node(self, event):
        for node, text in self.nodes:
            coords = self.canvas.coords(node)
            if coords[0] <= event.x <= coords[2] and coords[1] <= event.y <= coords[3]:
                self.selected_node = (node, text)
                break

    def deselect_node(self, event):
        self.selected_node = None

    def edit_node(self, event=None):
        if self.selected_node:
            node, text = self.selected_node
            new_text = simpledialog.askstring("Text bearbeiten", "Neuer Text:", initialvalue=self.canvas.itemcget(text, "text"))
            if new_text:
                self.canvas.itemconfig(text, text=new_text)
                self.undo_stack.append(('edit_node', (node, text, self.canvas.itemcget(text, "text"))))

    def delete_node(self):
        if self.selected_node:
            node, text = self.selected_node
            self.canvas.delete(node)
            self.canvas.delete(text)
            self.nodes.remove(self.selected_node)
            self.selected_node = None
            self.undo_stack.append(('delete_node', (node, text)))

    def change_color(self):
        if self.selected_node:
            color = colorchooser.askcolor(title="Farbe auswählen")[1]
            if color:
                node, text = self.selected_node
                self.canvas.itemconfig(node, fill=color)
                self.undo_stack.append(('change_color', (node, self.canvas.itemcget(node, "fill"))))

if __name__ == "__main__":
    root = tk.Tk()
    app = MindMapTool(root)
    root.mainloop()
