"""FitBuddy application package.

Loading this package also loads environment variables from a local ``.env``
file (if present) so every module can read configuration via ``os.environ``.
"""

from dotenv import load_dotenv

# Load .env once, as early as possible, before any submodule reads config.
load_dotenv()
