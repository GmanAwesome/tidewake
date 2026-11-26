"""Glimmer: the sky's spare light.

The loop, in plain words:
  1. Catch it. Floating motes are Glimmer. Walk into one. Pale motes drift by day;
     golden ones come thick at dusk. Waking a spire also leaves some.
  2. Waystones. Spend 1 Glimmer so a waystone remembers you. Attune two, then
     right-click either one to travel between them. Travel is free.
  3. The Tidewell (called the Glimmer Font before 1.4.4). Spend 2-4 Glimmer on a
     lasting gift for this sky.
"""

# id, title, cost, short how-to / effect
# Ordered cheapest first. Mote Sense is the cheap starter: it helps you catch more.
ATTUNEMENTS = [
    ('sense', 'Mote Sense', 2, 'More motes drift near you, they linger longer, and you catch them from farther away.'),
    ('reach', 'Keen Reach', 3, 'You can mine and place about a block and a half farther.'),
    ('lightfoot', 'Lightfoot', 3, 'You walk and hurry a little faster.'),
    ('breath', 'Deep Breath', 3, 'Hunger drains more slowly, so food lasts longer.'),
    ('brightwake', 'Brightwake', 4, 'A soft glow follows you, and you slowly mend while well-fed.'),
]

WAYSTONE_COST = 1
NAME = 'Tidewell'
HOW = [
    ('Catch', 'Floating motes are Glimmer: walk into one. More drift at dusk.'),
    ('Waystones', '1 Glimmer attunes a waystone. Attune two; travel between is free.'),
    ('Tidewell', 'Spend 2-4 Glimmer here on a lasting gift for this sky.'),
]

WAYSTONE = 'waystone'
FONT = 'tidewell'
LEGACY_FONT = 'glimmer_font'


def key(q, r, y):
    return f'{int(q)},{int(r)},{int(y)}'


def parse_key(k):
    q, r, y = (int(v) for v in k.split(','))
    return q, r, y
