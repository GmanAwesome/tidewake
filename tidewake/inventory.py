"""Slots of items: the backpack (9 hotbar + 27 more), chests and the kiln."""
from . import items as I


def stack_max(iid):
    it = I.get(iid)
    return it.stack if it else 64


class Inventory:
    def __init__(self, size=36):
        self.slots = [None] * size        # each slot: [id, count, uses_left] or None

    # ---------------------------------------------------------------- basics
    def add(self, iid, count=1, uses=None):
        """Add items; returns how many didn't fit."""
        it = I.get(iid)
        if it is None:
            return 0
        mx = it.stack
        for s in self.slots:
            if count <= 0:
                break
            if s and s[0] == iid and s[1] < mx and it.kind != 'tool':
                k = min(mx - s[1], count)
                s[1] += k
                count -= k
        for i, s in enumerate(self.slots):
            if count <= 0:
                break
            if s is None:
                k = min(mx, count)
                self.slots[i] = [iid, k, uses if uses is not None else it.uses]
                count -= k
        return count

    def count(self, iid):
        return sum(s[1] for s in self.slots if s and s[0] == iid)

    def remove(self, iid, count=1):
        for i, s in enumerate(self.slots):
            if count <= 0:
                break
            if s and s[0] == iid:
                k = min(s[1], count)
                s[1] -= k
                count -= k
                if s[1] <= 0:
                    self.slots[i] = None
        return count == 0

    def take_from(self, i, n=1):
        s = self.slots[i]
        if not s:
            return
        s[1] -= n
        if s[1] <= 0:
            self.slots[i] = None

    def clear(self):
        self.slots = [None] * len(self.slots)

    def to_list(self):
        return [list(s) if s else None for s in self.slots]

    def load(self, data):
        for i, s in enumerate(data[:len(self.slots)]):
            if not s or not I.get(int(s[0])):
                self.slots[i] = None
            else:
                uses = int(s[2]) if len(s) > 2 and s[2] is not None else 0
                self.slots[i] = [int(s[0]), int(s[1]), uses]
        return self


def click_slot(slots, i, cursor, right=False):
    """Minecraft-style slot clicking. slots: list; cursor: slot or None. Returns the new cursor."""
    s = slots[i]
    if not right:
        if cursor is None:
            slots[i] = None
            return s
        if s is None:
            slots[i] = cursor
            return None
        if s[0] == cursor[0] and I.get(s[0]).kind != 'tool':
            mx = stack_max(s[0])
            k = min(mx - s[1], cursor[1])
            s[1] += k
            cursor[1] -= k
            return cursor if cursor[1] > 0 else None
        slots[i] = cursor
        return s
    # right click: take half, or put one
    if cursor is None:
        if s is None:
            return None
        half = (s[1] + 1) // 2
        cur = [s[0], half, s[2]]
        s[1] -= half
        if s[1] <= 0:
            slots[i] = None
        return cur
    if s is None:
        slots[i] = [cursor[0], 1, cursor[2]]
        cursor[1] -= 1
    elif s[0] == cursor[0] and s[1] < stack_max(s[0]) and I.get(s[0]).kind != 'tool':
        s[1] += 1
        cursor[1] -= 1
    else:
        slots[i] = cursor
        return s
    return cursor if cursor[1] > 0 else None
