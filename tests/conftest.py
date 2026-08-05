import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# DATABASE_URL is forced to a throwaway local SQLite file by the root-level
# conftest.py (loaded before this one) — see that file for why.