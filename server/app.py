import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()


from router.llm_ask import llm_ask_router
from router.generate_note import generate_note_router
from router.onenote_server import FRONTEND_ORIGIN, onenote_router
from router.auth import auth_router

app = fastapi.FastAPI(
    title="LLM Read Book API",
    description="后端服务：OneNote（Microsoft Graph）与 LLM 读书问答等。",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "LLM",
            "description": "基于多模态模型的读书问答（OpenAI 兼容接口）"
        },
        {
            "name": "OneNote",
            "description": "Microsoft Graph OneNote（OAuth + 笔记本/分区/页面）"
        },
    ],
)

app.include_router(auth_router)
app.include_router(llm_ask_router)
app.include_router(onenote_router)
app.include_router(generate_note_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
