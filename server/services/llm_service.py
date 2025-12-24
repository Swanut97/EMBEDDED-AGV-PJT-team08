from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from services.mqtt_service import MQTTService
from util.prompt import getPersona
from schemas.chat_schema import Result

load_dotenv()


class LLMService:
    def __init__(self):
        self.mqtt = MQTTService()
        self.mqtt.connect()

        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.5,
        )

        self.structured_llm = llm.with_structured_output(Result)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "{persona}"),
            ("human", "{question}"),
        ])

        self.chain = self.prompt | self.structured_llm

    async def ask(self, question: str) -> Result:
        try:
            result = await self.chain.ainvoke({
                "persona": getPersona(),
                "question": question
            })
            print(result)
            self.mqtt.publish("AGV/CMD/1", result.command)
            return result

        except Exception as e:
            print(f"LLM Error: {e}")

            return Result(
                response="죄송합니다. 처리 중 오류가 발생했습니다.",
                command="None"
            )