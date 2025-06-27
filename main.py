from interface import*
from knowledge_base import KnowledgeBase
from agent import Agent

# 初始化知识库
knowledge_base = KnowledgeBase()

# 初始化 Agent 并传递知识库
Agent.knowledge_base = knowledge_base

root = tk.Tk()   #启动界面
app = Interface(root)
root.mainloop()