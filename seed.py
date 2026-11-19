"""重建演示数据：python seed.py --reset"""
import argparse
from pathlib import Path

from app.repositories import connect, init_schema, seed_demo

DB = Path(__file__).resolve().parent / "data" / "campusevent.db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="删除数据库后重建")
    args = parser.parse_args()
    if args.reset and DB.exists():
        DB.unlink()
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(DB)
    init_schema(conn)
    seed_demo(conn)
    print("数据库已就绪：", DB)


if __name__ == "__main__":
    main()
