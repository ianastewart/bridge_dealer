from pbn_reader import create_packs
from dealer import Dealer
from pathlib import Path
from mechanics import reset

pbn_path = Path("pbns/230801.pbn")
packs = create_packs(pbn_path)
print("Packs ready")
dealer = Dealer()
while not dealer.is_ready():
    print("Waiting")
if dealer.is_ready():
    dealer.deal(packs[0])

