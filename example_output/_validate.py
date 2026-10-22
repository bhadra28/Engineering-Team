from app import build_app


def main() -> None:
    demo = build_app()
    assert demo is not None
    print("Blocks constructed successfully")


if __name__ == "__main__":
    main()
