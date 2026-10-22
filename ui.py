import os
import time
# print("Python:", sys.executable)
# print("Version:", sys.version)
# print("SysPath:\n", "\n".join(sys.path))
from pbn_reader import create_packs
from dealer import Dealer
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

try:
    import RPi.GPIO as GPIO
    from mechanics import reset
except ImportError:
    from mock_mechanics import reset


def main_loop():
    dealer = Dealer()
    keyed = ""
    while True:
        number = 1
        valid = False
        while not valid:
            keyed = input("Enter board number or q: ")
            if keyed == "q":
                valid = True
            if keyed.isnumeric():
                number = int(keyed)
                if number > 0 and number <= len(packs):
                    valid = True
                else:
                    print(f"Number not in range 1 to {len(packs)}")
        if keyed == "q":
            break
        print(f"Preparing to deal board {number}")
        while not dealer.board_present():
            print("Insert board")
            time.sleep(1)
        while not dealer.is_ready():
            print("Waiting")
        if dealer.is_ready():
            if dealer.deal(packs[number - 1]):
                print(f"Board {number} completed")
            else:
                print(f"Board {number} failed")
                reset()



# Create a root window (hidden)
root = tk.Tk()
root.withdraw()  # Hide the main window

# Open file dialog
pbn_path = filedialog.askopenfilename(
    title="Select a file",
    filetypes=[("pbn files", "*.pbn"), ("All files", "*.*")],
    initialdir="pbns"
)

if pbn_path:
    print("Selected file:", pbn_path)
else:
    print("No file selected.")
pbn_name = os.path.split(pbn_path)[1]
packs = create_packs(pbn_path)
print(f"{pbn_name} contains {len(packs)} boards")
main_loop()
reset()
print("stopped")
