"""Glimmer systems: waystones (fast travel between attuned shrines) and the Font (spent Glimmer for lasting attunements)."""

# id, title, cost, short how-to / effect
ATTUNEMENTS = [
    ('reach', 'Keen Reach', 3, 'Your mining and placing reach grows by about a block and a half.'),
    ('lightfoot', 'Lightfoot', 3, 'You walk and hurry a little faster.'),
    ('breath', 'Deep Breath', 3, 'Hunger drains more slowly, so food lasts longer.'),
    ('sense', 'Mote Sense', 4, 'Dusk motes linger longer and you can catch them from slightly farther away.'),
    ('brightwake', 'Brightwake', 4, 'A soft glow follows you, and you mend a little when well-fed.'),
]

WAYSTONE = 'waystone'
FONT = 'glimmer_font'


def key(q, r, y):
    return f'{int(q)},{int(r)},{int(y)}'


def parse_key(k):
    q, r, y = (int(v) for v in k.split(','))
    return q, r, y
