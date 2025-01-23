import re
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import set_key

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.utils.string import StringUtils

lock = threading.Lock()


class GhProxyMonitor(_PluginBase):
    # 插件名称
    plugin_name = "GhProxy监控"
    # 插件描述
    plugin_desc = "监控https://ghproxy.link网站，获取当前可用加速地址。""
    # 插件图标
    plugin_icon = "github.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "dongjiqiang"
    # 作者主页
    author_url = "https://github.com/dongjiqiang"
    # 插件配置项ID前缀
    plugin_config_prefix = "GhProxyMonitor_"
    # 加载顺序
    plugin_order = 10
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _scheduler = None
    _enabled = False
    _onlyonce = False
    _notify = False
    _cron = None
    _env_path = None
    _url = "https://ghproxy.link/"

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._notify = config.get("notify")
            self._cron = config.get("cron")
            self._env_path = config.get("env_path", settings.CONFIG_PATH / "app.env")

        self.stop_service()

        if self.get_state() or self._onlyonce:
            if self._onlyonce:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info(f"GhProxy监控服务启动，立即运行一次")
                self._scheduler.add_job(func=self.check_ghproxy, trigger='date',
                                      run_date=datetime.now(
                                          tz=settings.TZ) + timedelta(seconds=3))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "enabled": self._enabled,
                    "notify": self._notify,
                    "onlyonce": self._onlyonce,
                    "cron": self._cron
                })
                if self._scheduler.get_jobs():
                    self._scheduler.print_jobs()
                    self._scheduler.start()

    def get_state(self) -> bool:
        return True if self._enabled and self._cron else False

    def get_service(self) -> List[Dict[str, Any]]:
        if self.get_state():
            return [{
                "id": "GhProxyMonitor",
                "name": "GhProxy监控服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.check_ghproxy,
                "kwargs": {}
            }]
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
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
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'env_path',
                                            'label': '环境变量文件路径',
                                            'placeholder': 'app.env路径',
                                            'hint': '用于保存GITHUB_PROXY环境变量',
                                            'persistent-hint': True
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
                                    'md': 6
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
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '发送通知',
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
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '执行周期',
                                            'placeholder': '0 */1 * * *'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
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
            "notify": False,
            "onlyonce": False,
            "cron": '0 */1 * * *'
        }

    def stop_service(self):
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error(f"停止GhProxy监控服务失败：{str(e)}")

    def check_ghproxy(self):
        """
        检查ghproxy.link网站
        """
        try:
            # 获取网页内容
            response = requests.get(self._url, timeout=10)
            response.raise_for_status()
            
            # 解析网页
            soup = BeautifulSoup(response.text, 'html.parser')
            addresses = []
            
            # 查找class="domain-name"下的a标签
            for item in soup.find_all(class_='domain-name'):
                a_tag = item.find('a')
                if a_tag and a_tag.text:
                    addresses.append(a_tag.text.strip())
            
            if addresses:
                # 只取第一个地址
                address = addresses[0]
                logger.info(f"获取到可用地址：{address}")
                
                # 保存数据
                self.save_data("address", address)
                self.save_data("last_check_time", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                # 更新配置
                self.update_config({
                    "last_address": address,
                    "last_check_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # 写入环境变量
                set_key(self._env_path, "GITHUB_PROXY", address)
                
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title=f"【GhProxy监控】",
                        text=f"当前可用地址：{address}"
                    )
            else:
                logger.warn("未找到可用地址")
                self.save_data("address", "")
                
        except Exception as e:
            logger.error(f"检查ghproxy.link失败：{str(e)}")
