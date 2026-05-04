import logging
import sys
from typing import Optional


class Logger:
    """
    Centralized, structured logger service for the PyMon monitoring application.
    Implements a basic Singleton pattern to ensure consistent configuration
    across all modules.
    """

    _instance: Optional["Logger"] = None

    def __new__(cls):
        if cls._instance is None or cls._instance._initialized is False:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = True
            cls._instance._setup_logging()
        return cls._instance

    def _setup_logging(self):
        """Configures the root logger with standardized format."""
        # 1. Get the root logger instance
        root_logger = logging.getLogger("pymon_monitoring")
        root_logger.setLevel(logging.DEBUG)  # Set lowest level to catch everything

        # Prevent adding handlers multiple times if __init__ is called repeatedly
        if not root_logger.handlers:
            # 2. Create a standardized format (Time, Level, Module, Message)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)-10s - [%(levelname)s] - %(module)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # 3. Create console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)

            # 4. Add the handler to the logger
            root_logger.addHandler(console_handler)

    def __init__(self):
        """Prevent re-initialization of complex setup logic."""
        pass  # Initialization is handled in __new__

    @staticmethod
    def get_module_name() -> str:
        """Helper to retrieve the name of the calling module for better context."""
        # This attempts to capture the caller's file/module name.
        # In a complex multi-threaded environment, this might need refinement.
        try:
            return logging.currentframe().f_back.f_globals["__name__"]  # type: ignore
        except Exception:
            return "unknown_module"

    def debug(self, message: str, exc_info: bool = False):
        """Logs a detailed DEBUG message."""
        logging.getLogger("pymon_monitoring").debug(message, exc_info=exc_info)

    def info(self, message: str, extra: Optional[dict] = None):
        """Logs an informational message."""
        if extra:
            logging.getLogger("pymon_monitoring").info(f"{message} | Extra Context: {extra}", extra=extra)
        else:
            logging.getLogger("pymon_monitoring").info(message)

    def warning(self, message: str, extra: Optional[dict] = None):
        """Logs a WARNING message."""
        if extra:
            logging.getLogger("pymon_monitoring").warning(f"{message} | Extra Context: {extra}", extra=extra)
        else:
            logging.getLogger("pymon_monitoring").warning(message)

    def error(self, message: str, exc_info: bool = True):
        """
        Logs a critical ERROR message with optional stack trace.
        If exc_info is True (default), full traceback is captured and logged.
        """
        logging.getLogger("pymon_monitoring").error(message, exc_info=exc_info)


# --- Usage Example ---
if __name__ == "__main__":
    logger = Logger()
    print("\n--- Testing Logger Service ---\n")

    logger.debug("This is a debug message testing functionality.")
    logger.info("System startup completed successfully.", extra={"component": "server_core"})

    try:
        x = 1 / 0
    except ZeroDivisionError as e:
        # Demonstrating how to log an error with a stack trace (exc_info=True)
        logger.error(f"Caught critical division by zero error.", exc_info=e)  # type: ignore

    logger.warning("Configuration file check passed, but some parameters are deprecated.")
