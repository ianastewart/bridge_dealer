import logging
from pathlib import Path
from typing import List, Dict
from bridgebots import Deal
from bridgebots.pbn import _build_record_dict, _split_pbn, from_pbn_deal
from bridgebots.deal_enums import Direction


def parse_single_deal(record_strings: List[str]) -> Deal:
    """
    Variant of _parse_single_pbn_record to only handle the deal
    """
    record_dict = _build_record_dict(record_strings)
    try:
        deal = from_pbn_deal(
            record_dict["Dealer"], record_dict["Vulnerable"], record_dict["Deal"]
        )
    except KeyError as e:
        raise ValueError("Missing deal fields and no previous_deal provided") from e
    # Add extra fields to the record
    deal.board = int(record_dict.get("Board", 0))
    deal.date = record_dict.get("Date", 0)
    return deal


def parse_pbn(file_path: Path) -> List[Deal]:
    """
    Variant of bridgebots.parse_pbn to omit board records
    Split PBN file into boards then decompose those boards into Deal objects. Only supports PBN v1.0
    See https://www.tistis.nl/pbn/pbn_v10.txt

    :param file_path: path to a PBN file
    :return: A list of Deals
    """
    records_strings = _split_pbn(file_path)
    result = []
    # Some PBNs have multiple board records per deal
    for record_strings in records_strings:
        try:
            deal = parse_single_deal(record_strings)
            result.append(deal)
        except (KeyError, ValueError) as e:
            logging.warning(f"Malformed record {record_strings}: {e}")
    return result


def create_packs(file_path: Path) -> List[Dict[str, str]]:
    deals = parse_pbn(file_path)
    result = []
    for deal in deals:
        pack = {}
        for direction in [
            Direction.NORTH,
            Direction.SOUTH,
            Direction.EAST,
            Direction.WEST,
        ]:
            for card in [
                f"{card.rank.value[1]}{card.suit.name[0]}"
                for card in deal.hands[direction].cards
            ]:
                pack[card] = direction.name[0]
        result.append(pack)
    return result
