"""Root launcher for Media Talent Tracker.

Usage:
    uv run streamlit run run.py
or:
    uv run python run.py
"""

import sys
from pathlib import Path

# Add src to sys.path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    # Check if executed via 'streamlit run' or direct python
    is_streamlit = "streamlit" in sys.modules or any("streamlit" in arg for arg in sys.argv)
    if is_streamlit:
        from media_talent_tracker.app import main
        main()
    else:
        from streamlit.web import cli as stcli
        target_app = str(src_dir / "media_talent_tracker" / "app.py")
        sys.argv = ["streamlit", "run", target_app]
        sys.exit(stcli.main())
