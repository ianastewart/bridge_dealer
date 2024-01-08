from pbn_reader import create_packs
from dealer import deal
from pathlib import Path


pbn_path = Path("pbns/230801.pbn")
packs = create_packs(pbn_path)
deal(packs[0])
