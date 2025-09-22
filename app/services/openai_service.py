import os
from typing import Dict, Any, List, Optional
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
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

        # Azure OpenAI
        # Remover barra final do endpoint para evitar inconsistências
        raw_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_endpoint = raw_endpoint[:-1] if raw_endpoint and raw_endpoint.endswith("/") else raw_endpoint
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
            result = self._chat_with_azure(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
            )
            return result

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



    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
        """
        Gera resposta com base em uma lista de mensagens (mensagens já devem incluir o(s) system prompt(s)).
        Retorna { message, tokens } com contagem aproximada do provedor.
        """
        if not self.is_configured():
            raise RuntimeError("Nenhuma configuração de OpenAI/Azure OpenAI encontrada")

        # Azure OpenAI preferencial
        if self.azure_endpoint and self.azure_api_key and self.azure_deployment:
            result = self._chat_with_azure(messages=messages, temperature=temperature)
            return result

        # OpenAI padrão
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        reply = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", None) or 0,
        }
        return {"message": reply, "tokens": tokens}


    def summarize(self, text: str, max_words: int = 300) -> str:
        """
        Resume o texto de uma conversa, preservando fatos, decisões e instruções acionáveis.
        """
        if not self.is_configured():
            raise RuntimeError("Nenhuma configuração de OpenAI/Azure OpenAI encontrada")

        system_prompt = (
            "Você é um assistente que cria resumos de conversas clínicas para contexto de chat. "
            "Produza um resumo objetivo, em português do Brasil, preservando: objetivos do usuário, "
            "informações de agendamento, restrições/condições, decisões já tomadas e dados fixos da clínica. "
            f"Limite-se a aproximadamente {max_words} palavras."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        result = self.chat_completion(messages, temperature=0.2)
        return result.get("message", "")

    # ===== Helpers internos =====
    def _create_azure_client(self):
        from openai import AzureOpenAI  # type: ignore

        return AzureOpenAI(
            api_version=self.azure_api_version,
            azure_endpoint=self.azure_endpoint,
            api_key=self.azure_api_key,
        )

    def _chat_with_azure(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
        """
        Chama Azure OpenAI com pequena política de retry e logs de erro básicos.
        Retorna { message, tokens }.
        """
        if not (self.azure_endpoint and self.azure_api_key and self.azure_deployment):
            raise RuntimeError("Azure OpenAI não configurado")

        last_error: Optional[Exception] = None
        for attempt in range(2):  # 2 tentativas rápidas
            try:
                client = self._create_azure_client()
                response = client.chat.completions.create(
                    messages=messages,
                    temperature=temperature,
                    model=self.azure_deployment,
                )
                reply = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                tokens = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None) or 0,
                    "completion_tokens": getattr(usage, "completion_tokens", None) or 0,
                }
                return {"message": reply, "tokens": tokens}
            except Exception as e:
                # Log mínimo para diagnóstico em dev; não interrompe UX (router trata fallback)
                print(f"[AzureOpenAI][attempt={attempt+1}] erro: {e}")
                last_error = e

        # Se falhar após as tentativas, propagar para o router fazer fallback
        assert last_error is not None
        raise last_error

