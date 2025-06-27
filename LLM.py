from openai import OpenAI
from tool_executor import ToolExecutor
import json
import knowledge_base
import config

class LLM:
    def __init__(self, model='qwen-plus', temperature=0.3, top_p=1.0, task="你是个好助手", tools=None):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.task = task
        self.messages = [{"role": "system", "content": task}]
        self.api = config.API_KEY
        self.base_url = config.BASE_URL
        self.tool_executor = ToolExecutor()
        self.available_tools = self._load_tools() if tools else None
        self.knowledge_base = knowledge_base.KnowledgeBase()

    def _load_tools(self):
        """加载工具定义"""
        from tools import tools
        return tools
    
    def response(self, context="None", stream_callback=None):
        """
        处理用户请求，支持流式响应和工具调用
        :param context: 用户输入
        :param stream_callback: 流式回调函数
        :return: 最终响应对象
        """
        # 知识库查询
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
            # 第一次调用模型
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
                return self._handle_stream_response(completion, stream_callback, client)
            else:
                # 非流式响应处理
                return self._handle_normal_response(completion, client)
                
        except Exception as e:
            error_msg = f"处理请求时出错：{str(e)}"
            print(f"LLM响应出错：{error_msg}")
            return self._create_error_response(error_msg)

    def _handle_stream_response(self, completion, stream_callback, client):
        """
        处理流式响应，包括可能的工具调用
        """
        collected_chunks = []
        collected_messages = []
        full_response = ""
        
        for chunk in completion:
            collected_chunks.append(chunk)
            chunk_message = chunk.choices[0].delta
            collected_messages.append(chunk_message)
            
            
            # 检查是否有工具调用
                
            if chunk_message.content:
                full_response += chunk_message.content
                stream_callback(chunk_message.content)

        tool_calls = []
        for delta in collected_messages:
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    # 新的工具调用开始
                    if tool_call_delta.index >= len(tool_calls):
                        tool_calls.append({
                            "id": tool_call_delta.id or "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                            })
                        current_tool_call = tool_calls[-1]
                            
                            # 更新工具调用信息
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            current_tool_call["function"]["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments
        # 保存完整的响应消息
        response_message = {
            "role": "assistant",
            "content": full_response
        }
        if tool_calls:
            response_message['tool_calls'] = tool_calls
        self.messages.append(response_message)

        if tool_calls:
                # 工具调用中断流式，转为普通处理
                return self._handle_tool_calls_in_stream(
                    tool_calls, 
                    client, 
                    stream_callback,
                    full_response
                )
        
        
        return self._create_success_response(response_message)

    def _handle_tool_calls_in_stream(self, tool_calls, client, stream_callback, partial_response):
        """
        处理流式响应中的工具调用
        """
        # 先显示已收集的部分响应
        if partial_response:
            stream_callback(partial_response)
        
        # 通知用户即将调用工具
        tool_names = [tc['function']['name'] for tc in tool_calls]
        stream_callback(f"\n\n调用工具: {', '.join(tool_names)}...\n")
        
        # 执行工具
        tool_responses = []
        for tool_call in tool_calls:
            tool_name = tool_call['function']['name']
            tool_args = json.loads(tool_call['function']['arguments'])
            
            tool_response = self.tool_executor.execute_tool(tool_name, tool_args)
            self.messages.append({"role":"tool","tool_call_id": tool_call['id'],"content": tool_response})
            tool_responses.append(tool_response)
            
            self.messages.append({
                "role": "tool",
                "content": tool_response,
                "tool_call_id": tool_call['id'],
                "name": tool_name
            })
        
        # 通知用户工具执行完成
        stream_callback("\n工具执行完成，生成最终回答...\n")
        
        # 第二次调用模型，带上工具执行结果
        second_completion = client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=True  # 继续流式
        )
        
        # 处理最终流式响应
        final_response = ""
        for chunk in second_completion:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                final_response += content
                stream_callback(content)
        
        # 保存最终响应
        response_message = {
            "role": "assistant",
            "content": final_response
        }
        self.messages.append(response_message)
        
        return self._create_success_response(response_message)

    def _handle_normal_response(self, completion, client):
        """
        处理普通响应，包括工具调用
        """
        response_message = completion.choices[0].message
        
        # 检查是否需要调用工具
        if response_message.tool_calls:
            # 执行工具
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

            # 第二次调用模型
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
        
        # 没有工具调用，直接返回
        self.messages.append(response_message)
        return completion.choices[0]

    def _create_success_response(self, message):
        """创建成功响应对象"""
        return type('obj', (object,), {
            'message': type('obj', (object,), message),
            'finish_reason': 'stop'
        })

    def _create_error_response(self, error_msg):
        """创建错误响应对象"""
        response_message = {
            "role": "assistant",
            "content": error_msg
        }
        self.messages.append(response_message)
        return type('obj', (object,), {
            'message': type('obj', (object,), response_message),
            'finish_reason': 'error'
        })