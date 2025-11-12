import ollama


client = ollama.Client(host="http://ollama:11434")


def get_rag_ollama_response(query: str, relevant_context: str) -> str:
    """Get a response from the RAG model using Ollama."""

    prompt = f"""
    You are a helpful AI assistant that can answer questions based on the available context provided by the contexts of a PDF file. 
    The context is provided in the following format:
    {relevant_context}
    Your answer should be concise and accurate based on the context provided. Do not hallucinate or make up information.

    Here's the question:
    {query}
    """

    response = client.generate(model="llama3.1:8b", prompt=prompt, stream=False)

    return str(response["response"])
