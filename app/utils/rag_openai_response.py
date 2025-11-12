from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai = OpenAI()


def get_rag_openai_response(query: str, relevant_context: str) -> str:
    """Get a response from the RAG model using OpenAI."""

    prompt = f"""
    You are a helpful AI assistant that can answer questions based on the available context provided by the contexts of a PDF file. 
    The context is provided in the following format:
    {relevant_context}
    Your answer should be concise and accurate based on the context provided. Do not hallucinate or make up information.
    """

    response = openai.chat.completions.create(
        model="gpt-5",
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
