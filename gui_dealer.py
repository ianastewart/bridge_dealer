"""
Dealer for the GUI. Kept apart from gui.py because importing it loads OpenCV,
the camera and the GPIO, which is slow on the Pi. gui.py imports it after the
window is showing.
"""

import threading

from dealer import Dealer, PI, feed_reset, reset


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
        self.not_ready = False  # True if the last deal did not start because no card was read

    def save_card_image(self):
        # camera.source is outlined by read_card and labelled by match. Copy it
        # because the worker thread draws on it again for the next card.
        source = getattr(self.camera, "source", None)
        if source is not None and self.camera.image is not None:
            self.card_image = source.copy()

    def is_ready(self):
        if not PI:
            return True
        reset()
        feed_reset()
        self.camera.capture()
        ready = self.camera.read_card()
        self.not_ready = not ready
        if not ready:
            # Keep the image so the GUI can show what the camera sees
            self.save_card_image()
        return ready

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
        self.save_card_image()
        return found

    def show_debug_images(self):
        pass
