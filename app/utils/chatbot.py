from app.utils.config import settings
from openai import OpenAI, AsyncOpenAI
import httpx
import json


class DeepSeekModel:
    """
    对话实例
    """

    def __init__(
        self,
        api_key: str = settings.DEEPSEEK_API_KEY,
        # model: str = "deepseek-chat",
        role: str | None = None,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.async_client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        # self.model = model
        self.role = role
        self.messages = [{"role": "system", "content": self.role}] if role is not None else []

    async def async_chat(self, model: str, user_input: str) -> str:
        """
        异步对话方法
        """
        self.messages.append({"role": "user", "content": user_input})
        response = await self.async_client.chat.completions.create(
            model=model,
            messages=self.messages,  # type: ignore
        )
        reply = response.choices[0].message
        self.messages.append(
            {"role": reply.role, "content": reply.content if reply.content is not None else ""}
        )
        return reply.content if reply.content is not None else ""

    # def reset_messages(self) -> None:
    #     """
    #     重置对话消息
    #     """
    #     self.messages = [{"role": "system", "content": self.role}] if self.role is not None else []

    async def async_chat_stream(self, model: str, messages: dict, **kwargs):
        """
        异步流式对话方法
        """
        response = await self.async_client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            reasoning = getattr(delta, "reasoning_content", None)
            if content:
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            if reasoning:
                yield f"data: {json.dumps({'reasoning_content': reasoning}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


class DouBaoModel:
    """
    豆包
    """

    def __init__(self, api_key: str = settings.DOUBAO_API_KEY) -> None:
        pass

    async def async_chat_stream(self, model: str, messages: dict, **kwargs):
        pass


class GPTModel:
    """
    GPT模型
    """

    def __init__(self, api_key: str = settings.GPT_API_KEY) -> None:
        self.client = OpenAI(
            api_key=api_key,
            # 便携AI聚合API的入口地址
            base_url="https://api.bianxie.ai/v1",
            # 禁用 SSL 验证，解决第三方 API 的 SSL EOF 问题
            http_client=httpx.Client(verify=False),
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            # 便携AI聚合API的入口地址
            base_url="https://api.bianxie.ai/v1",
            # 禁用 SSL 验证，解决第三方 API 的 SSL EOF 问题
            http_client=httpx.AsyncClient(verify=False),
        )

    async def async_chat_stream(self, model: str, messages: dict, **kwargs):
        """
        异步流式对话方法
        """
        response = await self.async_client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            reasoning = getattr(delta, "reasoning_content", None)
            if content:
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            if reasoning:
                yield f"data: {json.dumps({'reasoning_content': reasoning}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


model_dict = {
    "deepseek": DeepSeekModel,
    "doubao": DouBaoModel,
    "gpt": GPTModel,
}


class Chatbot:
    """
    聊天机器人类，根据参数生成不同模型的实例，并提供统一的接口进行对话交互
    """

    def __init__(self, modelType: str = "deepseek", **kwargs) -> None:
        if modelType in model_dict:
            self.model = model_dict[modelType](**kwargs)
        else:
            raise ValueError(f"不支持的模型类型: {modelType}")

        self.name_model = DeepSeekModel(
            role="你是一个会话名称生成器，根据用户输入生成一个简洁的会话名称，要求不超过20个字符。"
        )

    # async def async_chat(self, **kwargs) -> str:
    #     """
    #     异步发送消息并获取回复
    #     """
    #     return await self.model.async_chat(**kwargs)

    # def reset_conversation(self) -> None:
    #     """
    #     重置对话
    #     """
    #     self.model.reset_messages()

    async def generate_session_name(self, user_input: str) -> str:
        """
        根据用户输入生成会话名称
        """
        response = await self.name_model.async_chat(model="deepseek-chat", user_input=user_input)
        return response

    async def async_chat_stream(self, model: str, messages: dict, **kwargs):
        """
        异步流式对话方法，逐块返回内容
        """
        async for content in self.model.async_chat_stream(model=model, messages=messages, **kwargs):
            yield content
