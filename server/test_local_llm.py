"""
测试本地部署模型调用（OpenAI 兼容接口）
用法：python test_local_llm.py
"""
import asyncio
from openai import AsyncOpenAI

# ========== 配置区，按实际情况修改 ==========
BASE_URL = "http://172.29.7.1:7862/v1"
API_KEY = "any-string"   # 本地服务一般不校验，随便填
MODEL = ""               # 留空则自动从 /v1/models 获取第一个模型
# ============================================


async def fetch_available_models(client: AsyncOpenAI) -> list[str]:
    """查询本地服务支持的模型列表"""
    models = await client.models.list()
    return [m.id for m in models.data]


async def chat(client: AsyncOpenAI, model: str, user_message: str) -> str:
    """发送一条消息并返回回复"""
    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )
    return completion.choices[0].message.content


async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    # 查询可用模型
    print("正在查询可用模型...")
    try:
        models = await fetch_available_models(client)
        print(f"可用模型：{models}")
    except Exception as e:
        print(f"查询模型列表失败：{e}")
        models = []

    # 确定使用的模型
    model = MODEL if MODEL else (models[0] if models else "")
    if not model:
        print("未找到可用模型，请手动设置 MODEL 变量")
        return

    print(f"\n使用模型：{model}")
    print("-" * 40)

    # 发送测试消息
    test_messages = [
        "你好，请用一句话介绍一下你自己。",
        "1 + 1 等于几？",
    ]

    for msg in test_messages:
        print(f"\n[用户] {msg}")
        try:
            reply = await chat(client, model, msg)
            print(f"[模型] {reply}")
        except Exception as e:
            print(f"调用失败：{e}")


if __name__ == "__main__":
    asyncio.run(main())
