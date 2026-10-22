"""
Tkinter front end for the dealer. Sketch - ui.py is the existing console version.

Run with:  python gui.py

The dealing loop blocks for a minute or more, so it runs in a worker thread
and reports progress back to the window through a queue.
"""

import base64
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2

from dealer import Dealer, PI, RANKS, feed_reset, reset
from pbn_reader import create_packs

SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_ORDER = "SHDC"
RED = "#c0392b"
PBN_DIR = Path(__file__).parent / "pbns"
PREVIEW_MAX = (300, 420)  # largest size of the card image, the crop is portrait
POLL_MS = 100
PREVIEW_EVERY = 3  # refresh the preview every n polls


class GuiDealer(Dealer):
    """
    Dealer that reports progress on a queue, can be stopped, and never prompts
    on the console or opens OpenCV windows (neither works from a worker thread).
    """

    def __init__(self, events):
        super().__init__()
        self.events = events
        self.stop_event = threading.Event()
        self.camera.show_image = lambda: None
        # Last card image with contours and decoded card drawn on it
        self.card_image = None

    def is_ready(self):
        if not PI:
            return True
        reset()
        feed_reset()
        self.camera.capture()
        return self.camera.read_card()

    def deal_card(self):
        if self.stop_event.is_set():
            print("Stopped")
            return False
        if super().deal_card():
            self.events.put(
                ("card", self.card, self.last_slot, len(self.dealt["All"]))
            )
            return True
        return False

    def next_card(self):
        found = super().next_card()
        # camera.source is outlined by read_card and labelled by match. Copy it
        # because the worker thread draws on it again for the next card.
        source = getattr(self.camera, "source", None)
        if source is not None:
            self.card_image = source.copy()
        return found

    def show_debug_images(self):
        pass


class HandPanel(ttk.LabelFrame):
    """Shows the cards dealt to one hand, grouped by suit"""

    NAMES = {"N": "North", "E": "East", "S": "South", "W": "West"}

    def __init__(self, parent, direction):
        super().__init__(parent, text=self.NAMES[direction], padding=8)
        self.cards = []
        self.revealed = False
        self.lines = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # The suit lines and the counter share one cell. Whichever is raised is shown,
        # and the suit lines keep the panel the same size when the counter is shown.
        self.suits = tk.Frame(self)
        self.suits.grid(row=0, column=0, sticky="nsew")
        for suit in SUIT_ORDER:
            label = tk.Label(
                self.suits,
                font=("Courier", 14),
                anchor="w",
                width=26,
                fg=RED if suit in "HD" else "black",
            )
            label.pack(anchor="w")
            self.lines[suit] = label
        self.counter = tk.Label(self, font=("Helvetica", 56, "bold"), anchor="center")
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bridge dealer")
        self.packs = []
        self.worker = None
        self.preview_image = None  # keep a reference or Tk drops the image
        self.shown_image = None
        self.complete = False  # True when the hands shown are a finished board
        self.poll_count = 0
        self.events = queue.Queue()
        self.dealer = GuiDealer(self.events)

        # Controls
        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")
        self.open_button = ttk.Button(controls, text="Open PBN...", command=self.open_pbn)
        self.open_button.pack(side="left")
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
        self.progress = ttk.Progressbar(bottom, maximum=52)
        self.progress.pack(fill="x")
        self.status = ttk.Label(bottom, text="Select a PBN file")
        self.status.pack(anchor="w", pady=(4, 0))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_buttons()
        self.after(POLL_MS, self.poll)

    # Helpers
    def dealing(self):
        return self.worker is not None and self.worker.is_alive()

    def update_buttons(self):
        busy = self.dealing()
        state = "disabled" if busy else "normal"
        self.open_button.config(state=state)
        self.board_spin.config(state=state)
        self.deal_button.config(state="normal" if not busy and self.packs else "disabled")
        self.stop_button.config(state="normal" if busy else "disabled")
        self.reveal_button.config(state="normal" if self.complete and not busy else "disabled")

    def poll(self):
        """Runs every POLL_MS in the GUI thread"""
        self.drain_events()
        try:
            present = self.dealer.board_present()
        except Exception:
            present = False
        self.board_label.config(text="Board in place" if present else "No board")
        self.poll_count += 1
        if self.poll_count % PREVIEW_EVERY == 0:
            self.update_preview()
        self.after(POLL_MS, self.poll)

    def update_preview(self):
        image = self.dealer.card_image
        if image is None or image is self.shown_image:
            return
        self.shown_image = image
        h, w = image.shape[:2]
        scale = min(PREVIEW_MAX[0] / w, PREVIEW_MAX[1] / h)
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

    # Actions
    def board_number(self):
        try:
            return int(self.board_spin.get())
        except ValueError:
            return 0

    def open_pbn(self):
        path = filedialog.askopenfilename(
            title="Select PBN file",
            initialdir=PBN_DIR,
            filetypes=[("PBN files", "*.pbn"), ("All files", "*.*")],
        )
        if not path:
            return
        self.packs = create_packs(Path(path))
        self.file_label.config(text=f"{Path(path).name}: {len(self.packs)} boards")
        self.board_spin.config(from_=1 if self.packs else 0, to=len(self.packs))
        self.board_spin.set(1 if self.packs else 0)
        self.status.config(text="Ready")
        self.update_buttons()

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
            reset()
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
        else:
            self.status.config(text=f"Board {number} failed")
        self.complete = ok
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
        reset()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
