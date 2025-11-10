from livekit.agents.llm import LLM
import os
import httpx

class QwenLLM(LLM):
    def __init__(self, model: str = "qwen-turbo"):
        self.model = model
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not set in .env")

    async def chat(self, messages: list) -> str:
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {"result_format": "message"}
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["output"]["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Qwen error: {str(e)}"