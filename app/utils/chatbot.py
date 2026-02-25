from config import settings
from openai import OpenAI, AsyncOpenAI


class DeepSeekModel:
    """
    对话实例
    """

    def __init__(
        self,
        api_key: str = settings.DEEPSEEK_API_KEY,
        model: str = "deepseek-chat",
        role: str = "你是一个专业助手",
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.async_client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model
        self.role = role
        self.messages = [{"role": "system", "content": self.role}]

    def chat(self, user_input: str) -> str:
        """
        同步对话方法
        """
        self.messages.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,  # type: ignore
        )
        reply = response.choices[0].message
        self.messages.append(
            {"role": reply.role, "content": reply.content if reply.content is not None else ""}
        )
        return reply.content if reply.content is not None else ""

    async def async_chat(self, user_input: str) -> str:
        """
        异步对话方法
        """
        self.messages.append({"role": "user", "content": user_input})
        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=self.messages,  # type: ignore
        )
        reply = response.choices[0].message
        self.messages.append(
            {"role": reply.role, "content": reply.content if reply.content is not None else ""}
        )
        return reply.content if reply.content is not None else ""

    def reset_messages(self) -> None:
        """
        重置对话消息
        """
        self.messages = [{"role": "system", "content": self.role}]


class DouBaoModel:
    """
    豆包
    """
    def __init__(self, api_key: str = settings.DOUBAO_API_KEY) -> None:
        pass


model_dict = {
    "deepseek": DeepSeekModel,
    "doubao": DouBaoModel,
}


class Chatbot:
    """
    聊天机器人类，根据参数生成不同模型的实例，并提供统一的接口进行对话交互
    """

    def __init__(self, modelType: str = "deepseek", **kwargs) -> None:
        if modelType in model_dict:
            self.model = model_dict[modelType](**kwargs)
        else:
            raise ValueError(f"Unsupported model type: {modelType}")

    def send_message(self, user_input: str) -> str:
        """
        发送消息并获取回复
        """
        return self.model.chat(user_input)

    async def async_send_message(self, user_input: str) -> str:
        """
        异步发送消息并获取回复
        """
        return await self.model.async_chat(user_input)

    def reset_conversation(self) -> None:
        """
        重置对话
        """
        self.model.reset_messages()