"""
MARK XXXIX — UI paketi.

Public API:
    from ui import MorpheusUI

    ui = MorpheusUI("face.png")
    ui.set_state("LISTENING")
    ui.write_log("SYS: online")
    ui.root.mainloop()

Tema değiştirmek:
    ui.set_theme("minimal")           # ileride

Doğrudan modüllere erişim (advanced):
    from ui.state import bus, state
    from ui.themes import get_theme, switch_theme
"""
from .app import MorpheusUI, JarvisUI

__all__ = ["MorpheusUI", "JarvisUI"]

__version__ = "39.1.0-pr1"
