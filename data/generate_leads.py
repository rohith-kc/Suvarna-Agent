"""STUB — Phase 0 scaffold only.

Built in Phase 2 (CLAUDE.md Part 5.3): seeded synthetic lead generator.
Every distribution here is an INVENTED ASSUMPTION — label it as such.

Usage (once built): python data/generate_leads.py --n 200 --seed 42 --out data/out
"""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/out")
    parser.parse_args()
    raise NotImplementedError("Phase 2: implement per CLAUDE.md Part 5.3")


if __name__ == "__main__":
    main()
