import msal
import os

client_id = "***"
client_secret="***"
tenant_id = '***'
authority = f"https://login.microsoftonline.com/{tenant_id}"

os.environ['http_proxy'] = 'http://localhost:7897'
os.environ['https_proxy'] = 'http://localhost:7897'

# 客户端模式的 Scope 固定为 /.default
scopes = ["https://graph.microsoft.com/.default"]

app = msal.ConfidentialClientApplication(
    client_id, 
    authority=authority,
    client_credential=client_secret
)

#直接请求令牌
result = app.acquire_token_for_client(scopes=scopes)

if "access_token" in result:
    access_token = result['access_token']
    print(access_token)
    print("后台服务令牌获取成功")
else:
    print(result)
    print(f"错误: {result.get('error')}")