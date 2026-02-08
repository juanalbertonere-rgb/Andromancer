import re
from typing import Optional, Dict
from andromancer.core.capabilities.base import ADBCapability, Capability, ExecutionResult

class TapCapability(ADBCapability, Capability):
    name = "tap"
    description = "Toca en coordenadas (x, y) o en elemento UI"
    risk_level = "low"

    async def execute(self, x: Optional[int] = None, y: Optional[int] = None,
                     element: Optional[Dict] = None) -> ExecutionResult:
        if element:
            bounds = element.get('bounds', '')
            nums = [int(n) for n in re.findall(r"-?\d+", bounds)]
            if len(nums) >= 4:
                x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2

        if x is None or y is None:
            return ExecutionResult(False, error="Coordinates required")

        result = await self._adb(["shell", "input", "tap", str(x), str(y)])
        success = result.returncode == 0
        return ExecutionResult(success, data={"x": x, "y": y}, error=None if success else result.stderr)

class TypeCapability(ADBCapability, Capability):
    name = "type"
    description = "Escribe texto en campo focalizado"
    risk_level = "medium"

    async def execute(self, text: str) -> ExecutionResult:
        safe_text = text.replace("'", "\\'").replace('"', '\\"').replace(" ", "%s")
        result = await self._adb(["shell", "input", "text", safe_text])
        success = result.returncode == 0
        return ExecutionResult(success, data={"text": text}, error=None if success else result.stderr)

class SwipeCapability(ADBCapability, Capability):
    name = "swipe"
    description = "Desliza desde (x1,y1) hasta (x2,y2) con duración en ms"
    risk_level = "low"

    async def execute(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> ExecutionResult:
        result = await self._adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])
        success = result.returncode == 0
        return ExecutionResult(success, data={"x1": x1, "y1": y1, "x2": x2, "y2": y2}, error=None if success else result.stderr)

class BackCapability(ADBCapability, Capability):
    name = "back"
    description = "Presiona el botón de retroceso"
    risk_level = "low"

    async def execute(self) -> ExecutionResult:
        result = await self._adb(["shell", "input", "keyevent", "4"])
        success = result.returncode == 0
        return ExecutionResult(success, data={"action": "back"}, error=None if success else result.stderr)
