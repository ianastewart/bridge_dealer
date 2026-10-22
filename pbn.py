"""
Read and create PBN files without bridgebots (see pbn_reader.py for the bridgebots version).

Only the parts of PBN v1.0 that the dealer needs are handled: the [Deal] tag of each board.
Spec: https://www.tistis.nl/pbn/pbn_v10.txt
"""

import logging
import random
import re
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path
from typing import Dict, List, Optional

PBN_DIR = Path(__file__).parent / "pbns"
DEFAULT_BOARDS = 24

DIRECTIONS = "NESW"  # clockwise, the order of the hands in a [Deal] tag
SUITS = "SHDC"  # the order of the suits within a hand
RANKS = "AKQJT98765432"  # high to low
# Dealer and vulnerability for boards 1 to 16, repeating after that
VULNERABILITY = [
    "None", "NS", "EW", "All", "NS", "EW", "All", "None",
    "EW", "All", "None", "NS", "All", "None", "NS", "EW",
]  # fmt: skip


def parse_deal(deal: str) -> Dict[str, str]:
    """
    Convert the value of a [Deal] tag, e.g. "N:T.95.AT75432.K73 J962.AKQ763.K9.Q ...",
    into {card: direction} where card is rank then suit, e.g. "TS", and direction is N, E, S or W.
    Raises ValueError if the deal is not 52 different cards, 13 in each hand.
    """
    first, sep, hands = deal.strip().partition(":")
    if not sep or first not in DIRECTIONS:
        raise ValueError(f"Bad deal: {deal!r}")
    hands = hands.split()
    if len(hands) != 4:
        raise ValueError(f"Expected 4 hands: {deal!r}")
    start = DIRECTIONS.index(first)
    pack = {}
    for i, hand in enumerate(hands):
        direction = DIRECTIONS[(start + i) % 4]
        suits = hand.replace("10", "T").split(".")
        if len(suits) != 4:
            raise ValueError(f"Expected 4 suits in {hand!r}")
        for suit, ranks in zip(SUITS, suits):
            for rank in ranks:
                card = rank.upper() + suit
                if rank.upper() not in RANKS or card in pack:
                    raise ValueError(f"Bad or repeated card {card} in {deal!r}")
                pack[card] = direction
    if len(pack) != 52 or any(list(pack.values()).count(d) != 13 for d in DIRECTIONS):
        raise ValueError(f"Not 13 cards in each hand: {deal!r}")
    return pack


@dataclass
class Board:
    number: int
    dealer: str  # N, E, S or W
    vulnerable: str  # None, NS, EW or All, as written in the file
    pack: Dict[str, str]  # {card: direction}

    def hand(self, direction: str) -> List[str]:
        """The cards of one hand, by suit (S, H, D, C) and then high to low"""
        cards = [c for c, d in self.pack.items() if d == direction]
        return sorted(cards, key=lambda c: (SUITS.index(c[1]), RANKS.index(c[0])))


TAG = re.compile(r'\[(\w+)\s+"(.*)"\]')


def _records(text: str):
    """Yield {tag: value} for each board in the file. A blank line ends a board."""
    tags = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if "Deal" in tags:
                yield tags
                tags = {}
            continue
        match = TAG.match(line)
        if not match:
            continue  # comment, or a line of a table such as the double dummy results
        name, value = match.groups()
        if name == "Deal" and "Deal" in tags:
            # No blank line between boards
            yield tags
            tags = {}
        tags[name] = value
    if "Deal" in tags:
        yield tags


def read_boards(file_path: Path) -> List[Board]:
    """
    Read a PBN file and return its boards in file order.
    Boards with a missing or malformed [Deal] tag are skipped with a warning.
    """
    boards = []
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    for tags in _records(text):
        try:
            pack = parse_deal(tags["Deal"])
        except ValueError as e:
            logging.warning(f"Malformed deal skipped: {e}")
            continue
        dealer = tags.get("Dealer", "")
        if dealer not in DIRECTIONS:
            dealer = tags["Deal"].strip()[0]  # the first hand listed
        try:
            number = int(tags["Board"])
        except (KeyError, ValueError):
            number = len(boards) + 1
        boards.append(Board(number, dealer, tags.get("Vulnerable", ""), pack))
    return boards


def read_packs(file_path: Path) -> List[Dict[str, str]]:
    """Read a PBN file and return one pack, {card: direction}, per board in file order."""
    return [board.pack for board in read_boards(file_path)]


def random_deal(rng: Optional[random.Random] = None) -> Dict[str, List[str]]:
    """Shuffle a pack and return {direction: [cards]} with 13 cards each"""
    rng = rng or random
    cards = [rank + suit for suit in SUITS for rank in RANKS]
    rng.shuffle(cards)
    return {d: cards[i * 13 : (i + 1) * 13] for i, d in enumerate(DIRECTIONS)}


def format_hand(cards: List[str]) -> str:
    """Cards as PBN suit groups, high to low, e.g. "T.95.AT75432.K73" (a void is empty)"""
    return ".".join(
        "".join(sorted((c[0] for c in cards if c[1] == s), key=RANKS.index))
        for s in SUITS
    )


def format_board(number: int, hands: Dict[str, List[str]], day: Date) -> List[str]:
    """The lines of one board record. The dealer and vulnerability follow the usual rotation."""
    dealer = DIRECTIONS[(number - 1) % 4]
    start = DIRECTIONS.index(dealer)
    deal = " ".join(format_hand(hands[DIRECTIONS[(start + i) % 4]]) for i in range(4))
    return [
        '[Event ""]',
        '[Site ""]',
        f'[Date "{day:%Y.%m.%d}"]',
        f'[Board "{number}"]',
        f'[Dealer "{dealer}"]',
        f'[Vulnerable "{VULNERABILITY[(number - 1) % 16]}"]',
        f'[Deal "{dealer}:{deal}"]',
        "",
    ]


def default_name(day: Optional[Date] = None) -> str:
    """File name made from the date as yymmdd, e.g. 261004.pbn"""
    return f"{day or Date.today():%y%m%d}.pbn"


def create_pbn(
    path: Optional[Path] = None,
    boards: int = DEFAULT_BOARDS,
    overwrite: bool = False,
    rng: Optional[random.Random] = None,
) -> Path:
    """
    Create a PBN file of random deals and return its path.
    The default path is <PBN_DIR>/<yymmdd>.pbn using today's date.
    Raises FileExistsError rather than replacing a file, unless overwrite is True.
    """
    if boards < 1:
        raise ValueError("Need at least one board")
    day = Date.today()
    path = Path(path) if path else PBN_DIR / default_name(day)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    lines = ["%This pbn was generated by the bridge dealer program"]
    for number in range(1, boards + 1):
        lines += format_board(number, random_deal(rng), day)
    path.parent.mkdir(parents=True, exist_ok=True)
    # PBN files use CR LF line ends, as the existing files do
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")
    return path
