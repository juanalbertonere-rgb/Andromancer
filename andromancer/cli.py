import asyncio
import logging
from datetime import datetime
from andromancer.core.agent import AndroMancerAgent, MissionStatus, event_bus, AgentEvent
from andromancer.core.memory import memory_store
from andromancer import config as cfg

logger = logging.getLogger("AndroMancer.CLI")

class AndroMancerCLI:
    def __init__(self):
        self.agent = AndroMancerAgent()
        self.commands = {
            "mission": self._cmd_mission,
            "status": self._cmd_status,
            "memory": self._cmd_memory,
            "stop": self._cmd_stop,
            "capabilities": self._cmd_capabilities,
            "help": self._cmd_help
        }

    async def run(self, initial_goal: str = None):
        print("🔮 AndroMancer v12.0 - Modular Agent Architecture")

        if initial_goal:
            print(f"🚀 Executing initial goal: {initial_goal}")
            await self._cmd_mission(initial_goal)
            # For non-interactive mode, we might want to wait for completion
            while self.agent.mission and self.agent.mission.status == MissionStatus.RUNNING:
                await asyncio.sleep(1)
            return

        print("Commands: mission <goal>, status, memory, capabilities, stop, help")
        print()

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n🤖 Agent> "
                )
                parts = line.strip().split(maxsplit=1)
                if not parts:
                    continue

                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""

                if cmd in self.commands:
                    await self.commands[cmd](args)
                else:
                    await self._cmd_mission(line)

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                await self._cmd_stop("")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def _cmd_mission(self, goal: str):
        if not goal or goal.strip() == "":
            print("Usage: mission <description>")
            return

        try:
            mission = await self.agent.start_mission(goal)
            print(f"✅ Started mission: {mission.id}")
            asyncio.create_task(self._monitor_mission())
        except Exception as e:
            print(f"❌ Failed to start mission: {e}")

    async def _monitor_mission(self):
        last_step = -1
        while self.agent.mission and self.agent.mission.status == MissionStatus.RUNNING:
            await asyncio.sleep(1)
            if self.agent.mission.current_step != last_step:
                last_step = self.agent.mission.current_step
                if not cfg.SILENT_MODE:
                    print(f"📍 Step {self.agent.mission.current_step}/{self.agent.mission.max_steps}", end="\r")

        if self.agent.mission:
            if not cfg.SILENT_MODE:
                print()
                if self.agent.mission.status == MissionStatus.COMPLETED:
                    print(f"✅ Mission completed in {self.agent.mission.current_step} steps")
                elif self.agent.mission.status == MissionStatus.FAILED:
                    print(f"❌ Mission failed at step {self.agent.mission.current_step}")

    async def _cmd_status(self, _):
        if self.agent.mission:
            print(f"📋 Mission: {self.agent.mission.goal}")
            print(f"🔄 Status: {self.agent.mission.status.name}")
            print(f"📍 Step: {self.agent.mission.current_step}")
        else:
            print("ℹ️  No active mission")

    async def _cmd_memory(self, query: str):
        if not query:
            print(f"💾 Total memories: {len(memory_store.memories)}")
            return
        results = memory_store.retrieve(query)
        for m in results:
            print(f"  [{m.id}] {m.content[:80]}...")

    async def _cmd_capabilities(self, _):
        caps = self.agent.registry.list_capabilities()
        for cap in caps:
            print(f"  - {cap['name']}: {cap['description']}")

    async def _cmd_help(self, _):
        print("Available commands: mission, status, memory, capabilities, stop, help")

    async def _cmd_stop(self, _):
        print("🛑 Stopping agent...")
        self.agent.stop()
