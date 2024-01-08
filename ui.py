from pbn_reader import create_packs
from dealer import Dealer
from pathlib import Path


pbn_path = Path("pbns/230801.pbn")
packs = create_packs(pbn_path)
dealer = Dealer()
dealer.deal(packs[0])

