import json
import subprocess
import os
import requests
import base64
from typing import Dict, Any, Optional

class ToolExecutor:
    def __init__(self):
        self.available_tools = self._load_tools()
        
    def _load_tools(self) -> Dict[str, Dict]:
        """加载所有可用工具定义"""
        try:
            from tools import tools
            return {tool["function"]["name"]: tool for tool in tools}
        except ImportError:
            print("Error: Failed to load tools definitions")
            return {}
        except Exception as e:
            print(f"Error loading tools: {str(e)}")
            return {}
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        执行指定工具
        :param tool_name: 工具名称
        :param parameters: 工具参数
        :return: 执行结果字符串
        """
        if not tool_name or not isinstance(tool_name, str):
            return "Error: Invalid tool name"
            
        if tool_name not in self.available_tools:
            return f"Error: Tool '{tool_name}' not found."
        
        # 验证参数类型
        if not isinstance(parameters, dict):
            return "Error: Parameters must be a dictionary"
        
        try:
            # 根据工具名称路由到对应的处理方法
            handler = getattr(self, f"_handle_{tool_name}", None)
            if handler:
                return handler(parameters)
            
            # 兼容旧版处理方式
            return self._legacy_tool_handler(tool_name, parameters)
            
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
    
    # 新版工具处理方法（更模块化）
    def _handle_exec_code(self, params: Dict[str, Any]) -> str:
        """处理代码执行"""
        code = params.get("code", "")
        print("代码执行")
        if not code:
            return "Error: No code provided to execute."
        return self._execute_code(code)
    
    def _handle_create_ppt(self, params: Dict[str, Any]) -> str:
        """处理PPT生成请求"""
        topic = params.get("topic", "")
        print("ppt")
        if not topic:
            return "Error: Topic is required for PPT generation."
        
        requirements = params.get("requirements", "")
        filename = params.get("filename", "")
        
        return self._create_presentation(topic, requirements, filename)
    
    def _handle_recognize_image_text(self, params: Dict[str, Any]) -> str:
        """处理图片文字识别请求"""
        image_path = params.get("image_path", "")
        print("图片识别")
        if not image_path:
            return "Error: Image path is required for text recognition."
        
        if not os.path.exists(image_path):
            return f"Error: Image file not found at path: {image_path}"
        
        return self._recognize_image_text(image_path)
    
    # 工具具体实现方法
    def _execute_code(self, code: str) -> str:
        """执行Python代码"""
        try:
            local_vars = {}
            global_vars = {}
            exec(code, global_vars, local_vars)
            result = local_vars.get('result', None)
            
            if result is not None:
                return str(result)
            return "Code executed successfully but no result returned."
        except Exception as e:
            return f"Code execution error: {str(e)}"

    def _create_presentation(self, topic: str, requirements: str = "", filename: str = "") -> str:
        """创建PPT演示文稿"""
        try:
            # 导入PPT生成器
            from ppt_generator import create_presentation
            
            # 调用PPT生成功能
            result = create_presentation(topic, requirements, filename)
            
            return result
            
        except ImportError:
            return "Error: PPT生成器模块未找到，请确保ppt_generator.py文件存在"
        except Exception as e:
            return f"Error: PPT生成失败 - {str(e)}"
    
    def _recognize_image_text(self, image_path: str) -> str:
        """识别图片中的文字内容"""
        try:
            api_key = "45b774cc-7c8b-4278-b0a3-337f12a8a356"
            
            # 读取图片并转换为base64
            with open(image_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode()
            
            # 根据文件扩展名确定MIME类型
            file_ext = os.path.splitext(image_path)[1].lower()
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_type_map.get(file_ext, 'image/jpeg')
            
            url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # 尝试不同的请求格式
            data = {
                "model": "ep-20250626092900-4dh5m",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请帮我识别图片中的所有文字内容，只返回文字，不要其它描述。"},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_base64}"}}
                        ]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1
            }
            
            print(f"发送请求到: {url}")
            print(f"模型: {data['model']}")
            print(f"图片格式: {mime_type}")
            print(f"图片大小: {len(img_base64)} 字符")
            
            resp = requests.post(url, headers=headers, json=data)
            
            if resp.status_code != 200:
                print(f"API响应状态码: {resp.status_code}")
                print(f"API响应内容: {resp.text}")
                return f"图片识别失败：API返回错误 {resp.status_code} - {resp.text}"
            
            result = resp.json()["choices"][0]["message"]["content"]
            return f"图片识别结果：{result}"
            
        except Exception as e:
            import traceback
            print(f"图片识别异常: {str(e)}")
            print(f"异常详情: {traceback.format_exc()}")
            return f"图片识别失败：{str(e)}"

if __name__ == "__main__":
    executor = ToolExecutor()
    
    # 测试正常情况
    print("=== 正常测试 ===")
    print(executor.execute_tool("exec_code", {"code": "result = 5 + 1"}))  # 应输出 6
    print(executor.execute_tool("writer", {"theme": "AI发展", "title": "AI的未来"}))
    
    # 测试PPT生成
    print("\n=== PPT生成测试 ===")
    ppt_result = executor.execute_tool("create_ppt", {
        "topic": "机器学习基础",
        "requirements": "详细介绍",
        "filename": "ML基础教程"
    })
    print(ppt_result)
    
    # 测试错误情况
    print("\n=== 错误测试 ===")
    print(executor.execute_tool("exec_code", {}))  # 缺少代码参数
    print(executor.execute_tool("unknown_tool", {}))  # 未知工具
    print(executor.execute_tool("writer", {"theme": "只有主题"}))  # 缺少标题