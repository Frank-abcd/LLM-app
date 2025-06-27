from openai import OpenAI
from tool_executor import ToolExecutor
import json
import knowledge_base

class LLM:
    def __init__(self, model='qwen-plus', temperature=0.3, top_p=1.0, task="你是个好助手", tools=None):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.task = task
        self.messages = [{"role": "system", "content": task}]
        self.api = 'sk-c817ea30ea944b888b0f45e6409c34c2'
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.tool_executor = ToolExecutor()
        self.available_tools = self._load_tools() if tools else None
        self.knowledge_base = knowledge_base.KnowledgeBase()

    def _load_tools(self):
        """加载工具定义"""
        from tools import tools
        return tools
    
    def response(self, context="None", stream_callback=None):
        """
        新增stream_callback参数，用于流式传输时的回调函数
        当stream_callback不为None时，启用流式响应
        """
        # 如果知识库存在，先搜索相关答案
        if self.knowledge_base:
            search_results = self.knowledge_base.search(context, top_k=3)
            if search_results:
                context = f"根据文档内容回答问题：{' '.join(search_results)}\n问题：{context}"

        # 记忆功能
        if context != "None":
            self.messages.append({"role": "user", "content": context})
        
        client = OpenAI(
            api_key=self.api,
            base_url=self.base_url,
        )
        
        # 判断是否启用流式响应
        stream = stream_callback is not None
        
        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature,
                top_p=self.top_p,
                tools=self.available_tools,
                tool_choice="auto" if self.available_tools else None,
                stream=stream
            )
            
            if stream:
                # 流式响应处理
                collected_chunks = []
                collected_messages = []
                full_response = ""
                
                for chunk in completion:
                    collected_chunks.append(chunk)
                    chunk_message = chunk.choices[0].delta
                    collected_messages.append(chunk_message)
                    
                    if chunk_message.content:
                        full_response += chunk_message.content
                        stream_callback(chunk_message.content)
                
                # 保存完整的响应消息
                response_message = {
                    "role": "assistant",
                    "content": full_response
                }
                self.messages.append(response_message)
                
                return type('obj', (object,), {
                    'message': type('obj', (object,), response_message),
                    'finish_reason': 'stop'
                })
            else:
                # 非流式响应处理
                response_message = completion.choices[0].message
                
                # 检查是否需要调用工具
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        tool_response = self.tool_executor.execute_tool(tool_name, tool_args)
                        
                        self.messages.append({
                            "role": "tool",
                            "content": tool_response,
                            "tool_call_id": tool_call.id,
                            "name": tool_name
                        })

                    # 重新调用模型，带上工具执行结果
                    second_completion = client.chat.completions.create(
                        model=self.model,
                        messages=self.messages,
                        temperature=self.temperature,
                        top_p=self.top_p
                    )
                
                    # 更新最终回复
                    final_response = second_completion.choices[0].message
                    self.messages.append(final_response)
                    return second_completion.choices[0]            
                
                self.messages.append(response_message)
                return completion.choices[0]
                
        except Exception as e:
            print(f"LLM响应出错：{str(e)}")
            response_message = {
                "role": "assistant",
                "content": f"处理请求时出错：{str(e)}"
            }
            self.messages.append(response_message)
            return type('obj', (object,), {
                'message': type('obj', (object,), response_message),
                'finish_reason': 'error'
            })