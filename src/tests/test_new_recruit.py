from listgrok.army.army_list import ArmyList, Unit, UnitComposition
from listgrok.parsers.new_recruit import (
    _handle_header,
    _handle_unit_line,
    _handle_unit,
)


class TestHandleHeader:
    def test_happy_header(self):
        header = """
+++++++++++++++++++++++++++++++++++++++++++++++
+ FACTION KEYWORD: Xenos - T'au Empire
+ DETACHMENT: Experimental Prototype Cadre
+ TOTAL ARMY POINTS: 1985pts
+
+ WARLORD: Char2: Commander Shadowsun
+ ENHANCEMENT: Plasma Accelerator Rifle (on Char1: Commander in Coldstar Battlesuit)
& Fusion Blades (on Char2: Commander in Coldstar Battlesuit)
& Thermoneutronic Projector (on Char3: Commander in Enforcer Battlesuit)
+ NUMBER OF UNITS: 18
+ SECONDARY: - Bring It Down: (9x2) + (1x6) - Assassination: 5 Characters
+++++++++++++++++++++++++++++++++++++++++++++++"""

        list = ArmyList()
        _handle_header(header.split("\n"), list)  # type: ignore
        assert list.faction == "Xenos - T'au Empire"
        assert list.detachment == "Experimental Prototype Cadre"
        assert list.points == 1985

    def test_missing_faction(self):
        header = """
+++++++++++++++++++++++++++++++++++++++++++++++
+ DETACHMENT: Experimental Prototype Cadre
+ TOTAL ARMY POINTS: 1985pts
+
+ WARLORD: Char2: Commander Shadowsun
+ ENHANCEMENT: Plasma Accelerator Rifle (on Char1: Commander in Coldstar Battlesuit)
& Fusion Blades (on Char2: Commander in Coldstar Battlesuit)
& Thermoneutronic Projector (on Char3: Commander in Enforcer Battlesuit)
+ NUMBER OF UNITS: 18
+ SECONDARY: - Bring It Down: (9x2) + (1x6) - Assassination: 5 Characters
+++++++++++++++++++++++++++++++++++++++++++++++"""

        list = ArmyList()
        _handle_header(header.split("\n"), list)  # type: ignore
        assert list.faction == ""
        assert list.detachment == "Experimental Prototype Cadre"
        assert list.points == 1985

    def test_missing_detachment(self):
        header = """
+++++++++++++++++++++++++++++++++++++++++++++++
+ FACTION KEYWORD: Xenos - T'au Empire
+ TOTAL ARMY POINTS: 1985pts
+
+ WARLORD: Char2: Commander Shadowsun
+ ENHANCEMENT: Plasma Accelerator Rifle (on Char1: Commander in Coldstar Battlesuit)
& Fusion Blades (on Char2: Commander in Coldstar Battlesuit)
& Thermoneutronic Projector (on Char3: Commander in Enforcer Battlesuit)
+ NUMBER OF UNITS: 18
+ SECONDARY: - Bring It Down: (9x2) + (1x6) - Assassination: 5 Characters
+++++++++++++++++++++++++++++++++++++++++++++++"""

        list = ArmyList()
        _handle_header(header.split("\n"), list)  # type: ignore
        assert list.faction == "Xenos - T'au Empire"
        assert list.detachment == ""
        assert list.points == 1985

    def test_missing_army_size(self):
        header = """
+++++++++++++++++++++++++++++++++++++++++++++++
+ FACTION KEYWORD: Xenos - T'au Empire
+ DETACHMENT: Experimental Prototype Cadre
+
+ WARLORD: Char2: Commander Shadowsun
+ ENHANCEMENT: Plasma Accelerator Rifle (on Char1: Commander in Coldstar Battlesuit)
& Fusion Blades (on Char2: Commander in Coldstar Battlesuit)
& Thermoneutronic Projector (on Char3: Commander in Enforcer Battlesuit)
+ NUMBER OF UNITS: 18
+ SECONDARY: - Bring It Down: (9x2) + (1x6) - Assassination: 5 Characters
+++++++++++++++++++++++++++++++++++++++++++++++"""

        list = ArmyList()
        _handle_header(header.split("\n"), list)  # type: ignore
        assert list.faction == "Xenos - T'au Empire"
        assert list.detachment == "Experimental Prototype Cadre"
        assert list.points == -1


class TestHandleUnitLine:
    def test_warlord(self):
        unit = Unit()
        uc = UnitComposition()
        _handle_unit_line("• Warlord", unit, uc)
        assert unit.is_warlord

    def test_enhancement(self):
        unit = Unit()
        uc = UnitComposition()
        _handle_unit_line("• Fusion Blades (+25 pts)", unit, uc)
        assert unit.enhancement == "Fusion Blades"
        assert len(uc.wargear) == 0

    def test_ignore_upgrade(self):
        unit = Unit()
        uc = UnitComposition()
        _handle_unit_line("• Fusion Blades upgrade", unit, uc)
        assert unit.enhancement == ""
        assert len(uc.wargear) == 0

    def test_loadout(self):
        unit = Unit()
        uc = UnitComposition()
        _handle_unit_line("• 2x Fusion Blaster", unit, uc)
        assert uc.wargear == {"Fusion Blaster": 2}

    def test_multiple_weapons(self):
        unit = Unit()
        uc = UnitComposition()
        _handle_unit_line("• 2x Fusion Blaster", unit, uc)
        _handle_unit_line("• 1x Shield Generator", unit, uc)
        assert uc.wargear == {"Fusion Blaster": 2, "Shield Generator": 1}

    def test_duplicate_weapons(self):
        unit = Unit()
        uc = UnitComposition()
        _handle_unit_line("• 2x Fusion Blaster", unit, uc)
        _handle_unit_line("• 2x Fusion Blaster", unit, uc)
        assert uc.wargear == {"Fusion Blaster": 4}


class TestHandleUnit:
    def test_single_model_unit(self):
        lines = [
            "1x Commander in Coldstar Battlesuit (120 pts)",
            "• 1x Fusion blaster",
            "• Fusion Blades upgrade",
            "• 1x Fusion blaster",
            "• 1x Fusion blaster",
            "• 1x Fusion blaster",
            "• 1x Battlesuit fists",
            "• 2x Shield Drone",
            "• Fusion Blades (+25 pts)",
            "• Warlord",
        ]

        list = ArmyList()
        _handle_unit(lines, list, "CHARACTER")
        assert len(list.units) == 1
        unit = list.units[0]
        assert unit.name == "Commander in Coldstar Battlesuit"
        assert unit.points == 120
        assert len(unit.composition) == 1
        assert unit.is_warlord
        assert unit.sheet_type == "CHARACTER"
        assert unit.enhancement == "Fusion Blades"
        uc = unit.composition[0]
        assert uc.name == "Commander in Coldstar Battlesuit"
        assert uc.num_models == 1
        assert uc.wargear == {
            "Fusion blaster": 4,
            "Battlesuit fists": 1,
            "Shield Drone": 2,
        }

    def test_multi_model_units(self):
        lines = [
            "3x Stealth Battlesuits (60 pts)",
            "• 1x Stealth Shas'vre",
            "    • 1x Battlesuit fists",
            "    • 1x Fusion blaster",
            "  • Battlesuit support system, Homing beacon, Marker Drone, Shield Drone",
            "• 2x Stealth Shas'ui",
            "    • 2x Battlesuit fists",
            "    • 2x Burst cannon",
        ]

        list = ArmyList()
        _handle_unit(lines, list, "OTHER DATASHEETS")

        assert len(list.units) == 1
        unit = list.units[0]
        assert unit.name == "Stealth Battlesuits"
        assert unit.points == 60
        assert len(unit.composition) == 2
        assert unit.sheet_type == "OTHER DATASHEETS"
        uc = unit.composition[0]
        assert uc.name == "Stealth Shas'vre"
        assert uc.num_models == 1
        assert uc.wargear == {
            "Battlesuit fists": 1,
            "Fusion blaster": 1,
            "Battlesuit support system": 1,
            "Homing beacon": 1,
            "Marker Drone": 1,
            "Shield Drone": 1,
        }
        uc = unit.composition[1]
        assert uc.name == "Stealth Shas'ui"
        assert uc.num_models == 2
        assert uc.wargear == {
            "Battlesuit fists": 2,
            "Burst cannon": 2,
        }
