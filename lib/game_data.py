import json
from pathlib import Path

DATA_PATH = Path("faction_data.json")

FACTION_DATA = None
FACTION_LIST = None
DETACHMENT_LIST = None


def get_faction_data():
    global FACTION_DATA
    if FACTION_DATA is not None:
        return FACTION_DATA
    with open(DATA_PATH, "r") as f:
        FACTION_DATA = json.load(f)
    return FACTION_DATA


def get_factions():
    global FACTION_LIST
    if FACTION_LIST is not None:
        return FACTION_LIST
    data = get_faction_data()
    FACTION_LIST = set(data.keys())
    FACTION_LIST.remove("Core Rules")
    FACTION_LIST.remove("Space Marines")
    return FACTION_LIST


def get_all_detachments():
    global DETACHMENT_LIST
    if DETACHMENT_LIST is not None:
        return DETACHMENT_LIST
    data = get_faction_data()
    all_detachments = []
    for faction_key, faction in data.items():
        detachments = faction["detachments"]
        all_detachments.extend(detachments.keys())
    DETACHMENT_LIST = set(all_detachments)
    return DETACHMENT_LIST
