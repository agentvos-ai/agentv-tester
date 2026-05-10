import logging

logger = logging.getLogger(__name__)

# Trigger registration of all framework adapters
try:
    from . import langchain_adapter as langchain_adapter
except ImportError as e:
    logger.warning("LangChain adapter disabled: %s", str(e))

try:
    from . import langgraph_adapter as langgraph_adapter
except ImportError as e:
    logger.warning("LangGraph adapter disabled: %s", str(e))

try:
    from . import ag2_adapter as ag2_adapter
except ImportError as e:
    logger.warning("AG2 adapter disabled: %s", str(e))

try:
    from . import crewai_adapter as crewai_adapter
except ImportError as e:
    logger.warning("CrewAI adapter disabled: %s", str(e))
