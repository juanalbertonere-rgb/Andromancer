import asyncio
from andromancer.core.capabilities.base import ADBCapability, Capability, ExecutionResult
from andromancer.utils.apps import get_package_name

class OpenAppCapability(ADBCapability, Capability):
    name = "open_app"
    description = "Abre aplicación por nombre o package"
    risk_level = "low"

    async def execute(self, app_name: str = None, package: str = None) -> ExecutionResult:
        identifier = package or app_name
        if not identifier:
            return ExecutionResult(False, error="app_name or package is required")

        target_package = get_package_name(identifier)

        if target_package == "HOME":
            await self._adb(["shell", "input", "keyevent", "3"])
        else:
            result = await self._adb(["shell", "monkey", "-p", target_package, "1"])
            if result.returncode != 0:
                return ExecutionResult(False, error=f"Failed to open {target_package}: {result.stderr}")

        await asyncio.sleep(1.5)
        return ExecutionResult(True, data={"package": target_package})
