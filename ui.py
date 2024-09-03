from pbn_reader import create_packs
from dealer import Dealer
from pathlib import Path
from mechanics import board_present, reset

def main_loop():
    dealer = Dealer()
    keyed = ""
    while True:
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
        while not dealer.is_ready():
            print("Waiting")
        if dealer.is_ready():
            while not board_present():
                print("Insert board")
            if dealer.deal(packs[number-1]):
                print(f"Board {number} completed")
            else:
                print(f"Board {number} failed")

pbn_name = "240903.pbn"
pbn_path = Path(f"pbns/{pbn_name}")
packs = create_packs(pbn_path)
print(f"{pbn_name} contains {len(packs)} boards")
main_loop()
reset()
print("stopped")



