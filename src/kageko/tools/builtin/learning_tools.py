"""Re-exports from memory_tools + skill_tools.  Kept for backward compat."""

from kageko.tools.builtin.memory_tools import MEMORY_TOOLS
from kageko.tools.builtin.skill_tools import SKILL_TOOLS

LEARNING_TOOLS = MEMORY_TOOLS + SKILL_TOOLS

# Deprecated — use wire_learning from __init__ instead
def set_learning_db(db):
    pass

def set_learning_llm(llm):
    pass
