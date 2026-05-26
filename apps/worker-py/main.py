import asyncio
import os
import sys


async def loop() -> None:
    while True:
        print("[worker] alive", flush=True)
        await asyncio.sleep(10)


def main() -> None:
    app_env = os.getenv("APP_ENV", "unknown")
    print(f"[worker] starting (APP_ENV={app_env})", flush=True)
    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        print("[worker] stopped", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
