from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseShim(ABC):
    """
    Base abstraction for all 20 enterprise shims.
    Enforces deterministic state management and tool specification.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._state: Dict[str, Any] = {}
        self.reset()

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the shim."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the service being simulated."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets shim state to a deterministic baseline."""
        pass

    @abstractmethod
    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        """
        Returns a list of tools exposed by this shim.
        Format: [(name, function, description), ...]
        """
        pass

    def get_state(self) -> Dict[str, Any]:
        """Returns the current internal state of the shim."""
        return dict(self._state)

# Registration Imports (Must be at bottom to avoid circular dependency)
# noqa: E402
from . import s01_git as s01_git
from . import s02_rest_api as s02_rest_api
from . import s03_database as s03_database
from . import s04_knowledge_base as s04_knowledge_base
from . import s05_support_desk as s05_support_desk
from . import s06_social_media as s06_social_media
from . import s07_vector_db as s07_vector_db
from . import s08_cicd as s08_cicd
from . import s09_iot as s09_iot
from . import s10_security as s10_security
from . import s11_filesystem as s11_filesystem
from . import s12_email as s12_email
from . import s13_calendar as s13_calendar
from . import s14_payment as s14_payment
from . import s15_notification as s15_notification
from . import s16_search as s16_search
from . import s17_analytics as s17_analytics
from . import s18_workflow as s18_workflow
from . import s19_compliance as s19_compliance
from . import s20_hitl as s20_hitl
