from agents import OpenAIChatCompletionsModel,AsyncOpenAI,RunConfig
import os
from dotenv import load_dotenv

_: bool = load_dotenv()
gemini_api_key = os.getenv("gemini_api_key")


external_client = AsyncOpenAI(
    api_key= gemini_api_key,
    base_url= "https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model = "gemini-2.5-flash",
    openai_client= external_client
)

config = RunConfig(
    model=model,
    model_provider = external_client,
    tracing_disabled=True,
)