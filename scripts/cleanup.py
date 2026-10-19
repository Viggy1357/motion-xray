"""Motion X Ray — clean up local state and artifacts (STRUCTURE-ONLY stub).

The real command removes expired raw media and derived artifacts per the
configured TTLs. This scaffold only announces intent and exits nonzero.
"""

from __future__ import annotations

import sys


def main() -> int:
    print("[cleanup] STRUCTURE-ONLY stub — nothing removed.")
    print("[cleanup] TODO(T08): purge expired raw media/artifacts per TTL policy.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
