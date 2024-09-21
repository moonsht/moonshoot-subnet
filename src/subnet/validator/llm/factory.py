from src.subnet.validator._config import ValidatorSettings
from src.subnet.validator.llm.base_llm import BaseLLM
from src.subnet.validator.llm.openai import OpenAILLM

LLM_TYPE_OPENAI = "openai"

class LLMFactory:
    @classmethod
    def create_llm(cls, settings: ValidatorSettings) -> BaseLLM:
        llm_class = {
            LLM_TYPE_OPENAI: OpenAILLM,
        }.get(settings.LLM_TYPE)

        if llm_class is None:
            raise ValueError(f"Unsupported LLM Type: {settings.LLM_TYPE}")

        return llm_class(settings=settings)