from listgrok import ArmyList, Attachment, Unit, UnitComposition


def test_repeated_wargear_sums():
    model_set = UnitComposition(name="Commander", num_models=1)
    model_set.add_wargear("Missile pod", 1)
    model_set.add_wargear("Missile pod", 3)

    assert model_set.wargear == {"Missile pod": 4}


def test_unit_json_omits_attachment_when_absent():
    unit = Unit(name="Ghostkeel Battlesuit", points=150)

    assert "attachment" not in unit.to_json()
    assert "is_warlord" not in unit.to_json()


def test_unit_json_includes_attachment_when_present():
    unit = Unit(
        name="Ragnar Blackmane",
        points=90,
        is_warlord=True,
        attachment=Attachment(
            group="Attached unit 1", role="Leader", role_detail="Character"
        ),
    )

    o = unit.to_json()
    assert o["is_warlord"] is True
    assert o["attachment"] == {
        "group": "Attached unit 1",
        "role": "Leader",
        "role_detail": "Character",
    }


def test_army_list_json_carries_the_11th_edition_fields():
    army_list = ArmyList(
        name="Awoo",
        points=1260,
        super_faction="Space Marines",
        faction="Space Wolves",
        detachments=["Champions of Fenris", "Veterans of the Fang"],
        detachment_points=3,
        disposition="Disruption",
        army_size="Strike Force",
        army_size_points=2000,
    )

    o = army_list.to_json()
    assert o["detachments"] == ["Champions of Fenris", "Veterans of the Fang"]
    assert o["detachment_points"] == 3
    assert o["disposition"] == "Disruption"
    assert o["army_size"] == "Strike Force"
    assert o["army_size_points"] == 2000
    assert o["super_faction"] == "Space Marines"


def test_army_list_json_omits_super_faction_when_absent():
    assert "super_faction" not in ArmyList(faction="T’au Empire").to_json()
