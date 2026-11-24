"""Tidewake tuning constants."""
import math

# ---- the hex lattice -------------------------------------------------------
HEX = 1.0                     # circumradius of one hex cell (world units)
LAYER = 0.7                   # height of one layer of cells
SQ3 = math.sqrt(3.0)
CHUNK = 16                    # cells along q and r per chunk (a rhombus of 256 columns)
LAYERS = 128                  # layers per column
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
HEIGHT = 1.65
EYE = 1.5
WALK = 4.6
HURRY = 7.4
DRIFT_SPEED = 13.0
GRAVITY = 24.0
JUMP = 8.2
GLIDE_FALL = 2.2               # max fall speed while gliding
REACH = 8.0

# ---- time --------------------------------------------------------------------
TIDE_LENGTH = 720.0            # seconds for a full light -> dusk -> light cycle
SIM_TICK = 0.35                # living-cell simulation step
AUTOSAVE = 60.0
