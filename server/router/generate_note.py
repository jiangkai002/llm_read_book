from fastapi import APIRouter

generate_note_router = APIRouter(prefix="/generate_note")


@generate_note_router.post("/generate_note")
async def generate_note(generate_note: GenerateNote):
    return {"message": "Hello World"}
