import tkinter as tk

from tkinter import colorchooser
from tkinter.colorchooser import askcolor




def bresenham_line(x0, y0, x1, y1):
    points = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return points


class PixelEditor:
    def __init__(self, master, cols=32, rows=32, zoom=16):
        self.current_tool = None
        self.mirror_button = None
        self.color_preview_temp = "#8ba334"
        self.master = master
        self.cols = cols
        self.rows = rows
        self.zoom = zoom  # fator de zoom

        # self.zoom = pixel_size
        self.current_color = "#000000"
        self.bg_color = "#ffffff"
        self.tool = "pencil"

        # Palette
        self.palette = ["#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff"]
        self.selected_color = self.palette[0]
        self.palette_buttons = []  # lista dos botões da paleta

        self.show_grid = False
        self.show_checker = True
        self.pixels = [[None for _ in range(cols)] for _ in range(rows)]
        self.undo_stack = []
        self.create_ui()
        self.mirror_mode = "OFF" # OFF, HORIZONTAL, VERTICAL, BOTH


        self.mirror = False

        self.rect_start = None  # Ponto inicial do retângulo
        self.temp_rect_id = None  # ID do retângulo temporário no canvas
        self.circle_start = None  # Ponto inicial do círculo
        self.temp_circle_id = None  # ID do círculo temporário no canvas

        # =============== #
        self.drawing = False
        self.draw_grid()


    def create_ui(self):
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(fill="both", expand=True)

        # Toolbar esquerda
        self.controls = tk.Frame(self.main_frame, width=200)
        self.controls.pack(side="left", fill="y", padx=4, pady=4)

        # Barra de ferramentas
        self.tools_frame = tk.Frame(self.controls)
        self.tools_frame.pack(pady=4, fill='x')

        # btFerramentas
        self.tool_buttons = {}
        for name, label in [("pencil", "✏️ Lápis"), ("eraser", "🩹 Borracha"),
                            ("fill", "🪣 Balde"), ("rectangle", "▭ Retângulo"),
                            ("circle", "◯ Círculo"), ("line", "📏 Linha"), ("picker", "🎨 Conta-gotas")]:
            btn = tk.Button(self.tools_frame, text=label, command=lambda n=name: self.set_tool(n))
            btn.pack(fill="x", pady=2)
            self.tool_buttons[name] = btn

        self.zoom_frame = tk.Frame(self.controls)
        self.zoom_frame.pack(pady=2)

        tk.Button(self.zoom_frame, text="🔍 +", command=self.zoom_in).pack(side="left", pady=2, fill="x")
        tk.Button(self.zoom_frame, text="🔍 -", command=self.zoom_out).pack(side="left",pady=2, fill="x")

        tk.Button(self.controls, text="Grade on/off", command=self.toggle_grid).pack(pady=4, fill='x')
        tk.Button(self.controls, text="Fundo xadrez on/off", command=self.toggle_checker).pack(pady=4, fill='x')
        tk.Button(self.controls, text="Novo", command=self.clear).pack(pady=4, fill='x')
        tk.Button(self.controls, text="Desfazer", command=self.undo).pack(pady=4, fill='x')
        tk.Button(self.controls, text="Exportar PNG", command=self.export).pack(pady=4, fill='x')

        # BINDINGS-atalhos
        self.master.bind("g", lambda e: self.toggle_grid())
        self.master.bind("c", lambda e: self.toggle_checker())
        self.master.bind("<Control-z>", lambda e: self.undo())  # Ctrl+Z
        self.master.bind("<Control-m>", lambda e: self.set_mirror("OFF"))
        self.master.bind("<Control-plus>", lambda e: self.zoom_in())
        self.master.bind("<Control-minus>", lambda e: self.zoom_out())
        self.master.bind("<Control-Shift-A>", lambda e: self.add_current_color_to_palette())

        # Canvas (centro)
        self.canvas = tk.Canvas(self.main_frame, width=self.cols * self.zoom,
                                height=self.rows * self.zoom, bg=self.bg_color)
        self.canvas.pack(side="left", padx=4, pady=4, expand=True)

        self.canvas.bind("<Alt-Button-1>", self.alt_picker)

        self.canvas.bind("<Button-1>", self.start_action)
        self.canvas.bind("<B1-Motion>", self.draw_action)
        self.canvas.bind("<ButtonRelease-1>", self.stop_action)

        self.canvas.bind("<Button-3>", self.right_click)
        self.canvas.bind("<B3-Motion>", self.right_drag)

        self.canvas.bind("<ButtonRelease-3>", self.stop_action)

        # Frame direito para paleta e futuros controles
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side="left", fill="y", padx=4, pady=4)

        # Botão para adicionar cores
        tk.Button(self.right_frame, text="Adicionar Cor", command=self.add_color).pack(pady=4, fill='x')

        # Paleta de cores
        self.palette_frame = tk.Frame(self.right_frame)
        self.palette_frame.pack(pady=4)

        self.max_colors = 15

        self.draw_palette()

        tk.Button(self.right_frame, text="☀️ Clarear", command=self.lighten_color).pack(pady=2, fill='x')
        tk.Button(self.right_frame, text="🌑 Escurecer", command=self.darken_color).pack(pady=2, fill='x')


        # Espelho
        # LbEspelho
        self.lb_mirror = tk.Label(self.right_frame, text="Mirror")
        self.lb_mirror.pack(pady=2)
        # FRAME
        self.mirror_frame = tk.Frame(self.right_frame)
        self.mirror_frame.pack()
        # Botões de mirror no right_frame
        self.mirror_h_button = tk.Button(self.mirror_frame, text="H", width=8,
                                         command=lambda: self.set_mirror("HORIZONTAL"))
        self.mirror_h_button.pack(side="left", pady=2, fill="x")

        self.mirror_v_button = tk.Button(self.mirror_frame, text="V", width=8,
                                         command=lambda: self.set_mirror("VERTICAL"))
        self.mirror_v_button.pack(side="left", pady=2, fill="x")

        self.mirror_both_button = tk.Button(self.mirror_frame, text="H+V", width=8,
                                            command=lambda: self.set_mirror("BOTH"))
        self.mirror_both_button.pack(side="left", pady=2,)

    # Alt+click = picker
    def alt_picker(self, event):
        row, col = event.y // self.zoom, event.x // self.zoom
        if 0 <= row < self.rows and 0 <= col < self.cols:
            color = self.pixels[row][col]
            if color:  # só altera se houver uma cor
                self.set_color(color)

    # ZOOM
    # Ajuste na função draw_pixel
    def draw_pixel(self, row, col, color):
        """Desenha um único pixel na tela, considerando zoom e fundo quadriculado."""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return

        x0, y0 = col * self.zoom, row * self.zoom
        x1, y1 = x0 + self.zoom, y0 + self.zoom

        if color is None:
            # Pixel transparente → desenha o fundo quadriculado
            fill_color = "#cccccc" if (row + col) % 2 == 0 else "#eeeeee"
        else:
            fill_color = color

        self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill_color, width=0)

    def zoom_in(self):
        self.zoom = min(64, self.zoom + 1)  # incremento menor
        self.redraw_canvas()

    def zoom_out(self):
        self.zoom = max(1, self.zoom - 1)
        self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.config(width=self.cols * self.zoom, height=self.rows * self.zoom)
        self.canvas.delete("all")
        self.draw_grid()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.pixels[r][c]:
                    self.draw_pixel(r, c, self.pixels[r][c])

    # ESPELHO
    def set_mirror(self, mode):
        # Se clicar no botão que já está ativo, desativa o espelho
        if self.mirror_mode == mode:
            self.mirror_mode = "OFF"
        else:
            self.mirror_mode = mode

        # Atualiza a cor dos botões para indicar o ativo
        self.mirror_h_button.config(bg="#a0c0ff" if self.mirror_mode == "HORIZONTAL" else "SystemButtonFace")
        self.mirror_v_button.config(bg="#a0c0ff" if self.mirror_mode == "VERTICAL" else "SystemButtonFace")
        self.mirror_both_button.config(bg="#a0c0ff" if self.mirror_mode == "BOTH" else "SystemButtonFace")

    def draw_palette(self):
        for w in self.palette_frame.winfo_children():
            w.destroy()

        cols = 5
        for i in range(self.max_colors):
            row_idx, col_idx = divmod(i, cols)
            color = self.palette[i] if i < len(self.palette) else None

            if color:
                btn = tk.Button(
                    self.palette_frame,
                    bg=color,
                    width=3,
                    height=1,
                    relief="solid",
                    command=lambda col=color: self.select_color(col)
                )
                # clique com botão direito para remover
                btn.bind("<Button-3>", lambda e, idx=i: self.remove_color(idx))

                if color == getattr(self, "selected_color", None):
                    btn.config(highlightthickness=8, highlightbackground="black", bd=2)
                else:
                    btn.config(highlightthickness=1, highlightbackground="gray", bd=1)
                btn.grid(row=row_idx, column=col_idx, padx=3, pady=3)
            else:
                # slot vazio
                lbl = tk.Label(self.palette_frame, bg="#e0e0e0", width=3, height=1, relief="ridge", bd=1)
                lbl.grid(row=row_idx, column=col_idx, padx=3, pady=3)

    def select_color(self, color):
        self.current_color = color
        self.selected_color = color
        self.draw_palette()

    def update_palette_indicator(self):
        for btn in self.palette_buttons:
            if btn["bg"] == self.selected_color:
                btn.config(highlightthickness=8, highlightbackground="black")
            else:
                btn.config(highlightthickness=1, highlightbackground="gray")


    def add_color(self):
        if len(self.palette) >= self.max_colors:
            print("Paleta cheia! Remova uma cor antes de adicionar.")
            return

        color = askcolor(title="Escolher Cor")[1]  # retorna cor no formato #RRGGBB
        if color:
            self.palette.append(color)
            self.select_color(color)

    def remove_color(self, index):
        if index < len(self.palette):
            removed_color = self.palette.pop(index)
            # Se a cor removida era a selecionada, desmarcar
            if removed_color == self.selected_color:
                self.selected_color = None
                self.current_color = None
            self.draw_palette()

    def set_color(self, color):
        self.current_color = color
        self.selected_color = color
        self.update_palette_indicator()

    def update_tool_buttons(self):
        for name, btn in self.tool_buttons.items():
            if name == self.tool:
                btn.config(relief=tk.SUNKEN, bg="#a0c0ff")
            else:
                btn.config(relief=tk.RAISED, bg="SystemButtonFace")

    def set_tool(self, tool):
        self.tool = tool
        self.update_tool_buttons()

    def draw_grid(self):
        self.canvas.delete("all")
        ps = self.zoom

        # Fundo e checker
        if self.show_checker:
            for r in range(self.rows):
                for c in range(self.cols):
                    if (r + c) % 2 == 0:
                        x0, y0 = c * ps, r * ps
                        x1, y1 = x0 + ps, y0 + ps
                        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#dddddd", outline="")

        # Desenha pixels
        for r in range(self.rows):
            for c in range(self.cols):
                color = self.pixels[r][c]
                if color:
                    x0, y0 = c * ps, r * ps
                    x1, y1 = x0 + ps, y0 + ps
                    self.canvas.create_rectangle(x0, y0, x1, y1, fill=color,
                                                 outline="" if not self.show_grid else "#c0c0c0")
        # Linha do mirror
        if getattr(self, "mirror", False):
            self.canvas.create_line(self.cols * ps // 2, 0, self.cols * ps // 2, self.rows * ps,
                                    fill="red", width=2)

        # Linha(s) do mirror
        if self.mirror_mode in ("HORIZONTAL", "BOTH"):
            self.canvas.create_line(self.cols * self.zoom // 2, 0,
                                    self.cols * self.zoom // 2, self.rows * self.zoom,
                                    fill="red", width=2)
        if self.mirror_mode in ("VERTICAL", "BOTH"):
            self.canvas.create_line(0, self.rows * self.zoom // 2,
                                    self.cols * self.zoom, self.rows * self.zoom // 2,
                                    fill="red", width=2)



    # -----------------------------
    # Right Click Handlers atualizados
    # -----------------------------
    def right_click(self, event):
        self.drawing = True
        self.current_stroke = []  # inicia um novo stroke
        self.erase_pixel(event.y // self.zoom, event.x // self.zoom)

    def right_drag(self, event):
        if not self.drawing:
            return
        self.erase_pixel(event.y // self.zoom, event.x // self.zoom)


    # -----------------------------
    # Mirror Helper
    # -----------------------------
    # ---------------------------------
    # Ajuste em apply_mirror para stroke contínuo
    # ---------------------------------
    def apply_mirror(self, row, col, stroke_list=None):
        # Mirror horizontal
        if self.mirror_mode in ("HORIZONTAL", "BOTH"):
            mc = self.cols - 1 - col
            if mc != col:
                old_color = self.pixels[row][mc]
                self.pixels[row][mc] = self.current_color if self.tool != "eraser" else None
                self.draw_pixel(row, mc, self.pixels[row][mc])
                if stroke_list is not None:
                    stroke_list.append((row, mc, old_color))

        # Mirror vertical
        if self.mirror_mode in ("VERTICAL", "BOTH"):
            mr = self.rows - 1 - row
            if mr != row:
                old_color = self.pixels[mr][col]
                self.pixels[mr][col] = self.current_color if self.tool != "eraser" else None
                self.draw_pixel(mr, col, self.pixels[mr][col])
                if stroke_list is not None:
                    stroke_list.append((mr, col, old_color))

        # Mirror ambos
        if self.mirror_mode == "BOTH":
            mr = self.rows - 1 - row
            mc = self.cols - 1 - col
            if mr != row or mc != col:
                old_color = self.pixels[mr][mc]
                self.pixels[mr][mc] = self.current_color if self.tool != "eraser" else None
                self.draw_pixel(mr, mc, self.pixels[mr][mc])
                if stroke_list is not None:
                    stroke_list.append((mr, mc, old_color))

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.draw_grid()

    def toggle_checker(self):
        self.show_checker = not self.show_checker
        self.draw_grid()

    def clear(self):
        self.pixels = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.draw_grid()

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.current_color = color

    def save_state(self):
        # Faz uma cópia profunda da matriz de pixeis
        self.undo_stack.append([row[:] for row in self.pixels])
        # Limitar o tamanho do stack se quiser
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            return  # nada a desfazer

        last_action = self.undo_stack.pop()

        for r, c, old_color in last_action:
            # Restaura a matriz de pixels
            self.pixels[r][c] = old_color
            # Atualiza o canvas
            self.draw_pixel(r, c, old_color)

        # Limpa preview se houver
        self.canvas.delete("temp_shape")

    def export(self):
        from PIL import Image
        img = Image.new("RGBA", (self.cols, self.rows), (0, 0, 0, 0))  # fundo transparente
        for r in range(self.rows):
            for c in range(self.cols):
                color = self.pixels[r][c]
                if color:
                    r_c = int(color[1:3], 16)
                    g_c = int(color[3:5], 16)
                    b_c = int(color[5:7], 16)
                    img.putpixel((c, r), (r_c, g_c, b_c, 255))  # pixel opaco
        img.save("pixel_art.png")
        print("Exportado como pixel_art.png (com fundo transparente)")

    def hex_to_rgba(self, hex_color):
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        return tuple(int(hex_color[i:i+lv//3], 16) for i in range(0, lv, lv//3)) + (255,)

    # -----------------------------
    # Mouse Handlers
    # -----------------------------

    def start_action(self, event):
        self.drawing = True
        row, col = event.y // self.zoom, event.x // self.zoom
        self.start_row, self.start_col = row, col

        if self.tool == "pencil":
            self.current_stroke = []
            self.paint_pixel(row, col)
        elif self.tool == "eraser":
            self.current_stroke = []
            self.erase_pixel(row, col)
        elif self.tool in ("rectangle", "circle", "line"):
            # preview será tratado no draw_action
            pass
        elif self.tool == "fill":
            self.current_stroke = []
            self.fill_pixel(row, col)
        elif self.tool == "picker":
            if 0 <= row < self.rows and 0 <= col < self.cols:
                color = self.pixels[row][col]
                if color:
                    self.set_color(color)  # seleciona a cor no editor

    def fill_pixel(self, row, col):
        target_color = self.pixels[row][col]
        if target_color == self.current_color:
            return

        pixels_to_fill = [(row, col)]
        filled = []

        while pixels_to_fill:
            r, c = pixels_to_fill.pop()
            if 0 <= r < self.rows and 0 <= c < self.cols:
                if self.pixels[r][c] == target_color:
                    old_color = self.pixels[r][c]
                    self.pixels[r][c] = self.current_color
                    self.draw_pixel(r, c, self.current_color)
                    filled.append((r, c, old_color))

                    # Mirror
                    self.apply_mirror(r, c)

                    # Adiciona vizinhos
                    pixels_to_fill.extend([
                        (r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)
                    ])

        if filled:
            self.undo_stack.append(filled)

    # ---------------------------------
    # paint_pixel e erase_pixel atualizados
    # ---------------------------------
    def paint_pixel(self, row, col):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            old_color = self.pixels[row][col]
            if old_color != self.current_color:
                self.pixels[row][col] = self.current_color
                self.draw_pixel(row, col, self.current_color)
                self.current_stroke.append((row, col, old_color))

                # Aplicar mirror
                self.apply_mirror(row, col, stroke_list=self.current_stroke)

    def erase_pixel(self, row, col):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            old_color = self.pixels[row][col]
            if old_color is not None:
                self.pixels[row][col] = None
                self.draw_pixel(row, col, None)
                self.current_stroke.append((row, col, old_color))

                # Aplicar mirror
                self.apply_mirror(row, col, stroke_list=self.current_stroke)

    def draw_action(self, event):
        if not self.drawing:
            return
        row, col = event.y // self.zoom, event.x // self.zoom

        if self.tool == "pencil":
            self.paint_pixel(row, col)
        elif self.tool == "eraser":
            self.erase_pixel(row, col)
        elif self.tool == "line":
            self.canvas.delete("temp_shape")
            self.draw_line_generic(self.start_row, self.start_col, row, col, preview=True)
        elif self.tool == "rectangle":
            self.canvas.delete("temp_shape")
            self.draw_rectangle_generic(self.start_row, self.start_col, row, col, fill=False, preview=True)
        elif self.tool == "circle":
            self.canvas.delete("temp_shape")
            self.draw_circle_generic(self.start_row, self.start_col, row, col, fill=False, preview=True)

    # ---------------------------------
    # stop_action atualizado
    # ---------------------------------
    def stop_action(self, event):
        if not self.drawing:
            return
        self.drawing = False
        row, col = event.y // self.zoom, event.x // self.zoom

        # Apaga o preview ao finalizar
        self.canvas.delete("temp_shape")

        if self.tool in ("pencil", "eraser", "fill") or event.num == 3:  # botão direito também
            if hasattr(self, "current_stroke") and self.current_stroke:
                self.undo_stack.append(self.current_stroke)
                self.current_stroke = []

        elif self.tool == "rectangle":
            self.draw_rectangle_generic(self.start_row, self.start_col, row, col, fill=False, preview=False)
        elif self.tool == "circle":
            self.draw_circle_generic(self.start_row, self.start_col, row, col, fill=False, preview=False)
        elif self.tool == "line":
            self.draw_line_generic(self.start_row, self.start_col, row, col, preview=False)

        self.start_row, self.start_col = None, None

    def draw_rectangle_generic(self, start_row, start_col, end_row, end_col, fill=True, preview=False):
        r0, r1 = min(start_row, end_row), max(start_row, end_row)
        c0, c1 = min(start_col, end_col), max(start_col, end_col)

        action_pixels = []
        pixels_set = set()

        def draw_pixel_safe(r, c):
            if 0 <= r < self.rows and 0 <= c < self.cols:
                key = (r, c)
                if key not in pixels_set:
                    old_color = self.pixels[r][c]
                    self.pixels[r][c] = self.current_color
                    action_pixels.append((r, c, old_color))
                    self.draw_pixel(r, c, self.current_color)
                    pixels_set.add(key)

        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if fill or r in (r0, r1) or c in (c0, c1):
                    if preview:
                        x0, y0 = c * self.zoom, r * self.zoom
                        x1, y1 = x0 + self.zoom, y0 + self.zoom
                        self._draw_preview_pixel(r, c)
                    else:
                        draw_pixel_safe(r, c)

                        # Mirrors
                        if self.mirror_mode in ("HORIZONTAL", "BOTH"):
                            draw_pixel_safe(r, self.cols - 1 - c)
                        if self.mirror_mode in ("VERTICAL", "BOTH"):
                            draw_pixel_safe(self.rows - 1 - r, c)
                        if self.mirror_mode == "BOTH":
                            draw_pixel_safe(self.rows - 1 - r, self.cols - 1 - c)

        if not preview and action_pixels:
            self.undo_stack.append(action_pixels)

    # ----------------------------
    # draw_temp_circle (preview)
    # ----------------------------
    def draw_circle_generic(self, start_row, start_col, end_row, end_col, fill=True, preview=False):
        """
        Desenha ou faz preview de um círculo/ellipse.

        preview=True -> desenha no canvas como preview (tag 'temp_shape')
        preview=False -> desenha de fato e atualiza pixels/undo
        """

        if preview:
            self.canvas.delete("temp_shape")

        # Determina o retângulo que envolve o círculo
        r0, r1 = min(start_row, end_row), max(start_row, end_row)
        c0, c1 = min(start_col, end_col), max(start_col, end_col)

        rx = max(1, (c1 - c0) // 2)
        ry = max(1, (r1 - r0) // 2)

        cx = c0 + rx
        cy = r0 + ry

        action_pixels = []  # só usado se preview=False
        pixels_set = set()  # para evitar duplicatas

        # Função auxiliar para desenhar um pixel e registrar no undo
        def draw_pixel_safe(r, c):
            if 0 <= r < self.rows and 0 <= c < self.cols:
                key = (r, c)
                if key not in pixels_set:
                    old_color = self.pixels[r][c]
                    self.pixels[r][c] = self.current_color
                    action_pixels.append((r, c, old_color))
                    self.draw_pixel(r, c, self.current_color)
                    pixels_set.add(key)

        # Bresenham adaptado para elipse
        x = 0
        y = ry
        rx_sq = rx * rx
        ry_sq = ry * ry
        dx = 2 * ry_sq * x
        dy = 2 * rx_sq * y

        # Região 1
        d1 = ry_sq - (rx_sq * ry) + (0.25 * rx_sq)
        while dx < dy:
            points = [
                (cy + y, cx + x),
                (cy + y, cx - x),
                (cy - y, cx + x),
                (cy - y, cx - x)
            ]
            for r, c in points:
                if preview:
                    x0, y0 = c * self.zoom, r * self.zoom
                    x1, y1 = x0 + self.zoom, y0 + self.zoom
                    self._draw_preview_pixel(r, c)
                else:
                    draw_pixel_safe(r, c)

                    # Mirrors
                    if self.mirror_mode in ("HORIZONTAL", "BOTH"):
                        draw_pixel_safe(r, self.cols - 1 - c)
                    if self.mirror_mode in ("VERTICAL", "BOTH"):
                        draw_pixel_safe(self.rows - 1 - r, c)
                    if self.mirror_mode == "BOTH":
                        draw_pixel_safe(self.rows - 1 - r, self.cols - 1 - c)

            if d1 < 0:
                x += 1
                dx += 2 * ry_sq
                d1 += dx + ry_sq
            else:
                x += 1
                y -= 1
                dx += 2 * ry_sq
                dy -= 2 * rx_sq
                d1 += dx - dy + ry_sq

        # Região 2
        d2 = (ry_sq) * ((x + 0.5) ** 2) + (rx_sq) * ((y - 1) ** 2) - (rx_sq * ry_sq)
        while y >= 0:
            points = [
                (cy + y, cx + x),
                (cy + y, cx - x),
                (cy - y, cx + x),
                (cy - y, cx - x)
            ]
            for r, c in points:
                if preview:
                    x0, y0 = c * self.zoom, r * self.zoom
                    x1, y1 = x0 + self.zoom, y0 + self.zoom
                    self._draw_preview_pixel(r, c)
                else:
                    draw_pixel_safe(r, c)

                    # Mirrors
                    if self.mirror_mode in ("HORIZONTAL", "BOTH"):
                        draw_pixel_safe(r, self.cols - 1 - c)
                    if self.mirror_mode in ("VERTICAL", "BOTH"):
                        draw_pixel_safe(self.rows - 1 - r, c)
                    if self.mirror_mode == "BOTH":
                        draw_pixel_safe(self.rows - 1 - r, self.cols - 1 - c)

            if d2 > 0:
                y -= 1
                dy -= 2 * rx_sq
                d2 += rx_sq - dy
            else:
                y -= 1
                x += 1
                dx += 2 * ry_sq
                dy -= 2 * rx_sq
                d2 += dx - dy + rx_sq

        if not preview and action_pixels:
            self.undo_stack.append(action_pixels)

    def drag_action(self, event):
        row, col = event.y // self.zoom, event.x // self.zoom

        if self.current_tool == "LINE":
            self.draw_temp_line(event)

        elif self.current_tool == "RECTANGLE":
            self.draw_temp_rectangle(event)

        elif self.current_tool == "CIRCLE":
            self.draw_temp_circle(event)

        elif self.current_tool == "PENCIL":
            self.paint_pixel(row, col)

        elif self.current_tool == "ERASER":
            self.erase_pixel(row, col)

    def adjust_color(self, hex_color, factor, lighten=False):
        """ Clareia ou escurece a cor """
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        if lighten:
            # mistura a cor com o branco
            r = int(r + (255 - r) * (factor - 1))
            g = int(g + (255 - g) * (factor - 1))
            b = int(b + (255 - b) * (factor - 1))
        else:
            # escurece multiplicando
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)

        r = min(255, max(0, r))
        g = min(255, max(0, g))
        b = min(255, max(0, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    def lighten_color(self):
        if not self.selected_color:
            return
        color = self.selected_color
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        # Clarear 20%
        r = min(255, int(r + (255 - r) * 0.2))
        g = min(255, int(g + (255 - g) * 0.2))
        b = min(255, int(b + (255 - b) * 0.2))

        new_color = f"#{r:02x}{g:02x}{b:02x}"

        # NÃO altera a paleta
        self.current_color = new_color
        # Mantém a cor selecionada destacada
        self.draw_palette()

    def darken_color(self):
        if not self.selected_color:
            return
        color = self.selected_color
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        # Escurecer 20%
        r = max(0, int(r * 0.8))
        g = max(0, int(g * 0.8))
        b = max(0, int(b * 0.8))

        new_color = f"#{r:02x}{g:02x}{b:02x}"

        # NÃO altera a paleta
        self.current_color = new_color
        # Mantém a cor selecionada destacada
        self.draw_palette()

    #Adicionar a nova cor à paleta
    def add_current_color_to_palette(self):
        if not self.current_color:
            return

        if len(self.palette) >= self.max_colors:
            print("Paleta cheia! Remova uma cor antes de adicionar.")
            return

        # Adiciona current_color à paleta
        self.palette.append(self.current_color)
        # Seleciona a cor adicionada
        self.selected_color = self.current_color
        self.draw_palette()

    # BUCKET
    def fill_bucket_generic(self, start_row, start_col, preview=False):
        target_color = self.pixels[start_row][start_col]
        if target_color == self.current_color:
            return

        action_pixels = []
        pixels_set = set()
        stack = [(start_row, start_col)]

        def draw_pixel_safe(r, c):
            if 0 <= r < self.rows and 0 <= c < self.cols:
                key = (r, c)
                if key not in pixels_set:
                    old_color = self.pixels[r][c]
                    self.pixels[r][c] = self.current_color
                    action_pixels.append((r, c, old_color))
                    self.draw_pixel(r, c, self.current_color)
                    pixels_set.add(key)

        while stack:
            r, c = stack.pop()
            if self.pixels[r][c] != target_color:
                continue

            if preview:
                x0, y0 = c * self.zoom, r * self.zoom
                x1, y1 = x0 + self.zoom, y0 + self.zoom
                self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=self.color_preview_temp,
                    outline=self.current_color,
                    width=1,
                    tags="temp_shape"
                )
            else:
                draw_pixel_safe(r, c)
                if self.mirror_mode in ("HORIZONTAL", "BOTH"):
                    draw_pixel_safe(r, self.cols - 1 - c)
                if self.mirror_mode in ("VERTICAL", "BOTH"):
                    draw_pixel_safe(self.rows - 1 - r, c)
                if self.mirror_mode == "BOTH":
                    draw_pixel_safe(self.rows - 1 - r, self.cols - 1 - c)

            # Adiciona vizinhos
            for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.pixels[nr][nc] == target_color:
                    stack.append((nr, nc))

        if not preview and action_pixels:
            self.undo_stack.append(action_pixels)

    # Desenha linha
    def draw_line_generic(self, start_row, start_col, end_row, end_col, preview=False):
        action_pixels = []
        pixels_set = set()

        def draw_pixel_safe(r, c):
            if 0 <= r < self.rows and 0 <= c < self.cols:
                key = (r, c)
                if key not in pixels_set:
                    old_color = self.pixels[r][c]
                    self.pixels[r][c] = self.current_color
                    action_pixels.append((r, c, old_color))
                    self.draw_pixel(r, c, self.current_color)
                    pixels_set.add(key)

        r0, c0, r1, c1 = start_row, start_col, end_row, end_col
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        sr = 1 if r0 < r1 else -1
        sc = 1 if c0 < c1 else -1
        err = dr - dc

        while True:
            if preview:
                # Usar função de preview que já trata mirror
                self._draw_preview_pixel(r0, c0)
            else:
                draw_pixel_safe(r0, c0)
                # Mirror real
                if self.mirror_mode in ("HORIZONTAL", "BOTH"):
                    draw_pixel_safe(r0, self.cols - 1 - c0)
                if self.mirror_mode in ("VERTICAL", "BOTH"):
                    draw_pixel_safe(self.rows - 1 - r0, c0)
                if self.mirror_mode == "BOTH":
                    draw_pixel_safe(self.rows - 1 - r0, self.cols - 1 - c0)

            if r0 == r1 and c0 == c1:
                break
            e2 = 2 * err
            if e2 > -dc:
                err -= dc
                r0 += sr
            if e2 < dr:
                err += dr
                c0 += sc

        if not preview and action_pixels:
            self.undo_stack.append(action_pixels)


    def _draw_mirror_pixels(self, r, c, action_pixels):
        # Mirror horizontal
        if self.mirror_mode in ("HORIZONTAL", "BOTH"):
            mirror_c = self.cols - 1 - c
            old_color_m = self.pixels[r][mirror_c]
            self.pixels[r][mirror_c] = self.current_color
            action_pixels.append((r, mirror_c, old_color_m))
            self.draw_pixel(r, mirror_c, self.current_color)

        # Mirror vertical
        if self.mirror_mode in ("VERTICAL", "BOTH"):
            mirror_r = self.rows - 1 - r
            old_color_m = self.pixels[mirror_r][c]
            self.pixels[mirror_r][c] = self.current_color
            action_pixels.append((mirror_r, c, old_color_m))
            self.draw_pixel(mirror_r, c, self.current_color)

        # Mirror ambos
        if self.mirror_mode == "BOTH":
            mirror_r = self.rows - 1 - r
            mirror_c = self.cols - 1 - c
            old_color_m = self.pixels[mirror_r][mirror_c]
            self.pixels[mirror_r][mirror_c] = self.current_color
            action_pixels.append((mirror_r, mirror_c, old_color_m))
            self.draw_pixel(mirror_r, mirror_c, self.current_color)

    def _draw_preview_pixel(self, row, col):
        """Desenha um pixel de preview considerando mirror."""
        x0, y0 = col * self.zoom, row * self.zoom
        x1, y1 = x0 + self.zoom, y0 + self.zoom
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill=self.color_preview_temp,
            outline=self.current_color,
            width=1,
            tags="temp_shape"
        )

        # Mirror horizontal
        if self.mirror_mode in ("HORIZONTAL", "BOTH"):
            mc = self.cols - 1 - col
            if mc != col:
                x0, y0 = mc * self.zoom, row * self.zoom
                x1, y1 = x0 + self.zoom, y0 + self.zoom
                self.canvas.create_rectangle(x0, y0, x1, y1,
                                             fill=self.color_preview_temp,
                                             outline="black",
                                             width=1,
                                             tags="temp_shape")

        # Mirror vertical
        if self.mirror_mode in ("VERTICAL", "BOTH"):
            mr = self.rows - 1 - row
            if mr != row:
                x0, y0 = col * self.zoom, mr * self.zoom
                x1, y1 = x0 + self.zoom, y0 + self.zoom
                self.canvas.create_rectangle(x0, y0, x1, y1,
                                             fill=self.color_preview_temp,
                                             outline="black",
                                             width=1,
                                             tags="temp_shape")

        # Mirror ambos
        if self.mirror_mode == "BOTH":
            mr, mc = self.rows - 1 - row, self.cols - 1 - col
            if (mr != row or mc != col):
                x0, y0 = mc * self.zoom, mr * self.zoom
                x1, y1 = x0 + self.zoom, y0 + self.zoom
                self.canvas.create_rectangle(x0, y0, x1, y1,
                                             fill=self.color_preview_temp,
                                             outline="black",
                                             width=1,
                                             tags="temp_shape")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Editor de Pixel Art")

    # --- Ajustar janela para 90% da tela ---
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    window_width = int(screen_width * 0.9)
    window_height = int(screen_height * 0.9)

    # Centralizar
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    editor = PixelEditor(root)

    # Ajustar canvas para preencher a janela
    editor.canvas.config(width=window_width - 220, height=window_height - 20)  # considerando espaço da toolbar
    editor.redraw_canvas()

    # --- Atalhos de zoom ---
    root.bind("<Control-plus>", lambda e: editor.zoom_in())
    root.bind("<Control-equal>", lambda e: editor.zoom_in())  # algumas teclas + usam "="
    root.bind("<Control-minus>", lambda e: editor.zoom_out())

    # --- Scroll para zoom ---
    def on_mouse_wheel(event):
        if event.state & 0x0004:  # Ctrl pressionado
            if event.delta > 0 or event.num == 4:  # roda para cima
                editor.zoom = min(64, editor.zoom + 1)  # incremento de 1px
            else:  # roda para baixo
                editor.zoom = max(1, editor.zoom - 1)
            editor.redraw_canvas()


    # Bind Windows / Mac / Linux
    root.bind("<MouseWheel>", on_mouse_wheel)  # Windows / Mac
    root.bind("<Button-4>", on_mouse_wheel)    # Linux scroll up
    root.bind("<Button-5>", on_mouse_wheel)    # Linux scroll down

    root.mainloop()
