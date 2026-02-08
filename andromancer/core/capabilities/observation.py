import os
import asyncio
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
from andromancer.core.capabilities.base import ADBCapability, Capability, ExecutionResult

class UIScrapeCapability(ADBCapability, Capability):
    name = "get_ui"
    description = "Obtiene jerarquía UI actual como XML estructurado"
    risk_level = "low"

    async def execute(self, use_cache: bool = False) -> ExecutionResult:
        try:
            temp_dir = Path(tempfile.gettempdir())

            if not os.access("/tmp", os.W_OK):
                temp_dir = Path.home() / ".cache" / "andromancer"

            temp_dir.mkdir(parents=True, exist_ok=True)
            local_ui_path = temp_dir / "ui.xml"

            await self._adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
            await asyncio.sleep(0.3)

            result = await self._adb(["pull", "/sdcard/ui.xml", str(local_ui_path)])
            if result.returncode != 0:
                return ExecutionResult(False, error="Failed to pull UI: " + (result.stderr or ""))

            try:
                with open(local_ui_path, "r", encoding="utf-8") as f:
                    xml_content = f.read()

                root = ET.fromstring(xml_content)
                elements = self._parse_nodes(root)
                screen_summary = self._summarize_screen(elements)

                return ExecutionResult(True, data={
                    "xml": xml_content,
                    "elements": elements,
                    "summary": screen_summary
                })
            except Exception as e:
                return ExecutionResult(False, error=f"XML parse error: {str(e)}")
        except Exception as e:
            return ExecutionResult(False, error=f"UI scrape error: {str(e)}")

    def _parse_nodes(self, root) -> List[Dict]:
        elements = []
        for node in root.iter('node'):
            if node.get('clickable') == 'true':
                elements.append({
                    "text": node.get('text', ''),
                    "content_desc": node.get('content-desc', ''),
                    "resource_id": node.get('resource-id', ''),
                    "class": node.get('class', ''),
                    "bounds": node.get('bounds', ''),
                    "package": node.get('package', '')
                })
        return elements

    def _summarize_screen(self, elements: List[Dict]) -> str:
        texts = [e['text'] or e['content_desc'] for e in elements[:10] if e['text'] or e['content_desc']]
        return "Screen with: " + ", ".join(texts) if texts else "Screen with no visible text"
