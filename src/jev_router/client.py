import ssl

import httpx
import truststore

ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def post_request(body, key):
    """單次請求；錯誤訊息不包含 headers、金鑰或供應商回應內容。"""
    try:
        with httpx.Client(timeout=25, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as client:
            response = client.post(ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError:
        raise RuntimeError("無法連線到 Jev；沒有產生建議。") from None
    if response.is_error:
        raise RuntimeError(f"Jev 回傳 HTTP {response.status_code}；沒有產生建議。")
    try:
        return response.json()
    except ValueError:
        raise RuntimeError("Jev 回傳不是 JSON；沒有產生建議。") from None
