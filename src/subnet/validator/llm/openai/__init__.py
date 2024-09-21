from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from src.subnet.validator._config import ValidatorSettings
from src.subnet.validator.llm.base_llm import BaseLLM
from src.subnet.validator.llm.prompt_reader import read_local_file
from src.subnet.validator.llm.utils import split_messages_into_chunks
from loguru import logger


class OpenAILLM(BaseLLM):
    def __init__(self, settings: ValidatorSettings) -> None:
        self.settings = settings
        self.chat_gpt4o = ChatOpenAI(api_key=settings.LLM_API_KEY, model="gpt-4o", temperature=0)
        self.MAX_TOKENS = 128000

    def is_tweet_sentiment_positive(self, tweet_text) -> bool:
        validation_template_path = f"openai/prompts/classification_prompt.txt"
        prompt_template = read_local_file(validation_template_path)

        if not prompt_template:
            raise Exception("Failed to read prompt template")

        if not tweet_text:
            logger.warning("The tweet text is empty")
            return False

        try:
            substituted_template = prompt_template.replace('{tweet_text}', tweet_text)
        except Exception as e:
            logger.error(f"Error during prompt/query substitution: {e}")
            raise Exception("Error formatting validation prompt with prompt and query") from e

        try:
            messages = [SystemMessage(content=substituted_template)]
            message_chunks = split_messages_into_chunks(messages)
            ai_responses = []
            for chunk in message_chunks:
                ai_message = self.chat_gpt4o.invoke(chunk)
                ai_responses.append(ai_message.content)
            combined_response = "\n".join(ai_responses)

            if 'positive' in combined_response.lower():
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"LlmQuery validation error: {e}")
            raise Exception("LLM_ERROR_VALIDATION_FAILED")
