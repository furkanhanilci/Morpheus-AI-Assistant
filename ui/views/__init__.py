"""ui.views — kompozit panel/sekmeler."""
from .agent_plan_view import AgentPlanView, StepRow
from .conversation_view import ConversationView, Message
from .hud_canvas import HudCanvas
from .memory_inspector import MemoryInspectorView
from .right_dock import RightDock
from .settings_view import SettingsView
from .sidebar_metrics import SidebarMetrics
from .tool_activity_view import ToolActivityView
from .workspace_view import WorkspaceView

__all__ = [
    "AgentPlanView", "StepRow",
    "ConversationView", "Message",
    "HudCanvas",
    "MemoryInspectorView",
    "RightDock",
    "SettingsView",
    "SidebarMetrics",
    "ToolActivityView",
    "WorkspaceView",
]
