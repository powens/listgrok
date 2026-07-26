from listgrok import ArmyList, Attachment, Unit, UnitComposition


def test_repeated_wargear_sums():
    model_set = UnitComposition(name="Commander", num_models=1)
    model_set.add_wargear("Missile pod", 1)
    model_set.add_wargear("Missile pod", 3)

    assert model_set.wargear == {"Missile pod": 4}


def test_unit_dict_keys_are_stable_when_optional_fields_absent():
    o = Unit(name="Ghostkeel Battlesuit", points=150).to_dict()

    assert o["attachment"] is None
    assert o["is_warlord"] is False


def test_unit_dict_includes_attachment_when_present():
    unit = Unit(
        name="Ragnar Blackmane",
        points=90,
        is_warlord=True,
        attachment=Attachment(
            group="Attached unit 1", role="Leader", role_detail="Character"
        ),
    )

    o = unit.to_dict()
    assert o["is_warlord"] is True
    assert o["attachment"] == {
        "group": "Attached unit 1",
        "role": "Leader",
        "role_detail": "Character",
    }


def test_army_list_dict_carries_the_11th_edition_fields():
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

    o = army_list.to_dict()
    assert o["detachments"] == ["Champions of Fenris", "Veterans of the Fang"]
    assert o["detachment_points"] == 3
    assert o["disposition"] == "Disruption"
    assert o["army_size"] == "Strike Force"
    assert o["army_size_points"] == 2000
    assert o["super_faction"] == "Space Marines"


def test_army_list_dict_keeps_super_faction_key_when_absent():
    assert ArmyList(faction="T’au Empire").to_dict()["super_faction"] == ""
