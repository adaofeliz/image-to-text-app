import os

from openai import OpenAI
from dotenv import load_dotenv

from app.utils.constants import model_names, models_supported

load_dotenv()


def get_rag_cloudmodel_response(query: str, relevant_context: str, model: str) -> str:
    """Get a response from the RAG model using Cloud Models."""

    prompt = f"""
    You are a helpful AI assistant that can answer questions based on the available context provided by the contexts of a PDF file. 
    The context is provided in the following format:
    {relevant_context}
    Your answer should be concise and accurate based on the context provided. Do not hallucinate or make up information.
    """

    client = None  # type: ignore
    if model == models_supported["gemini"]:
        client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    elif model == models_supported["deepseek"]:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
    elif model == models_supported["openai"]:
        client = OpenAI()
    else:
        raise ValueError(f"Invalid model: {model}")

    response = client.chat.completions.create(
        model=model_names[model],
        stream=False,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    )

    return str(response.choices[0].message.content)
