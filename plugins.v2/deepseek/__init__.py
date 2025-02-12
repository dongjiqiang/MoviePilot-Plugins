from typing import Any, List, Dict, Tuple

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.plugins.deepseek.deepseek_api import DeepseekApi
from app.schemas.types import EventType, ChainEventType


class Deepseek(_PluginBase):
    # 插件名称
    plugin_name = "Deepseek"
    # 插件描述
    plugin_desc = "使用Deepseek AI进行媒体信息识别。(测试中)"
    # 插件图标
    plugin_icon = "deepseek.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "dongjiqiang"
    # 作者主页
    author_url = "https://github.com/dongjiqiang"
    # 插件配置项ID前缀
    plugin_config_prefix = "deepseek_"
    # 加载顺序
    plugin_order = 16
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    deepseek = None
    _enabled = False
    _proxy = False
    _recognize = False
    _api_url = None
    _api_key = None
    _model = None

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._proxy = config.get("proxy")
            self._recognize = config.get("recognize")
            self._api_url = config.get("api_url")
            self._api_key = config.get("api_key")
            self._model = config.get("model")
            if self._api_url and self._api_key:
                self.deepseek = DeepseekApi(api_key=self._api_key, 
                                          api_url=self._api_url,
                                          proxy=settings.PROXY if self._proxy else None,
                                          model=self._model)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'proxy',
                                            'label': '使用代理服务器',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'recognize',
                                            'label': '辅助识别',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_url',
                                            'label': 'Deepseek API Url',
                                            'placeholder': 'https://api.deepseek.com',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_key',
                                            'label': 'API Key'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'model',
                                            'label': '自定义模型',
                                            'placeholder': 'deepseek-chat',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '开启辅助识别后，内置识别功能无法正常识别种子/文件名称时，将使用Deepseek进行AI辅助识别，可以提升动漫等非规范命名的识别成功率。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "proxy": False,
            "recognize": False,
            "api_url": "https://api.deepseek.com",
            "api_key": "",
            "model": "deepseek-chat"
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(ChainEventType.NameRecognize)
    def recognize(self, event: Event):
        """
        监听识别事件，使用Deepseek辅助识别名称
        """
        if not self.deepseek:
            return
        if not self._recognize:
            return
        if not event.event_data:
            return
        title = event.event_data.get("title")
        if not title:
            return
        # 调用Deepseek
        response = self.deepseek.get_media_name(filename=title)
        logger.info(f"Deepseek返回结果：{response}")
        if response and response.get("name"):
            event.event_data = {
                'title': title,
                'name': response.get("name"),
                'year': response.get("year"),
                'season': response.get("season"),
                'episode': response.get("episode")
            }

    def stop_service(self):
        """
        退出插件
        """
        pass 