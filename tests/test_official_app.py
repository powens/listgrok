import json
from pathlib import Path

import pytest

from listgrok import ParseError
from listgrok.parsers.official_app import parse_official_app

EXAMPLES = Path(__file__).parents[1] / "examples" / "official_app"
# New Recruit's GW-style exports (nr_official_*) parse as official-app exports
# but live with New Recruit's other formats.
NEW_RECRUIT_EXAMPLES = (
    Path(__file__).parents[1] / "examples" / "new_recruit" / "official"
)


def example_path(filename: str) -> Path:
    folder = NEW_RECRUIT_EXAMPLES if filename.startswith("nr_") else EXAMPLES
    return folder / filename


OFFICIAL_EXAMPLES = {
    # official_11 and official_25 nest "Warlord" / "Enhancements:" under the
    # model that carries it rather than at the top of the body.
    "official_11.txt": {
        "name": "BLOW ME (away)",
        "points": 2000,
        "super_faction": "",
        "faction": "Astra Militarum",
        "detachments": ["Bridgehead Strike", "Combined Arms"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_12.txt": {
        "name": "Beast Slayer Again",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": [
            "Assault Brethren",
            "Saga of the Beastslayer",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_13.txt": {
        "name": "Deathwatch 2k Voidfire",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Deathwatch",
        "detachments": ["Black Spear Task Force"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_14.txt": {
        "name": "Fuck it we Baal",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Blood Angels",
        "detachments": [
            "Assault Brethren",
            "Ironclad Champions",
            "Wrath of the Doomed",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 3,
        "decorations": {},
    },
    # official_15: an "Attached unit 1" group under CHARACTERS (no ATTACHED UNITS
    # section), and "Mark of Chaos: <god>" body lines, which land in
    # decorations. The two Chosen differ in mark, hence the points-qualified keys.
    "official_15.txt": {
        "name": "Host of Urlakh",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Pactbound Zealots"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 15,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {
            "Chaos Lord": ["Mark of Chaos: Khorne"],
            "Chosen (140)": ["Mark of Chaos: Khorne"],
            "Cultist Mob": ["Mark of Chaos: Khorne"],
            "Chaos Predator Destructor": ["Mark of Chaos: Tzeentch"],
            "Chosen (280)": ["Mark of Chaos: Slaanesh"],
            "Defiler": ["Mark of Chaos: Nurgle"],
            "Havocs": ["Mark of Chaos: Tzeentch"],
            "Helbrute": ["Mark of Chaos: Slaanesh"],
            "Raptors": ["Mark of Chaos: Khorne"],
            "Traitor Guardsmen Squad": ["Mark of Chaos: Tzeentch"],
        },
    },
    "official_16.txt": {
        "name": "Admech CyberErad T&H",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Mechanicus",
        "detachments": ["Cohort Cybernetica", "Eradication Cohort"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 15,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "official_17.txt": {
        "name": "ShamblePoP",
        "points": 2000,
        "super_faction": "",
        "faction": "Death Guard",
        "detachments": ["Paragons of Putrescence", "Shamblerot Vectorium"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "official_18.txt": {
        "name": "Fathers of the fang",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": [
            "Assault Brethren",
            "Ironstorm Spearhead",
            "Saga of the Beastslayer",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_19.txt": {
        "name": "sister.",
        "points": 2000,
        "super_faction": "",
        "faction": "Adepta Sororitas",
        "detachments": ["Bringers of Flame", "Sacred Champions"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "official_20.txt": {
        "name": "11/15/26 BA 18SG Lmao",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Blood Angels",
        "detachments": ["Assault Brethren", "Encarmine Speartip", "Ironclad Champions"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_21.txt": {
        "name": "Need to gaârd something over there v1",
        "points": 2000,
        "super_faction": "",
        "faction": "Leagues of Votann",
        "detachments": ["Farseekers", "Needgaârd Oathband"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_22.txt": {
        "name": "Iron Supplements",
        "points": 1995,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Cabal of Chaos", "Warpstrike Champions"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_23.txt": {
        "name": "I'm going to make so many friends this weekend.",
        "points": 1990,
        "super_faction": "",
        "faction": "Necrons",
        "detachments": ["Awakened Dynasty"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 1990,
        "attached_groups": 4,
        "decorations": {},
    },
    "official_24.txt": {
        "name": "WAAAAAAGGGHHH",
        "points": 1995,
        "super_faction": "",
        "faction": "Orks",
        "detachments": ["Dread Mob", "Green Tide", "Taktikal Brigade"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 1995,
        "attached_groups": 4,
        "decorations": {},
    },
    "official_25.txt": {
        "name": "Sons of dom",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Black Templars",
        "detachments": [
            "Assault Brethren",
            "Ironstorm Spearhead",
            "Tacticus Attack Force",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    # official_26: "<Detachment> Keywords: Character" body lines land in decorations.
    "official_26.txt": {
        "name": "I have no idea what i’m doing… but can you kill this?",
        "points": 1990,
        "super_faction": "",
        "faction": "Astra Militarum",
        "detachments": ["Abhuman Auxiliaries", "Steel Hammer"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1990,
        "attached_groups": 0,
        "decorations": {
            "Baneblade": ["Steel Hammer Keywords: Character"],
            "Doomhammer": ["Steel Hammer Keywords: Character"],
        },
    },
    "official_27.txt": {
        "name": "his is my parameter, and my parameter is me",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Dark Angels",
        "detachments": [
            "Assault Brethren",
            "Stormlance Task Force",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    # official_28: the army name carries no "(N Points)" suffix, so points
    # stays None; everything before the header is the name.
    "official_28.txt": {
        "name": "No more Overwatch…our dreams lie dead….",
        "points": None,
        "super_faction": "",
        "faction": "Imperial Knights",
        "detachments": ["Questor Forgepact", "Valourstrike Lance"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 10,
        "unit_points_total": 1995,
        "attached_groups": 1,
        "decorations": {},
    },
    "official_29.txt": {
        "name": "Space wolves",
        "points": 1975,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": ["Saga of the Great Wolf", "Terminator Storm Force"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 10,
        "unit_points_total": 1975,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_30.txt": {
        "name": "worlds",
        "points": 1995,
        "super_faction": "",
        "faction": "Tyranids",
        "detachments": ["Assimilation Swarm", "Talons of the Norn Queen"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 1995,
        "attached_groups": 1,
        "decorations": {},
    },
    # Each "Attached unit N" heading is underlined with "============".
    "official_31.txt": {
        "name": "Calgar does what Calgar wants",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Ultramarines",
        "detachments": [
            "Devastator Brethren",
            "Tacticus Firestorm Force",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    # LVO 2026 lists (via listhammer): unindented app v2.6.0 exports. Most
    # carry player notes between the name and the header, which are dropped;
    # lvo2026_world_eaters has no "(N Points)" line, so its first block (song
    # lyrics) is the name and points is None. lvo2026_genestealer_cults is
    # hand-annotated and does not parse, so it is not listed.
    "lvo2026_adeptus_mechanicus.txt": {
        "name": "Maybe this year I'll have fun in Vegas",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Mechanicus",
        "detachments": ["Cohort Cybernetica", "Lords of the Forge"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 15,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "lvo2026_aeldari.txt": {
        "name": "10th ed is dead, long live 10th ed",
        "points": 2000,
        "super_faction": "",
        "faction": "Aeldari",
        "detachments": ["Aspect Host"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "lvo2026_chaos_knights.txt": {
        "name": "LVO Huntem",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Knights",
        "detachments": ["Houndpack Lance", "Hunting Warpack"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 2000,
        "attached_groups": 0,
        "decorations": {
            # One of each of these War Dogs carries the keyword line and its
            # same-named siblings do not; the Executioners all cost 140, so
            # a "Name (points)" key cannot single it out.
            "War Dog Brigand": (["Houndpack Lance Keyword: Character"], 1),
            "War Dog Executioner": (["Houndpack Lance Keyword: Character"], 1),
            "War Dog Karnivore": (["Houndpack Lance Keyword: Character"], 1),
        },
    },
    "lvo2026_chaos_space_marines.txt": {
        "name": "Snorting lines and rolling nines",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Creations of Bile"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    "lvo2026_dark_angels.txt": {
        "name": "My first ever army",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Dark Angels",
        "detachments": ["Company of Hunters", "Darkflight Pursuit"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "lvo2026_deathwatch.txt": {
        "name": "Tome to go LVO",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Deathwatch",
        "detachments": ["Black Spear Task Force"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 11,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    "lvo2026_grey_knights.txt": {
        "name": "Palworld2",
        "points": 2000,
        "super_faction": "",
        "faction": "Grey Knights",
        "detachments": ["Argent Assault", "Banishers"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 11,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "lvo2026_imperial_knights.txt": {
        "name": "1 Valourstrike Castellan",
        "points": 1995,
        "super_faction": "",
        "faction": "Imperial Knights",
        "detachments": ["Dominus Foebreakers", "Valourstrike Lance"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 7,
        "unit_points_total": 1995,
        "attached_groups": 0,
        "decorations": {},
    },
    "lvo2026_orks.txt": {
        "name": "Meta",
        "points": 1995,
        "super_faction": "",
        "faction": "Orks",
        "detachments": ["Blitz Brigade", "Runt Swarm", "Wreckas"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 1995,
        "attached_groups": 3,
        "decorations": {},
    },
    "lvo2026_space_wolves.txt": {
        "name": "Technically not 30 Wolf Guard Terminators",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": ["Legends of Saga and Song", "Saga of the Great Wolf"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 11,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "lvo2026_tau_empire.txt": {
        "name": "LVO Emotional Support Hammerheads",
        "points": 2000,
        "super_faction": "",
        "faction": "T’au Empire",
        "detachments": ["Retaliation Cadre"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 18,
        "unit_points_total": 2000,
        "attached_groups": 4,
        "decorations": {},
    },
    "lvo2026_world_eaters.txt": {
        "name": (
            "Listen on! Listen on! This is the truth of it.\n"
            "Fighting leads to killing, and killing gets to warring.\n"
            "And that was damn near the death of us all.\n"
            "Look at us now, busted up and everyone talking about hard rain!\n"
            "But we've learned by the dust of 'em all. Bartertown's learned.\n"
            "Now when men get to fighting, it happens here.\n"
            "And it finishes here.\n"
            "Two men enter, one man leaves"
        ),
        "points": None,
        "super_faction": "",
        "faction": "World Eaters",
        "detachments": ["Khorne Daemonkin", "Vessels of Wrath"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    # listhammer_*: lists from 16+ player events, Sept–Nov 2026, via
    # listhammer.info. Each covers an export form the lvo2026 set lacks: a
    # localised app, a thousands separator other than a comma, the app's
    # ERRORS block, or a footnoted unit header.
    "listhammer_adeptus_custodes.txt": {
        # "2.000 Points": a dot as thousands separator.
        "name": "4++ Magic",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Custodes",
        "detachments": [
            "Emperor’s Chosen",
            "Grav‑Assault Force",
            "Might of the Moritoi",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 10,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "listhammer_adeptus_custodes_errors.txt": {
        # An ERRORS block fused onto the header block, no blank line between.
        "name": "11th harvester",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Custodes",
        "detachments": [
            "Emperor’s Chosen",
            "Lions of the Emperor",
            "Might of the Moritoi",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 11,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
        "validation_errors": [
            (
                "You must select one **CHARACTER** model from your army to be your "
                "**WARLORD**."
            )
        ],
    },
    "listhammer_adeptus_mechanicus_fr.txt": {
        # The French app in the newer dialect: "Unités Attachées" fused with
        # "Unité 1 Attachée", lower-case "points".
        "name": "PWE",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Mechanicus",
        "detachments": ["Cohort Cybernetica", "Eradication Cohort"],
        "detachment_points": 3,
        "disposition": "Prendre et Tenir",
        "army_size": "Force de Frappe",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "listhammer_chaos_knights.txt": {
        # "(145 Points)*" headers, each followed by a "* …" footnote block.
        "name": "We’re going to candy mountain!",
        "points": 1995,
        "super_faction": "",
        "faction": "Chaos Knights",
        "detachments": ["Houndpack Lance", "Hunting Warpack"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 1995,
        "attached_groups": 0,
        "decorations": {
            "War Dog Karnivore": (
                [
                    "Houndpack Lance Keyword: Character",
                    "This Datasheet also has the Battleline keyword",
                ],
                2,
            ),
            "War Dog Stalker": (
                [
                    "Houndpack Lance Keyword: Character",
                    "This Datasheet also has the Battleline keyword",
                ],
                1,
            ),
        },
    },
    "listhammer_imperial_knights_de.txt": {
        # The German app: "Kontingentspunkte", "Punkte", "2.000".
        "name": "Freeblade",
        "points": 1995,
        "super_faction": "",
        "faction": "Imperiale Ritter",
        "detachments": ["Freeblade Company"],
        "detachment_points": 3,
        "disposition": "Prioritätsziele",
        "army_size": "Einsatzverband",
        "army_size_points": 2000,
        "unit_count": 9,
        "unit_points_total": 1995,
        "attached_groups": 0,
        "decorations": {},
    },
    "listhammer_orks_fr.txt": {
        # The French app in the glyph dialect, with narrow no-break spaces
        # as thousands separators and an ERREURS block.
        "name": "Ork FG",
        "points": 2000,
        "super_faction": "",
        "faction": "Orks",
        "detachments": ["Bouzilleurs", "Fling’boyz", "Nuée de Minus"],
        "detachment_points": 3,
        "disposition": "Atouts Prioritaires",
        "army_size": "Force de Frappe",
        "army_size_points": 2000,
        "unit_count": 18,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
        "validation_errors": [
            (
                "Vous devez choisir 1 figurine de PERSONNAGE de votre armée pour "
                "être votre SEIGNEUR DE GUERRE."
            )
        ],
    },
    "listhammer_tau_empire.txt": {
        # "2'000 Points": an apostrophe as thousands separator. The army
        # name's player name is redacted.
        "name": "A Player's shit list",
        "points": 1990,
        "super_faction": "",
        "faction": "T’au Empire",
        "detachments": ["Retaliation Cadre"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 18,
        "unit_points_total": 1990,
        "attached_groups": 5,
        "decorations": {},
    },
    "listhammer_tyranids.txt": {
        # "2 000 Points" with a no-break space as thousands separator.
        "name": "Hive fleet reroll",
        "points": 2000,
        "super_faction": "",
        "faction": "Tyranids",
        "detachments": ["Subterranean Assault"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 19,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {"Trygon": ["Subterranean Assault Keywords: Character"]},
    },
    "listhammer_world_eaters_de.txt": {
        # The German app in the newer dialect, joining detachments with "und".
        "name": "2k",
        "points": 1990,
        "super_faction": "",
        "faction": "World Eaters",
        "detachments": ["Berzerker Warband", "Schlächter des Khorne"],
        "detachment_points": 3,
        "disposition": "Einnehmen und halten",
        "army_size": "Einsatzverband",
        "army_size_points": 2000,
        "unit_count": 11,
        "unit_points_total": 1990,
        "attached_groups": 1,
        "decorations": {},
    },
    # New Recruit v38.5's GW-style export: the official layout under its own
    # footer.
    "nr_official_2.txt": {
        "name": "Vangaurd Onslaught Warrior Bioform Onslaught",
        "points": 2000,
        "super_faction": "",
        "faction": "Tyranids",
        "detachments": ["Vanguard Onslaught", "Warrior Bioform Onslaught"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 20,
        "unit_points_total": 2000,
        "attached_groups": 6,
        "decorations": {},
    },
    # New Recruit v37.14's GW-style export, with an Oxford comma in the
    # detachment line.
    "nr_official_3.txt": {
        "name": "UM- Terminators",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Ultramarines",
        "detachments": [
            "Devastator Brethren",
            "Tacticus Firestorm Force",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    # The same list in New Recruit's other shape: no army-size line, and no blank
    # line after a group heading or between the units of a group.
    "nr_official_4.txt": {
        "name": "UM- Terminators",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Ultramarines",
        "detachments": [
            "Devastator Brethren",
            "Tacticus Firestorm Force",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "",
        "army_size_points": None,
        "unit_count": 12,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
}


def parse_example(filename: str):
    return parse_official_app(example_path(filename).read_text())


# Synthetic, minimal form of official_15's groups: a grouped unit with no
# "Attached as:" line still gets an attachment, with an empty role.
GROUPED_UNIT_WITHOUT_ATTACHED_AS = """Test Army (100 Points)

Test Faction
Test Detachment (3 Detachment Points)
Test Disposition
Strike Force (100 Points)

ATTACHED UNITS

Attached unit 1

Test Unit (50 Points)
  • 1x Test Wargear
"""

# Synthetic: a second "(N Detachment Points)" block looks like a header to
# classify_blocks, so the fold must reject it rather than overwrite the first.
TWO_HEADER_BLOCKS = """Test Army (100 Points)

Test Faction
Test Detachment (3 Detachment Points)
Test Disposition
Strike Force (100 Points)

Test Faction Two
Test Detachment Two (3 Detachment Points)
Test Disposition Two
Strike Force (100 Points)

CHARACTERS

Test Unit (50 Points)
  • 1x Test Wargear
"""


class TestAllOfficialExamples:
    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_metadata(self, filename):
        expected = OFFICIAL_EXAMPLES[filename]
        army_list = parse_example(filename)

        assert army_list.name == expected["name"]
        assert army_list.points == expected["points"]
        assert army_list.super_faction == expected["super_faction"]
        assert army_list.faction == expected["faction"]
        assert army_list.detachments == expected["detachments"]
        assert army_list.detachment_points == expected["detachment_points"]
        assert army_list.disposition == expected["disposition"]
        assert army_list.army_size == expected["army_size"]
        assert army_list.army_size_points == expected["army_size_points"]
        assert len(army_list.units) == expected["unit_count"]
        # Optional key: only an export carrying the app's ERRORS block has any.
        assert army_list.validation_errors == expected.get("validation_errors", [])

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_units_are_well_formed(self, filename):
        expected_decorations = OFFICIAL_EXAMPLES[filename]["decorations"]
        army_list = parse_example(filename)
        carriers: dict[str, int] = {}

        for unit in army_list.units:
            assert unit.name, f"{filename}: unit with empty name"
            assert isinstance(unit.points, int)
            assert unit.sheet_type, f"{filename}: {unit.name} has no sheet type"
            assert unit.composition, f"{filename}: {unit.name} has no composition"
            # decorations is an escape hatch for body lines that are neither
            # "Nx wargear" nor a known keyword ("Mark of Chaos: Khorne" in
            # official_15); each entry tabulates them per unit name, and
            # anything else appearing means an Enhancements:/wargear match
            # regressed rather than the fixture growing a legitimately odd line.
            # A "Name (points)" key wins over a plain "Name" one, for a list
            # whose same-named units decorate differently (official_15).
            key = f"{unit.name} ({unit.points})"
            if key not in expected_decorations:
                key = unit.name
            expected = expected_decorations.get(key, [])
            # A (lines, n) value: exactly n same-named units carry the lines
            # and the rest carry none (lvo2026_chaos_knights' War Dogs).
            if isinstance(expected, tuple):
                if unit.decorations:
                    carriers[key] = carriers.get(key, 0) + 1
                expected = expected[0] if unit.decorations else []
            assert unit.decorations == expected, (
                f"{filename}: {unit.name} has unexpected decorations"
            )
            for model_set in unit.composition:
                assert model_set.name, f"{filename}: {unit.name} model set unnamed"
                assert model_set.num_models, (
                    f"{filename}: {unit.name} model set has no num_models"
                )
                assert all(count > 0 for count in model_set.wargear.values())

        assert carriers == {
            key: value[1]
            for key, value in expected_decorations.items()
            if isinstance(value, tuple)
        }, f"{filename}: wrong number of units carry counted decorations"

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_parsed_list_is_json_serialisable(self, filename):
        army_list = parse_example(filename)

        # The only test that runs to_dict() over a fully populated tree.
        json.dumps(army_list.to_dict())

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_unit_points_sum_to_the_list_total(self, filename):
        # Tabulated, not read from army_list.points, which is None for a list
        # with no points line (official_28, lvo2026_world_eaters).
        army_list = parse_example(filename)

        expected_total = OFFICIAL_EXAMPLES[filename]["unit_points_total"]
        assert sum(unit.points or 0 for unit in army_list.units) == expected_total

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_attached_units_pair_a_leader_with_a_bodyguard(self, filename):
        army_list = parse_example(filename)

        groups: dict[str, list[str]] = {}
        for unit in army_list.units:
            if unit.attachment is not None:
                groups.setdefault(unit.attachment.group, []).append(
                    unit.attachment.role
                )

        assert len(groups) == OFFICIAL_EXAMPLES[filename]["attached_groups"]
        for group, roles in groups.items():
            # Case-insensitive: the classic dialect writes "Attached unit 1",
            # the newer one "Attached Unit 1"; both are kept verbatim, as are
            # the French and German forms (listhammer_*_fr, *_de).
            assert group.lower().startswith(
                ("attached unit ", "unité ", "angeschlossene einheit ")
            ), group
            if not any(roles):
                # official_15 writes the group with no "Attached as:" lines.
                continue
            # One bodyguard unit, and one or more characters joining it: a
            # group can hold two Leaders (official_11) or a Support character
            # alongside or instead of a Leader (official_12, official_19).
            assert roles.count("Bodyguard") == 1, (group, roles)
            others = [role for role in roles if role != "Bodyguard"]
            assert others, (group, roles)
            assert set(others) <= {"Leader", "Support"}, (group, roles)

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_crlf_line_endings_change_nothing(self, filename):
        text = example_path(filename).read_text(encoding="utf-8")

        crlf = parse_official_app(text.replace("\n", "\r\n"))

        assert crlf.to_dict() == parse_official_app(text).to_dict()

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_attachment_comes_only_from_a_group_heading(self, filename):
        army_list = parse_example(filename)

        for unit in army_list.units:
            # official_15 puts its group heading under CHARACTERS rather than
            # an ATTACHED UNITS section, so the sheet type alone does not say
            # whether a unit is attached; only a group heading above it does.
            if unit.sheet_type == "ATTACHED UNITS":
                assert unit.attachment is not None, unit.name
            if unit.attachment is not None:
                assert unit.attachment.group, unit.name


class TestGroupAttachmentFold:
    def test_unit_with_no_attached_as_line_is_still_stamped_with_its_group(self):
        army_list = parse_official_app(GROUPED_UNIT_WITHOUT_ATTACHED_AS)

        unit = army_list.units[0]
        assert unit.attachment is not None
        assert unit.attachment.group == "Attached unit 1"
        assert unit.attachment.role == ""
        assert unit.attachment.role_detail == ""


class TestDuplicateHeaderFold:
    def test_second_header_block_raises_instead_of_overwriting_metadata(self):
        with pytest.raises(ParseError):
            parse_official_app(TWO_HEADER_BLOCKS)


ARMY_NAME_HEADER = """Imperial Knights
Questor Forgepact (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

CHARACTERS

Knight Crusader (410 Points)
  • 1x Avenger gatling cannon
"""


class TestArmyNameFold:
    def test_name_without_a_points_suffix_has_no_points(self):
        # official_28
        army_list = parse_official_app(
            "No more Overwatch…our dreams lie dead….\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "No more Overwatch…our dreams lie dead…."
        assert army_list.points is None

    def test_points_suffix_is_read_off_the_end_of_the_name(self):
        army_list = parse_official_app(
            "Round 2 list\n\nQFP (2,000 Points)\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "Round 2 list\n\nQFP"
        assert army_list.points == 2000

    def test_notes_after_the_points_line_are_dropped(self):
        # lvo2026_grey_knights: player notes follow the name in the same block.
        army_list = parse_official_app(
            "Palworld2 (2,000 Points)\nDonovan Sailo\nMaking Saves\n\n"
            + ARMY_NAME_HEADER
        )

        assert army_list.name == "Palworld2"
        assert army_list.points == 2000

    def test_notes_blocks_after_the_points_line_are_dropped(self):
        # lvo2026_chaos_space_marines: notes in their own blocks after the name.
        army_list = parse_official_app(
            "Snorting lines (2,000 Points)\n\nDan this is whimsy\n\n"
            "**THING YOU SHOULD KNOW***\n- a note\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "Snorting lines"
        assert army_list.points == 2000

    def test_without_a_points_line_only_the_first_block_is_the_name(self):
        army_list = parse_official_app(
            "No more Overwatch\n\nsome notes\nmore notes\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "No more Overwatch"
        assert army_list.points is None


class TestValidationErrorsFold:
    def test_wrapped_error_reads_back_as_one_error(self):
        # Synthetic: a long error the export wraps onto an unbulleted line.
        army_list = parse_official_app(
            GROUPED_UNIT_WITHOUT_ATTACHED_AS.replace(
                "ATTACHED UNITS",
                "ERRORS\n• You must select one\n  character model\n• Too many\n\n"
                "ATTACHED UNITS",
            )
        )

        assert army_list.validation_errors == [
            "You must select one character model",
            "Too many",
        ]


class TestFootnoteFold:
    def test_footnote_joins_the_decorations_of_the_unit_above(self):
        # Synthetic, minimal form of listhammer_chaos_knights.
        army_list = parse_official_app(
            GROUPED_UNIT_WITHOUT_ATTACHED_AS.replace(
                "Test Unit (50 Points)", "Test Unit (50 Points)*"
            )
            + "\n* This Datasheet also has the Battleline keyword\n"
        )

        assert army_list.units[0].decorations == [
            "This Datasheet also has the Battleline keyword"
        ]

    def test_footnote_before_any_unit_raises(self):
        with pytest.raises(ParseError, match="Footnote not directly below"):
            parse_official_app(
                GROUPED_UNIT_WITHOUT_ATTACHED_AS.replace(
                    "ATTACHED UNITS", "* A stray footnote\n\nATTACHED UNITS"
                )
            )

    def test_footnote_below_an_unmarked_unit_raises(self):
        with pytest.raises(ParseError, match="Footnote not directly below"):
            parse_official_app(
                GROUPED_UNIT_WITHOUT_ATTACHED_AS + "\n* A stray footnote\n"
            )

    def test_footnote_after_a_heading_raises(self):
        # Synthetic: a heading between the marked unit and the footnote.
        with pytest.raises(ParseError, match="Footnote not directly below"):
            parse_official_app(
                GROUPED_UNIT_WITHOUT_ATTACHED_AS.replace(
                    "Test Unit (50 Points)", "Test Unit (50 Points)*"
                )
                + "\nBATTLELINE\n\n* This Datasheet also has the Battleline keyword\n"
            )
