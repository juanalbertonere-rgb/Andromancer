import asyncio
from andromancer.core.capabilities.base import ADBCapability, Capability, ExecutionResult

class OpenAppCapability(ADBCapability, Capability):
    name = "open_app"
    description = "Abre aplicación por nombre o package"
    risk_level = "low"

    async def execute(self, app_name: str) -> ExecutionResult:
        app_map = {
            "whatsapp": "com.whatsapp",
            "chrome": "com.android.chrome",
            "home": "HOME",
            "settings": "com.android.settings",
            "instagram": "com.instagram.android",
            "twitter": "com.twitter.android",
            "gmail": "com.google.android.gm"
        }
        package = app_map.get(app_name.lower(), app_name)

        if package == "HOME":
            await self._adb(["shell", "input", "keyevent", "3"])
        else:
            result = await self._adb(["shell", "monkey", "-p", package, "1"])
            if result.returncode != 0:
                return ExecutionResult(False, error=f"Failed to open {package}: {result.stderr}")

        await asyncio.sleep(1.5)
        return ExecutionResult(True, data={"package": package})
