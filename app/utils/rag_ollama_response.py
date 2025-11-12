import asyncio

import ollama

client = ollama.Client(host="http://ollama:11434")


async def get_rag_ollama_response(query: str, relevant_context: str) -> str:
    """Get a response from the RAG model using Ollama."""

    prompt = f"""Based on this context from a PDF:
      {relevant_context}

      Question: {query}

      Answer concisely using only the context provided. Do not make up information.
    """

    def _generate():
        response = client.generate(
            model="llama3.1:4b",
            prompt=prompt,
            stream=False,
            options={
                "temperature": 0.7,  
                "num_predict": 500,  
            },
        )
        return str(response["response"])

    response = await asyncio.to_thread(_generate)
    return response
