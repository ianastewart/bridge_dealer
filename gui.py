"""
PySide6 front end for the dealer. Sketch - ui.py is the existing console version.

Run with:  python gui.py

The dealing loop blocks for a minute or more, so it runs in a worker thread
and reports progress back to the window with Qt signals.
"""

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from dealer import Dealer, PI, RANKS, SUITS, feed_reset, reset
from pbn_reader import create_packs

SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_ORDER = "SHDC"
RED = "#c0392b"
PBN_DIR = Path(__file__).parent / "pbns"


class DealSignals(QObject):
    """Created in the GUI thread, emitted from the worker thread"""

    card_dealt = Signal(str, str, int)  # card, slot, number dealt so far
    finished = Signal(bool)


class GuiDealer(Dealer):
    """
    Dealer that reports progress by signal, can be stopped, and never prompts
    on the console or opens OpenCV windows (neither works from a worker thread).
    """

    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        self.stop_event = threading.Event()
        self.camera.show_image = lambda: None

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
            self.signals.card_dealt.emit(
                self.card, self.last_slot, len(self.dealt["All"])
            )
            return True
        return False

    def show_debug_images(self):
        pass


class DealWorker(QThread):
    def __init__(self, dealer, pack):
        super().__init__()
        self.dealer = dealer
        self.pack = pack

    def run(self):
        ok = False
        try:
            ok = bool(self.dealer.deal(self.pack))
        except Exception as e:
            print(f"Deal error: {e}")
            reset()
        self.dealer.signals.finished.emit(ok)


class HandPanel(QGroupBox):
    """Shows the cards dealt to one hand, grouped by suit"""

    NAMES = {"N": "North", "E": "East", "S": "South", "W": "West"}

    def __init__(self, direction):
        super().__init__(self.NAMES[direction])
        self.cards = []
        self.label = QLabel()
        self.label.setTextFormat(Qt.RichText)
        self.label.setFont(QFont("Monospace", 14))
        self.label.setMinimumWidth(240)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.refresh()

    def clear(self):
        self.cards = []
        self.refresh()

    def add(self, card):
        self.cards.append(card)
        self.refresh()

    def refresh(self):
        lines = []
        for suit in SUIT_ORDER:
            ranks = sorted(
                (c[0] for c in self.cards if c[1] == suit), key=RANKS.index, reverse=True
            )
            colour = RED if suit in "HD" else "inherit"
            text = " ".join("10" if r == "T" else r for r in ranks) or "-"
            lines.append(
                f'<span style="color:{colour}">{SUIT_SYMBOLS[suit]}</span> {text}'
            )
        self.label.setText("<br>".join(lines))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bridge dealer")
        self.packs = []
        self.worker = None
        self.signals = DealSignals()
        self.signals.card_dealt.connect(self.on_card_dealt)
        self.signals.finished.connect(self.on_finished)
        self.dealer = GuiDealer(self.signals)

        # Controls
        self.file_label = QLabel("No PBN file selected")
        self.open_button = QPushButton("Open PBN...")
        self.open_button.clicked.connect(self.open_pbn)
        self.board_spin = QSpinBox()
        self.board_spin.setRange(0, 0)
        self.deal_button = QPushButton("Deal")
        self.deal_button.clicked.connect(self.start_deal)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_deal)
        self.board_label = QLabel()
        controls = QHBoxLayout()
        for w in (
            self.open_button,
            self.file_label,
            QLabel("Board:"),
            self.board_spin,
            self.deal_button,
            self.stop_button,
        ):
            controls.addWidget(w)
        controls.addStretch()
        controls.addWidget(self.board_label)

        # Hands laid out as a compass
        self.panels = {d: HandPanel(d) for d in "NESW"}
        compass = QGridLayout()
        compass.addWidget(self.panels["N"], 0, 1)
        compass.addWidget(self.panels["W"], 1, 0)
        compass.addWidget(self.panels["E"], 1, 2)
        compass.addWidget(self.panels["S"], 2, 1)

        # Camera preview
        self.preview = QLabel("No camera image")
        self.preview.setFixedSize(320, 240)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background: #222; color: #aaa;")

        middle = QHBoxLayout()
        middle.addLayout(compass)
        middle.addWidget(self.preview, alignment=Qt.AlignTop)

        self.progress = QProgressBar()
        self.progress.setRange(0, 52)
        self.status = QLabel("Select a PBN file")

        root = QVBoxLayout()
        root.addLayout(controls)
        root.addLayout(middle)
        root.addWidget(self.progress)
        root.addWidget(self.status)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        # Poll the board switch and refresh the camera preview
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(250)
        self.update_buttons()

    # Helpers
    def dealing(self):
        return self.worker is not None and self.worker.isRunning()

    def update_buttons(self):
        busy = self.dealing()
        self.open_button.setEnabled(not busy)
        self.board_spin.setEnabled(not busy)
        self.deal_button.setEnabled(not busy and bool(self.packs))
        self.stop_button.setEnabled(busy)

    def poll(self):
        try:
            present = self.dealer.board_present()
        except Exception:
            present = False
        self.board_label.setText("Board in place" if present else "No board")
        image = self.dealer.camera.image
        if image is not None:
            h, w = image.shape[:2]
            qimage = QImage(image.data, w, h, image.strides[0], QImage.Format_BGR888)
            self.preview.setPixmap(
                QPixmap.fromImage(qimage).scaled(
                    self.preview.size(), Qt.KeepAspectRatio
                )
            )

    # Actions
    def open_pbn(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PBN file", str(PBN_DIR), "PBN files (*.pbn);;All files (*)"
        )
        if not path:
            return
        self.packs = create_packs(Path(path))
        self.file_label.setText(f"{Path(path).name}: {len(self.packs)} boards")
        self.board_spin.setRange(1 if self.packs else 0, len(self.packs))
        self.status.setText("Ready")
        self.update_buttons()

    def start_deal(self):
        if not self.dealer.board_present():
            QMessageBox.warning(self, "Bridge dealer", "Insert a board first")
            return
        number = self.board_spin.value()
        for panel in self.panels.values():
            panel.clear()
        self.progress.setValue(0)
        self.status.setText(f"Dealing board {number}...")
        self.dealer.stop_event.clear()
        self.worker = DealWorker(self.dealer, self.packs[number - 1])
        self.worker.start()
        self.update_buttons()

    def stop_deal(self):
        self.status.setText("Stopping...")
        self.dealer.stop_event.set()

    # Signals from the worker thread
    def on_card_dealt(self, card, slot, count):
        self.panels[slot].add(card)
        self.progress.setValue(count)

    def on_finished(self, ok):
        self.worker.wait()
        if ok:
            self.status.setText(f"Board {self.board_spin.value()} completed")
        elif self.dealer.stop_event.is_set():
            self.status.setText("Stopped")
        else:
            self.status.setText(f"Board {self.board_spin.value()} failed")
        self.update_buttons()

    def closeEvent(self, event):
        if self.dealing():
            self.dealer.stop_event.set()
            self.worker.wait(5000)
        reset()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
