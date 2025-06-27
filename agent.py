from LLM import*
from agent_prompt import*
import json

class Agent:
    def __init__(self):
        self.system_prompt = agent_prompt
        # 初始化主代理，这个代理接收用户的命令
        #self.agent = LLM(task = self.system_prompt,  model='qwen-max-longcontext',tools=True)
        self.agent = LLM(tools=True)

    def response(self, user_question="None", stream_callback=None):    # 添加stream_callback参数
        # 将stream_callback传递给LLM的response方法
        self.res = self.agent.response(user_question, stream_callback=stream_callback)
        return self.res.message.content   # 包括文本回复信息
    
if __name__ == '__main__':
    agent = Agent()
    res= agent.response("执行print(5+1)")
    print(res)