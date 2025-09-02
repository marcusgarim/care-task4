import os
from typing import Dict, Any
from dotenv import load_dotenv


class OpenAIService:
    """
    Serviço simples para encapsular a chamada à OpenAI.
    Usa fallback no endpoint caso a variável OPENAI_API_KEY não esteja configurada.
    """

    def __init__(self) -> None:
        # Garantir carregamento do .env na raiz
        try:
            load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
        except Exception:
            pass

        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Azure OpenAI
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-05-01-preview")
        self.azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    def is_configured(self) -> bool:
        return bool(self.api_key) or bool(self.azure_endpoint and self.azure_api_key and self.azure_deployment)

    def generate_reply(self, user_message: str, session_id: str, is_first: bool) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Nenhuma configuração de OpenAI/Azure OpenAI encontrada")

        system_prompt = (
            "Você é um assistente de agendamentos de clínica, seja objetivo e claro. "
            "Responda em português do Brasil."
        )

        # Azure OpenAI preferencial se configurado
        if self.azure_endpoint and self.azure_api_key and self.azure_deployment:
            from openai import AzureOpenAI  # type: ignore

            client = AzureOpenAI(
                api_version=self.azure_api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=self.azure_api_key,
            )
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
                model=self.azure_deployment,
            )
            reply = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            tokens = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None) or 0,
                "completion_tokens": getattr(usage, "completion_tokens", None) or 0,
            }
            return {"message": reply, "tokens": tokens}

        # OpenAI padrão
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
        reply = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", None) or 0,
        }
        return {"message": reply, "tokens": tokens}


