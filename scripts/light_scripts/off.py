#!/usr/bin/env python3

# NAME: Off
# Turn all lights off

from backend.ceiling import Ceiling


def run(**kwargs):
    ceil = kwargs["ceiling"]
    ceil.clear(True)


if __name__ == "__main__":
    run(ceiling=Ceiling())
