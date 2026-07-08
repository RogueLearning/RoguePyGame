#!/usr/bin/env python3
import asyncio

from game import Game


if __name__ == "__main__":
    asyncio.run(Game().run())
