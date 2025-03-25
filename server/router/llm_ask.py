from fastapi import APIRouter

llm_ask_router = APIRouter()


@llm_ask_router.post("/llm_ask")
async def llm_ask(question: str):
    return {"question": question}
