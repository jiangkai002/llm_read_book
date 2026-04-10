import msal

client_id = '***REMOVED_CLIENT_ID***'
client_secret = '***REMOVED_CLIENT_SECRET***'
tenant_id = 'common'
authority = f"https://login.microsoftonline.com/{tenant_id}"

# 客户端模式的 Scope 固定为 /.default
scopes = ["https://graph.microsoft.com/.default"]

app = msal.ConfidentialClientApplication(
    client_id, 
    authority=authority,
    client_credential=client_secret
)

# 直接请求令牌
result = app.acquire_token_for_client(scopes=scopes)

if "access_token" in result:
    access_token = result['access_token']
    print("后台服务令牌获取成功")
else:
    print(f"错误: {result.get('error')}")