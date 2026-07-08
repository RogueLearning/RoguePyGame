"""Web (pygbag/WASM) entry point.

pygbag looks for a top-level ``main.py`` that runs an async ``main()`` via
``asyncio.run``. The same entry works on desktop too. The per-frame
``await asyncio.sleep(0)`` that hands control back to the browser lives inside
``Game.run``.
"""
import asyncio

from game import Game


async def main():
    await Game().run()


asyncio.run(main())
