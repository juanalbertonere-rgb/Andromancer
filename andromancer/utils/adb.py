import asyncio
import subprocess
import logging
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from andromancer import config as cfg

logger = logging.getLogger("AndroMancer.ADB")

class ADBConnectionError(Exception):
    pass

class ADBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance.device_id = None
        return cls._instance

    async def _run(self, cmd: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            )

    async def ensure_connected(self) -> bool:
        if getattr(self, "_initialized", False):
            return True

        try:
            result = await self._run(["adb", "devices"], timeout=cfg.ADB_TIMEOUT)
            out = (result.stdout or "") + (result.stderr or "")
            devices = [l for l in out.splitlines() if "\tdevice" in l and not l.startswith("List of devices")]
            if not devices:
                raise ADBConnectionError("No Android device connected")
            first_device_line = devices[0].strip()
            self.device_id = first_device_line.split()[0]
            self._initialized = True
            logger.info(f"ADB connected: {self.device_id}")
            return True
        except Exception as e:
            logger.error(f"ADB ensure_connected error: {e}")
            raise ADBConnectionError(str(e))

adb_manager = ADBManager()
