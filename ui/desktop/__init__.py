# ui/desktop/__init__.py
"""
PySide6 Desktop Application
"""
from .widgets.analysis import AnalysisWidget
from .widgets.input_panel import InputPanel
from .widgets.results_panel import ResultsPanel
from .widgets.chat_tab import ChatTab
from .widgets.user_profile_widget import UserProfileWidget
from .widgets.onboarding_wizard import OnboardingWizard

# For backward compatibility (if needed)
MainWindow = AnalysisWidget
ChatPanel = ChatTab

__all__ = [
    'AnalysisWidget',
    'MainWindow',  # Alias for backward compatibility
    'InputPanel',
    'ResultsPanel',
    'ChatTab',
    'ChatPanel',   # Alias for backward compatibility
    'UserProfileWidget',
    'OnboardingWizard'
]