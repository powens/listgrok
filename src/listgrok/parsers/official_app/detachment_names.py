"""Detachment names that contain a list joiner (", " or " and ").

The official app writes several detachments as a serial list ("A, B and C"),
so these names are matched whole before the line is split on its joiners.
Generated from the app's detachment data; names are only ever added, because
old exports still carry detachments GW has since removed.
"""

COMPOUND_DETACHMENTS = frozenset(
    {
        "Legends of Saga and Song",
        "Ordo Hereticus, Purgation Force",
        "Ordo Malleus, Daemon Hunters",
        "Ordo Xenos, Alien Hunters",
    }
)
