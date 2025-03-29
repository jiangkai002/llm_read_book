from pydantic import BaseModel


class Config(BaseModel):
    api_key: str
    llm_model: str


config = Config()
