from __future__ import annotations

import app


def main() -> None:
    assert app.demo is not None
    print("OK: app.demo constructed successfully")


if __name__ == "__main__":
    main()
