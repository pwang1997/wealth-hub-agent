

import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPManager:
    def __init__(self, config_file: str = "mcp_config.json"):
        
        load_dotenv()
        self.config = self._load_config(config_file)
        
        # 初始化大模型
        self.llm = self._init_llm()
        
        # MCP客户端和工具
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List = []
        self.tools_by_server: Dict[str, List] = {}
        
        self.conversation_history: List[Dict[str, str]] = []
        
        def _load_config(self, config_file: str) -> Dict[str, Any]:
            """加载配置文件"""
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"配置文件加载成功: {config_file}")
                return config
            except FileNotFoundError:
                print(f"⚠️ 配置文件未找到: {config_file}，使用默认配置")
                return {"servers": {}, "agent_permissions": {}}
            except json.JSONDecodeError as e:
                print(f"❌ 配置文件格式错误: {e}")
                return {"servers": {}, "agent_permissions": {}}