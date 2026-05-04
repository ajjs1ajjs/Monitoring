import re
from typing import Dict, Any, Optional

class MetricsParser:
    """Base class for metric parsers."""
    def parse(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError

class PrometheusParser(MetricsParser):
    """Parser for Prometheus/Telegraf text format."""
    def parse(self, text: str) -> Dict[str, Any]:
        metrics = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                if "{" in line:
                    name_part, rest = line.split("{", 1)
                    value_str = rest.rsplit("}", 1)[1]
                    name = name_part.strip()
                    metrics[name] = float(value_str.strip())
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics[parts[0]] = float(parts[1])
            except (ValueError, IndexError):
                continue
        return metrics
