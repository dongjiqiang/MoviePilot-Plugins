import json
from typing import Optional, Dict
import requests
from app.log import logger


class DeepseekApi:
    """
    Deepseek API 请求类
    """
    
    def __init__(self, api_key: str,
                 api_url: str = "https://api.deepseek.com",
                 proxy: str = None,
                 model: str = "deepseek-chat"):
        self.api_key = api_key
        self.api_url = api_url
        self.proxy = proxy
        self.model = model
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }

    def get_media_name(self, filename: str) -> Optional[Dict]:
        """
        识别媒体信息
        """
        try:
            # 构建提示信息
            prompt = (f"请帮我识别以下文件名包含的影视信息：{filename}\n"
                     f"请按照以下格式返回（注意使用英文标点）:\n"
                     f"{{\"name\": \"名称\",\"year\": \"年份\",\"season\": \"季数\",\"episode\": \"集数\"}}")

            # API请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 请求数据
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            # 发送请求
            response = self.session.post(f"{self.api_url}/v1/chat/completions",
                                       headers=headers,
                                       json=data,
                                       timeout=30)

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                try:
                    return json.loads(content)
                except Exception as e:
                    logger.error(f"解析JSON失败: {str(e)}")
                    return None
            else:
                logger.error(f"API请求失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"请求Deepseek API异常: {str(e)}")
            return None 