"""Tidewake tuning constants."""
import math

# ---- the hex lattice -------------------------------------------------------
HEX = 1.0                     # circumradius of one hex cell (world units)
LAYER = 0.85                  # height of one layer of cells (taller blocks; player is 2 blocks)
SQ3 = math.sqrt(3.0)
CHUNK = 16                    # cells along q and r per chunk (a rhombus of 256 columns)
LAYERS = 500                  # layers per column (1.4.4: 500 tall; v6 surfaces reach ~470, v3-v5 ~342)
V2_LAYERS = 128               # 1.4 / 1.4.1 column height; old saves are this tall
CLOUD_SEA = 12                # layer the cloud sea sits on (world y = 8.4)

# ---- streaming -------------------------------------------------------------
VIEW_DISTANCE = 6             # chunks
UNLOAD_MARGIN = 1.5
MAX_JOBS_IN_FLIGHT = 12
UPLOADS_PER_FRAME = 3

# ---- window ----------------------------------------------------------------
WINDOW_SIZE = (1280, 720)
FOV = 70.0

# ---- the wanderer ----------------------------------------------------------
RADIUS = 0.32
HEIGHT = 1.66                  # just under 2 blocks, so 2-block doors and tunnels fit
EYE = 1.48
CROUCH_HEIGHT = 1.25           # about 1.5 blocks; lower camera, not a crawl
CROUCH_EYE = 1.05
CROUCH_SPEED = 1.55
WALK = 4.6
HURRY = 7.4
DRIFT_SPEED = 13.0
GRAVITY = 24.0
JUMP = 8.6                     # clears one taller block with a little loft
GLIDE_FALL = 2.2               # max fall speed while gliding
REACH = 8.0
FALL_RESPAWN_LAYERS = 10       # drop in from this many layers above land

# ---- time --------------------------------------------------------------------
TIDE_LENGTH = 720.0            # seconds for a full light -> dusk -> light cycle
SIM_TICK = 0.35                # living-cell simulation step
AUTOSAVE = 60.0
