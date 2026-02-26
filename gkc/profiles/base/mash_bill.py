from typing import Any, Dict


class MashBill:
    """Extract structured facts from an external source."""

    name: str
    description: str = ""

    def run(self, identifier: str) -> Dict[str, Any]:
        """Return structured facts for a given QID/EID/PID."""
        raise NotImplementedError
