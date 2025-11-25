from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda


def make_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a friendly assistant that greets users."),
            ("user", "Say hello to {name}"),
        ]
    )
    # Fake LLM for offline demo; swap with a real model later (e.g., ChatOpenAI).
    fake_llm = RunnableLambda(
        lambda inputs: f"Hello, {inputs['name']}! (LangChain placeholder)"
    )
    return prompt | fake_llm | StrOutputParser()


def main() -> None:
    chain = make_chain()
    result = chain.invoke({"name": "LegalScraper"})
    print(f"[agent-demo] {result}")


if __name__ == "__main__":
    main()
