"""
Tkinter front end for the dealer. Sketch - ui.py is the existing console version.

Run with:  python gui.py

The window is shown first. OpenCV, the camera and the dealer are slow to load on
the Pi, so they are loaded in a thread afterwards (see load_backend).
The dealing loop blocks for a minute or more, so it runs in a worker thread
and reports progress back to the window through a queue.
"""

import base64
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from types import SimpleNamespace

import pbn

RANKS = "23456789TJQKA"
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_ORDER = "SHDC"
RED = "#c0392b"
BACKGROUND = "white"  # hand boxes
PREVIEW_MAX = (300, 420)  # largest size of the card image, the crop is portrait
POLL_MS = 100
PREVIEW_EVERY = 3  # refresh the preview every n polls


def load_backend(events):
    """
    Slow imports and hardware start-up. Runs in a thread so the window shows first.
    Puts ("ready", backend) or ("load_failed", message) on the queue.
    """
    try:
        import cv2
        from gui_dealer import GuiDealer, reset

        dealer = GuiDealer(events)
    except Exception as e:
        events.put(("load_failed", str(e)))
        return
    events.put(
        (
            "ready",
            SimpleNamespace(cv2=cv2, dealer=dealer, reset=reset),
        )
    )


class HandPanel(tk.LabelFrame):
    """Shows the cards dealt to one hand, grouped by suit"""

    NAMES = {"N": "North", "E": "East", "S": "South", "W": "West"}

    def __init__(self, parent, direction):
        super().__init__(
            parent, text=self.NAMES[direction], bg=BACKGROUND, padx=8, pady=8
        )
        self.cards = []
        self.revealed = False
        self.lines = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # The suit lines and the counter share one cell. Whichever is raised is shown,
        # and the suit lines keep the panel the same size when the counter is shown.
        self.suits = tk.Frame(self, bg=BACKGROUND)
        self.suits.grid(row=0, column=0, sticky="nsew")
        for suit in SUIT_ORDER:
            label = tk.Label(
                self.suits,
                font=("Courier", 14),
                anchor="w",
                bg=BACKGROUND,
                width=26,
                fg=RED if suit in "HD" else "black",
            )
            label.pack(anchor="w")
            self.lines[suit] = label
        self.counter = tk.Label(
            self, font=("Helvetica", 56, "bold"), anchor="center", bg=BACKGROUND
        )
        self.counter.grid(row=0, column=0, sticky="nsew")
        self.refresh()

    def clear(self):
        self.cards = []
        self.revealed = False
        self.refresh()

    def add(self, card):
        self.cards.append(card)
        self.refresh()

    def set_revealed(self, revealed):
        self.revealed = revealed
        self.refresh()

    def refresh(self):
        for suit in SUIT_ORDER:
            ranks = sorted(
                (c[0] for c in self.cards if c[1] == suit), key=RANKS.index, reverse=True
            )
            text = " ".join("10" if r == "T" else r for r in ranks) or "-"
            self.lines[suit].config(text=f"{SUIT_SYMBOLS[suit]} {text}")
        self.counter.config(text=str(len(self.cards)))
        if self.revealed:
            self.suits.tkraise()
        else:
            self.counter.tkraise()


class BoardsWindow(tk.Toplevel):
    """Shows the boards of the current PBN file as hand diagrams"""

    CELL = 30  # width of one hand, wide enough for "♠ A K Q J 10 9 8 7 6 5 4 3 2"

    def __init__(self, parent):
        super().__init__(parent)
        self.geometry("800x640")
        self.text = tk.Text(self, font=("Courier", 12), wrap="none", bg="white")
        scroll = ttk.Scrollbar(self, command=self.text.yview)
        self.text.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_config("red", foreground=RED)
        self.text.tag_config("head", font=("Courier", 12, "bold"), spacing1=12)

    @staticmethod
    def suit_lines(board, direction):
        """Four lines, one per suit, each a list of (text, tag)"""
        cards = board.hand(direction)
        lines = []
        for suit in SUIT_ORDER:
            ranks = " ".join("10" if c[0] == "T" else c[0] for c in cards if c[1] == suit)
            ranks = ranks or "-"
            tag = "red" if suit in "HD" else ""
            lines.append([(SUIT_SYMBOLS[suit], tag), (f" {ranks}", "")])
        return lines

    def pad(self, segments):
        used = sum(len(t) for t, _ in segments)
        return segments + [(" " * (self.CELL - used), "")]

    def show(self, boards, name, current=None):
        self.title(f"{name}: {len(boards)} boards")
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        for board in boards:
            self.text.mark_set(f"board{board.number}", "end-1c")
            self.text.mark_gravity(f"board{board.number}", "left")
            vul = board.vulnerable or "?"
            self.text.insert(
                "end",
                f"Board {board.number}   Dealer {board.dealer}   Vul {vul}\n",
                "head",
            )
            hands = {d: self.suit_lines(board, d) for d in "NESW"}
            blank = []
            rows = []
            for i in range(4):
                rows.append([blank, hands["N"][i], blank])
            for i in range(4):
                rows.append([hands["W"][i], blank, hands["E"][i]])
            for i in range(4):
                rows.append([blank, hands["S"][i], blank])
            for row in rows:
                for cell in row:
                    for text, tag in self.pad(cell):
                        self.text.insert("end", text, tag)
                self.text.insert("end", "\n")
        self.text.config(state="disabled")
        if current is not None and f"board{current}" in self.text.mark_names():
            self.text.yview(f"board{current}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bridge dealer")
        self.packs = []
        self.boards = []
        self.pbn_name = ""
        self.boards_window = None
        self.worker = None
        self.preview_image = None  # keep a reference or Tk drops the image
        self.shown_image = None
        self.complete = False  # True when the hands shown are a finished board
        self.poll_count = 0
        self.events = queue.Queue()
        self.backend = None  # set when load_backend has finished
        self.dealer = None

        # Controls
        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")
        self.open_button = ttk.Button(controls, text="Open PBN...", command=self.open_pbn)
        self.open_button.pack(side="left")
        self.new_button = ttk.Button(controls, text="New PBN...", command=self.new_pbn)
        self.new_button.pack(side="left", padx=4)
        self.show_button = ttk.Button(controls, text="Show", command=self.show_pbn)
        self.show_button.pack(side="left")
        self.file_label = ttk.Label(controls, text="No PBN file selected")
        self.file_label.pack(side="left", padx=8)
        ttk.Label(controls, text="Board:").pack(side="left")
        self.board_spin = ttk.Spinbox(controls, from_=0, to=0, width=5)
        self.board_spin.set(0)
        self.board_spin.pack(side="left", padx=4)
        self.deal_button = ttk.Button(controls, text="Deal", command=self.start_deal)
        self.deal_button.pack(side="left", padx=4)
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop_deal)
        self.stop_button.pack(side="left")
        self.reveal_button = ttk.Button(
            controls, text="Reveal hands", command=self.toggle_reveal
        )
        self.reveal_button.pack(side="left", padx=4)
        self.board_label = ttk.Label(controls)
        self.board_label.pack(side="right")

        # Hands laid out as a compass, with the camera preview beside them
        middle = ttk.Frame(self, padding=8)
        middle.pack(fill="both", expand=True)
        compass = ttk.Frame(middle)
        compass.pack(side="left")
        self.panels = {d: HandPanel(compass, d) for d in "NESW"}
        self.panels["N"].grid(row=0, column=1, padx=4, pady=4)
        self.panels["W"].grid(row=1, column=0, padx=4, pady=4)
        self.panels["E"].grid(row=1, column=2, padx=4, pady=4)
        self.panels["S"].grid(row=2, column=1, padx=4, pady=4)
        self.preview = tk.Label(
            middle,
            text="No card image",
            fg="#aaaaaa",
            bg="#222222",
            width=PREVIEW_MAX[0] // 8,
            height=PREVIEW_MAX[1] // 16,
        )
        self.preview.pack(side="left", anchor="n", padx=8)

        # Progress
        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill="x")
        self.progress = ttk.Progressbar(bottom, maximum=52, mode="indeterminate")
        self.progress.pack(fill="x")
        self.status = ttk.Label(bottom, text="Starting dealer...")
        self.status.pack(anchor="w", pady=(4, 0))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_buttons()
        self.after(POLL_MS, self.poll)
        # Let the window draw before the slow imports start
        self.after(100, self.start_loading)

    def start_loading(self):
        self.progress.start(15)
        threading.Thread(target=load_backend, args=(self.events,), daemon=True).start()

    # Helpers
    def dealing(self):
        return self.worker is not None and self.worker.is_alive()

    def update_buttons(self):
        busy = self.dealing()
        state = "disabled" if busy else "normal"
        self.open_button.config(state=state)
        self.new_button.config(state=state)
        self.show_button.config(state="normal" if self.boards else "disabled")
        self.board_spin.config(state=state)
        can_deal = self.dealer is not None and bool(self.packs)
        self.deal_button.config(state="normal" if not busy and can_deal else "disabled")
        self.stop_button.config(state="normal" if busy else "disabled")
        self.reveal_button.config(state="normal" if self.complete and not busy else "disabled")

    def poll(self):
        """Runs every POLL_MS in the GUI thread"""
        self.drain_events()
        if self.dealer is not None:
            try:
                present = self.dealer.board_present()
            except Exception:
                present = False
            self.board_label.config(text="Board in place" if present else "No board")
            self.poll_count += 1
            if self.poll_count % PREVIEW_EVERY == 0:
                self.update_preview()
        self.after(POLL_MS, self.poll)

    def clear_preview(self):
        self.dealer.card_image = None
        self.shown_image = None
        self.preview_image = None
        self.preview.config(
            image="",
            text="No card image",
            width=PREVIEW_MAX[0] // 8,
            height=PREVIEW_MAX[1] // 16,
        )

    def update_preview(self):
        image = self.dealer.card_image
        if image is None or image is self.shown_image:
            return
        self.shown_image = image
        h, w = image.shape[:2]
        scale = min(PREVIEW_MAX[0] / w, PREVIEW_MAX[1] / h)
        cv2 = self.backend.cv2
        small = cv2.resize(image, (int(w * scale), int(h * scale)))
        # Tk reads PNG data directly, so Pillow is not needed
        ok, png = cv2.imencode(".png", small)
        if ok:
            self.preview_image = tk.PhotoImage(data=base64.b64encode(png.tobytes()))
            self.preview.config(image=self.preview_image, width=0, height=0)

    def drain_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return
            if event[0] == "card":
                _, card, slot, count = event
                self.panels[slot].add(card)
                self.progress.config(value=count)
            elif event[0] == "finished":
                self.on_finished(event[1])
            elif event[0] == "ready":
                self.on_ready(event[1])
            elif event[0] == "load_failed":
                self.progress.stop()
                self.status.config(text=f"Could not start dealer: {event[1]}")
                messagebox.showerror("Bridge dealer", f"Could not start dealer:\n{event[1]}")

    def on_ready(self, backend):
        self.backend = backend
        self.dealer = backend.dealer
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self.show_status()
        self.update_buttons()

    def show_status(self):
        """Status line when idle"""
        if self.dealer is None:
            self.status.config(text="Starting dealer...")
        elif self.packs:
            self.status.config(text="Ready")
        else:
            self.status.config(text="Select a PBN file")

    # Actions
    def board_number(self):
        try:
            return int(self.board_spin.get())
        except ValueError:
            return 0

    def open_pbn(self):
        path = filedialog.askopenfilename(
            title="Select PBN file",
            initialdir=pbn.PBN_DIR,
            filetypes=[("PBN files", "*.pbn"), ("All files", "*.*")],
        )
        if not path:
            return
        self.load_pbn(Path(path))

    def new_pbn(self):
        """Create a PBN file of random deals named for today's date, and open it"""
        boards = simpledialog.askinteger(
            "New PBN",
            "Number of boards:",
            initialvalue=pbn.DEFAULT_BOARDS,
            minvalue=1,
            maxvalue=99,
            parent=self,
        )
        if boards is None:
            return
        path = pbn.PBN_DIR / pbn.default_name()
        overwrite = False
        if path.exists():
            if not messagebox.askyesno(
                "Bridge dealer", f"{path.name} already exists. Replace it?"
            ):
                return
            overwrite = True
        try:
            pbn.create_pbn(path, boards=boards, overwrite=overwrite)
        except OSError as e:
            messagebox.showerror("Bridge dealer", f"Could not create {path.name}:\n{e}")
            return
        self.load_pbn(path)

    def load_pbn(self, path):
        boards = pbn.read_boards(path)
        if not boards:
            messagebox.showwarning("Bridge dealer", f"No boards found in {path.name}")
            return
        self.boards = boards
        self.pbn_name = path.name
        packs = self.packs = [board.pack for board in boards]
        self.file_label.config(text=f"{path.name}: {len(packs)} boards")
        self.board_spin.config(from_=1, to=len(packs))
        self.board_spin.set(1)
        self.show_status()
        self.update_buttons()
        if self.boards_window_open():
            self.show_pbn()  # refresh it with the new file

    def boards_window_open(self):
        return self.boards_window is not None and self.boards_window.winfo_exists()

    def show_pbn(self):
        """Show the boards of the current PBN file in a window"""
        if not self.boards:
            return
        if not self.boards_window_open():
            self.boards_window = BoardsWindow(self)
        self.boards_window.show(self.boards, self.pbn_name, self.board_number())
        self.boards_window.lift()

    def start_deal(self):
        number = self.board_number()
        if not 1 <= number <= len(self.packs):
            messagebox.showwarning("Bridge dealer", f"Board must be 1 to {len(self.packs)}")
            return
        if not self.dealer.board_present():
            messagebox.showwarning("Bridge dealer", "Insert a board first")
            return
        for panel in self.panels.values():
            panel.clear()
        self.complete = False
        self.reveal_button.config(text="Reveal hands")
        self.progress.config(value=0)
        self.status.config(text=f"Dealing board {number}...")
        self.dealer.stop_event.clear()
        self.worker = threading.Thread(
            target=self.run_deal, args=(self.packs[number - 1],), daemon=True
        )
        self.worker.start()
        self.update_buttons()

    def run_deal(self, pack):
        """Worker thread"""
        ok = False
        try:
            ok = bool(self.dealer.deal(pack))
        except Exception as e:
            print(f"Deal error: {e}")
            self.backend.reset()
        self.events.put(("finished", ok))

    def toggle_reveal(self):
        reveal = not self.panels["N"].revealed
        for panel in self.panels.values():
            panel.set_revealed(reveal)
        self.reveal_button.config(text="Hide hands" if reveal else "Reveal hands")

    def stop_deal(self):
        self.status.config(text="Stopping...")
        self.dealer.stop_event.set()

    def on_finished(self, ok):
        self.worker.join()
        number = self.board_number()
        if ok:
            self.status.config(text=f"Board {number} completed")
        elif self.dealer.stop_event.is_set():
            self.status.config(text="Stopped")
        elif self.dealer.not_ready:
            # The image of what the camera sees stays in the preview
            self.status.config(text="Not ready: no card could be read. Check the pack")
        else:
            self.status.config(text=f"Board {number} failed")
        self.complete = ok
        if ok:
            self.clear_preview()
        # The spinbox ignores set() while disabled, so enable the controls first
        self.update_buttons()
        if ok:
            if number < len(self.packs):
                self.board_spin.set(number + 1)
            else:
                self.status.config(text="All boards dealt")
                messagebox.showinfo("Bridge dealer", "All boards dealt")

    def on_close(self):
        if self.dealing():
            self.dealer.stop_event.set()
            self.worker.join(5)
        if self.backend is not None:
            self.backend.reset()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
