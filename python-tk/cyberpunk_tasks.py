import json
from pathlib import Path

import tkinter as tk
from tkinter import ttk, simpledialog

# -----------------------------
# Cyberpunk Task Board (Tkinter)
# -----------------------------
# Features
# - Dark-mode, neon/cyberpunk palette
# - "+" button to add tasks
# - Each task is its own draggable card
# - "-" button on each task moves it to the Completed Items tab
# - "✕" button deletes the task entirely
# - Scrollable task areas
# - Pure standard library (Tkinter), single file

# ---- Theme / Style ----
BG_DARK = "#0b0f14"      # near-black
BG_PANEL = "#121826"     # dark panel
NEON_CYAN = "#00E5FF"
NEON_MAGENTA = "#FF00FF"
NEON_LIME = "#39FF14"
NEON_RED = "#FF0055"
TEXT_LIGHT = "#E6F1FF"
TEXT_DIM = "#93a4c3"
CARD_BG = "#0e1421"
CARD_BORDER = "#1f2a44"

TITLE_FONT = ("Segoe UI", 16, "bold")
TEXT_FONT = ("Segoe UI", 11)

CARD_PADY = 8
CARD_PADX = 10


class ScrollableArea(ttk.Frame):
    """A scrollable area containing a Canvas with an interior Frame."""
    def __init__(self, parent, *, bg=BG_PANEL):
        super().__init__(parent)
        self.configure(style="Panel.TFrame")

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel support (Windows/Mac/Linux)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.itemconfigure(self.window_id, width=self.canvas.winfo_width())

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        # Windows/MacOS
        if event.widget is self.canvas or str(event.widget).startswith(str(self.inner)):
            delta = int(-1 * (event.delta / 120))
            self.canvas.yview_scroll(delta, "units")

    def _on_mousewheel_linux(self, event):
        # Linux
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


class TaskCard:
    """A draggable card representing a single task."""
    def __init__(self, app, parent_frame, text):
        self.app = app
        self.parent_frame = parent_frame
        self.text = text

        # Outer frame used for neon border glow effect
        self.shadow = tk.Frame(parent_frame, bg=NEON_CYAN)
        self.frame = tk.Frame(self.shadow, bg=CARD_BG, highlightthickness=2,
                              highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER)

        # Header: drag handle + title + complete button
        self.header = tk.Frame(self.frame, bg=CARD_BG)
        our_handle = "≡"
        self.handle = tk.Label(self.header, text=our_handle, fg=NEON_CYAN, bg=CARD_BG, font=TITLE_FONT)
        self.title = tk.Label(self.header, text=self.text, fg=TEXT_LIGHT, bg=CARD_BG, font=TEXT_FONT, wraplength=700, justify="left")
        self.edit_btn = tk.Button(
            self.header,
            text="✎",
            fg=NEON_MAGENTA,
            bg="#1a0b14",
            activebackground="#33101f",
            activeforeground=NEON_MAGENTA,
            bd=0,
            relief="flat",
            font=TITLE_FONT,
            command=self.edit,
        )
        self.complete_btn = tk.Button(
            self.header,
            text="-",
            fg=NEON_LIME,
            bg="#0b1a12",
            activebackground="#10331d",
            activeforeground=NEON_LIME,
            bd=0,
            relief="flat",
            font=TITLE_FONT,
            command=self.complete,
        )
        self.delete_btn = tk.Button(
            self.header,
            text="✕",
            fg=NEON_RED,
            bg="#140b0b",
            activebackground="#330f0f",
            activeforeground=NEON_RED,
            bd=0,
            relief="flat",
            font=TITLE_FONT,
            command=self.delete,
        )

        self.header.pack(fill="x", padx=12, pady=10)
        self.handle.pack(side="left")
        self.title.pack(side="left", padx=10, fill="x", expand=True)
        self.delete_btn.pack(side="right", padx=(0, 6))
        self.complete_btn.pack(side="right")
        self.edit_btn.pack(side="right")

        # Subtle neon underline
        self.underline = tk.Frame(self.frame, height=2, bg=NEON_MAGENTA)
        self.underline.pack(fill="x")

        self.frame.pack(fill="x", expand=True, padx=2, pady=2)
        self.shadow.pack(fill="x", padx=CARD_PADX, pady=CARD_PADY)

        # Drag bindings (use handle or whole card)
        drag_targets = [self.frame, self.header, self.handle, self.title]
        for w in drag_targets:
            w.bind("<Button-1>", self.on_drag_start)
            w.bind("<B1-Motion>", self.on_drag_motion)
            w.bind("<ButtonRelease-1>", self.on_drag_release)

        self._drag_index = None

    # ---- Drag & drop ordering ----
    def on_drag_start(self, event):
        try:
            self._drag_index = self.app.tasks.index(self)
        except ValueError:
            self._drag_index = None
        self.shadow.configure(bg=NEON_MAGENTA)  # highlight during drag

    def on_drag_motion(self, event):
        if self._drag_index is None:
            return
        container = self.parent_frame  # tasks area frame
        pointer_y = container.winfo_pointery() - container.winfo_rooty()

        # Determine target index based on pointer position vs centers of sibling cards
        cards = self.app.tasks
        y_centers = []
        for card in cards:
            y = card.shadow.winfo_y()
            h = card.shadow.winfo_height() or 1
            y_centers.append(y + h / 2)

        target_index = self._drag_index
        for i, c_y in enumerate(y_centers):
            if pointer_y < c_y:
                target_index = i
                break
        else:
            target_index = len(cards) - 1

        if target_index != self._drag_index:
            # Reorder list and repack
            card = cards.pop(self._drag_index)
            cards.insert(target_index, card)
            self._drag_index = target_index
            self.app.repack_task_cards()

    def on_drag_release(self, event):
        self.shadow.configure(bg=NEON_CYAN)
        self._drag_index = None
        self.app.save_state()

    # ---- Actions ----
    def mark_as_completed(self):
        """Style this card for the completed list."""
        self.title.configure(fg=TEXT_DIM)
        self.shadow.configure(bg=NEON_LIME)

        # Disable dragging
        for w in [self.frame, self.header, self.handle, self.title]:
            w.unbind("<Button-1>")
            w.unbind("<B1-Motion>")
            w.unbind("<ButtonRelease-1>")

        # Swap the complete button to a restore action
        self.complete_btn.configure(text="+", command=self.restore, state="normal")

    def complete(self, save=True):
        """Move this card to the completed tab."""
        # Create a completed-task card before removing this one
        self.app.add_completed_task(self.text, save=False)
        self.app.notebook.select(self.app.tab_completed)

        # Remove and destroy the original card
        if self in self.app.tasks:
            self.app.tasks.remove(self)
        self.shadow.destroy()
        self.app.repack_task_cards()

        if save:
            self.app.save_state()

    def delete(self):
        """Remove this task card entirely."""
        if self in self.app.tasks:
            self.app.tasks.remove(self)
            self.app.repack_task_cards()
        elif self in self.app.completed:
            self.app.completed.remove(self)
        self.shadow.destroy()
        self.app.refresh_scrollregions()
        self.app.save_state()

    def edit(self):
        new_text = simpledialog.askstring("Edit Task", "Edit the task:", initialvalue=self.text, parent=self.app.root)
        if new_text:
            self.text = new_text.strip()
            self.title.configure(text=self.text)
            self.app.save_state()

    def restore(self, save=True):
        """Return this completed card to the active tasks list."""
        if self in self.app.completed:
            self.app.completed.remove(self)
        self.shadow.destroy()

        self.app.add_task(self.text, save=False)
        self.app.refresh_scrollregions()

        if save:
            self.app.save_state()


class TaskBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cyberpunk Task Board")
        self.root.geometry("900x600")
        self.root.resizable(True, True)
        self.root.configure(bg=BG_DARK)
        # self.root.overrideredirect(True)  # Disabled to use native window decorations

        self._drag_x = 0
        self._drag_y = 0

        self._setup_style()

        # Custom title bar
        titlebar = tk.Frame(root, bg="black")
        title_label = tk.Label(titlebar, text="CYBERPUNK TASK LIST", fg=NEON_CYAN, bg="black", font=TITLE_FONT)
        add_btn = tk.Button(titlebar, text="＋", fg=TEXT_LIGHT, bg=BG_PANEL, activebackground=NEON_MAGENTA,
                            activeforeground=TEXT_LIGHT, bd=0, relief="flat", font=("Segoe UI", 18, "bold"),
                            command=self.add_task_dialog)

        # Window control buttons
        min_btn = tk.Button(titlebar, text="–", command=self.root.iconify, fg=TEXT_LIGHT, bg="black",
                             activeforeground=TEXT_LIGHT, activebackground="black", bd=0, relief="flat")
        self._restore_geometry = None

        def toggle_max_restore():
            if self.root.state() == "zoomed":
                self.root.state("normal")
                if self._restore_geometry:
                    self.root.geometry(self._restore_geometry)
            else:
                self._restore_geometry = self.root.geometry()
                self.root.state("zoomed")

        max_btn = tk.Button(titlebar, text="□", command=toggle_max_restore, fg=TEXT_LIGHT, bg="black",
                             activeforeground=TEXT_LIGHT, activebackground="black", bd=0, relief="flat")
        close_btn = tk.Button(titlebar, text="✕", command=self.on_close, fg=TEXT_LIGHT, bg="black",
                               activeforeground=TEXT_LIGHT, activebackground="black", bd=0, relief="flat")

        title_label.pack(side="left", padx=10, pady=12)
        close_btn.pack(side="right", padx=4)
        max_btn.pack(side="right", padx=4)
        min_btn.pack(side="right", padx=4)
        add_btn.pack(side="right", padx=4)
        titlebar.pack(fill="x")

        # Drag to move window
        def start_move(event):
            self._drag_x = event.x
            self._drag_y = event.y

        def do_move(event):
            x = event.x_root - self._drag_x
            y = event.y_root - self._drag_y
            self.root.geometry(f"+{x}+{y}")

        titlebar.bind("<Button-1>", start_move)
        titlebar.bind("<B1-Motion>", do_move)
        title_label.bind("<Button-1>", start_move)
        title_label.bind("<B1-Motion>", do_move)

        # Notebook (tabs)
        self.notebook = ttk.Notebook(root, style="Neon.TNotebook")
        self.tab_active = tk.Frame(self.notebook, bg=BG_PANEL)
        self.tab_completed = tk.Frame(self.notebook, bg=BG_PANEL)
        self.notebook.add(self.tab_active, text="Tasks")
        self.notebook.add(self.tab_completed, text="Completed Items")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Scrollable areas
        self.active_area = ScrollableArea(self.tab_active, bg=BG_PANEL)
        self.active_area.pack(fill="both", expand=True)

        self.completed_area = ScrollableArea(self.tab_completed, bg=BG_PANEL)
        self.completed_area.pack(fill="both", expand=True)

        # Data and persistence
        self.data_file = Path(__file__).with_name("tasks.json")
        self.tasks = []
        self.completed = []
        if not self.load_state():
            for t in [
                "Patch proxies to 12.2.18",
                "Prepare AI Steering Committee slides",
                "Finish CrowdStrike DFD",
                "Schedule PCI policy review",
            ]:
                self.add_task(t, save=False)
            self.save_state()

        # Ensure state is saved when window closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- Style ----
    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Panel.TFrame", background=BG_PANEL)

        style.layout("Neon.TNotebook", style.layout("TNotebook"))
        style.configure("Neon.TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("Neon.TNotebook.Tab", padding=(16, 8), background=BG_PANEL, foreground=TEXT_LIGHT)
        style.map("Neon.TNotebook.Tab",
                  background=[("selected", BG_DARK)],
                  foreground=[("selected", NEON_CYAN)])

    # ---- Task operations ----
    def add_task_dialog(self):
        text = simpledialog.askstring("New Task", "Describe the task:", parent=self.root)
        if text:
            self.add_task(text.strip())

    def add_task(self, text: str, save=True):
        card = TaskCard(self, self.active_area.inner, text)
        self.tasks.append(card)
        self.repack_task_cards()
        self.refresh_scrollregions()
        if save:
            self.save_state()
        return card

    def add_completed_task(self, text: str, save=True):
        card = TaskCard(self, self.completed_area.inner, text)
        card.mark_as_completed()
        self.completed.append(card)
        self.refresh_scrollregions()
        if save:
            self.save_state()
        return card

    def repack_task_cards(self):
        # Repack active tasks in current order
        for card in self.tasks:
            try:
                card.shadow.pack_forget()
            except Exception:
                pass
        for card in self.tasks:
            card.shadow.pack(fill="x", padx=CARD_PADX, pady=CARD_PADY)
        self.refresh_scrollregions()

    def refresh_scrollregions(self):
        # Force scrollregion update
        self.root.update_idletasks()
        self.active_area._on_configure(None)
        self.completed_area._on_configure(None)

    def save_state(self):
        data = {
            "tasks": [card.text for card in self.tasks],
            "completed": [card.text for card in self.completed],
        }
        try:
            with self.data_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load_state(self):
        if not self.data_file.exists():
            return False
        try:
            with self.data_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for text in data.get("tasks", []):
                self.add_task(text, save=False)
            for text in data.get("completed", []):
                self.add_completed_task(text, save=False)
            self.refresh_scrollregions()
            return True
        except Exception:
            return False

    def on_close(self):
        self.save_state()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskBoardApp(root)
    root.mainloop()
