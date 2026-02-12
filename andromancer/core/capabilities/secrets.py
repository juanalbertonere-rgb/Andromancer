from typing import Dict, Optional
from andromancer.core.capabilities.base import Capability, ExecutionResult
from andromancer.utils.secrets import secret_store

class GetSecretCapability(Capability):
    name = "get_secret"
    description = "Obtiene credenciales (usuario/password) para un servicio específico (ej: 'leetcode', 'twitter')"
    risk_level = "medium"

    async def execute(self, service: str) -> ExecutionResult:
        secret = secret_store.get_secret(service)
        if secret:
            # We return it in data, the LLM will use it to type
            return ExecutionResult(True, data={"service": service, "credentials": secret})
        else:
            return ExecutionResult(False, error=f"No se encontraron credenciales para: {service}")
