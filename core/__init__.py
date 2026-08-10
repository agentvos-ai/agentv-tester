import logging
import warnings

# Suppress noisy upstream deprecations and warnings for Python 3.14 industrial stack
warnings.filterwarnings("ignore", message=".*UnionGenericAlias.*")
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")
warnings.filterwarnings("ignore", message=".*allowed_objects.*")
warnings.filterwarnings("ignore", message=".*jsonschema.*")
warnings.filterwarnings("ignore", message=".*google.genai.*")
warnings.filterwarnings("ignore", message=".*langchain.*")
warnings.filterwarnings("ignore", message=".*asyncio.iscoroutinefunction.*")
warnings.filterwarnings("ignore", message=".*LangChainPendingDeprecationWarning.*")

# Configure basic logging for the core package
logging.basicConfig(level=logging.INFO)
