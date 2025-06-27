import tkinter as tk
from tkinter import ttk ,filedialog
from agent import*
import threading
import subprocess
import platform
import os
from knowledge_base import KnowledgeBase
import requests
import base64

import datetime
import shutil
import re

class Interface:
    def __init__(self, root):
        self.agent = Agent()
        self.root = root
        self.root.title("大语言模型应用")
        self.root.geometry("1200x800")
        self.root.lift()
        # 设置窗口短暂置顶
        self.root.attributes("-topmost", True)  # 立即置顶
        self.root.update()  # 确保窗口已绘制
        self.root.after(500, lambda: self.root.attributes("-topmost", False))  # 0.5秒后取消置顶
        self.turn = 0

        # 可选：强制窗口获得焦点
        self.root.after(100, self.root.focus_force)

        # 创建主容器
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 对话显示区域（带滚动条）
        self.conversation_frame = tk.Frame(self.main_frame)
        self.conversation_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.conversation_frame)
        self.scrollbar = ttk.Scrollbar(self.conversation_frame, orient="vertical", command=self.canvas.yview)
        self.conversation_inner = tk.Frame(self.canvas)

        self.conversation_inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # 替换原来的 canvas.create_window(...) 行
        self.canvas.create_window((0, 0), window=self.conversation_inner, anchor="nw", tags="inner_frame")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 绑定窗口大小变化事件，动态更新气泡宽度
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 输入框和按钮容器
        self.input_frame = tk.Frame(self.main_frame)
        self.input_frame.pack(padx=10, pady=10, fill=tk.X)

        # 输入框
        self.text_input = tk.Text(self.input_frame, wrap='word', height=2, font=("Arial", 14))
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.text_input.bind("<<Modified>>", self.on_text_modified)

        # 设置 pack 不随内容改变自身大小（由我们控制）
        self.input_frame.pack_propagate(False)
        self.input_frame.config(height=60)

        self.on_new_conversation()

        # 提交按钮
        self.submit_button = tk.Button(self.input_frame, text="发送", command=self.on_submit, font=("Arial", 14), width=6)
        self.submit_button.pack(side=tk.RIGHT, padx=5)

        # 上传文档按钮
        self.upload_button = tk.Button(self.input_frame, text="上传文档", command=self.upload_document, font=("Arial", 14), width=6)
        self.upload_button.pack(side=tk.RIGHT, padx=5)

        # 输入图片按钮
        self.image_button = tk.Button(self.input_frame, text="输入图片", command=self.input_image, font=("Arial", 14), width=6)
        self.image_button.pack(side=tk.RIGHT, padx=5)

        # 知识库实例
        self.knowledge_base = KnowledgeBase()

        self.param_frame = tk.Frame(self.main_frame)
        self.param_frame.pack(padx=10, pady=5, fill=tk.X)

        self.temperature_label = tk.Label(self.param_frame, text="Temperature:", font=("Arial", 12))
        self.temperature_label.pack(side=tk.LEFT, padx=5)
        self.temperature_entry = tk.Entry(self.param_frame, font=("Arial", 12), width=6)
        self.temperature_entry.insert(0, "0.3")
        self.temperature_entry.pack(side=tk.LEFT, padx=5)

        self.top_p_label = tk.Label(self.param_frame, text="Top P:", font=("Arial", 12))
        self.top_p_label.pack(side=tk.LEFT, padx=5)
        self.top_p_entry = tk.Entry(self.param_frame, font=("Arial", 12), width=6)
        self.top_p_entry.insert(0, "1.0")
        self.top_p_entry.pack(side=tk.LEFT, padx=5)

        # 新增：对话管理相关变量
        self.history_dir = os.path.join(os.getcwd(), 'history')
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
        self.current_conversation_dir = None
        self.is_new_conversation = True # 标记是否为一次全新的对话


        # ================= 底部工具栏区域 =================
        self.bottom_toolbar = tk.Frame(self.main_frame)
        self.bottom_toolbar.pack(padx=10, pady=5, fill=tk.X, side=tk.BOTTOM)

        # 新增：历史对话菜单按钮
        self.history_menu_button = ttk.Menubutton(
            self.bottom_toolbar,
            text="历史对话",
            style="BottomToolbar.TButton"
        )
        self.history_menu = tk.Menu(self.history_menu_button, tearoff=0)
        self.history_menu_button["menu"] = self.history_menu
        self.history_menu_button.pack(side=tk.LEFT, padx=5)
        self.update_history_menu() # 初始化历史对话菜单

        # 新对话按钮
        self.new_conversation_btn = ttk.Button(
            self.bottom_toolbar,
            text="新对话",
            command=self.on_new_conversation,
            width=10,
            style="BottomToolbar.TButton"
        )
        self.new_conversation_btn.pack(side=tk.RIGHT, padx=5)


        
    # 在此处添加实际功能实现
    def _on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig("inner_frame", width=canvas_width)

    def on_text_modified(self, event=None):
        line_count = int(self.text_input.index('end-1c').split('.')[0])
        min_height = 3
        max_height = 10
        new_height = min(max(line_count, min_height), max_height)

        self.text_input.config(height=new_height)
        self.text_input.edit_modified(False)
        self.input_frame.config(height=new_height * 25)


    def on_submit(self):
        user_input = self.text_input.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        
        # 如果是全新的对话，需要先创建对话文件夹
        if self.is_new_conversation:
            # 1.立即创建一个文件夹，使用时间戳
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            temp_folder_name = f"对话_{timestamp}"

            # folder_name_prompt = f"请将以下问题精简为一个短标题，适合作为文件夹名称：'{user_input}'"
            # # 注意：这里需要一个同步的LLM调用来获取文件夹名称
            # # 为了简化，我们暂时使用时间戳作为文件夹名，您可以替换为LLM调用
            # # folder_name = self.agent.response(folder_name_prompt).strip().replace(" ", "_")
            # folder_name = f"对话_{timestamp}"

            self.current_conversation_dir = os.path.join(self.history_dir, temp_folder_name)
            if not os.path.exists(self.current_conversation_dir):
                os.makedirs(self.current_conversation_dir)
            
            self.is_new_conversation = False
            self.root.title(f"大语言模型应用 - {temp_folder_name}") # 更新窗口标题
            self.update_history_menu() # 更新历史对话菜单

            # 2.启动一个后台线程处理异步重命名
            rename_thread = threading.Thread(
                target=self._rename_conversation_folder_async,
                args=(self.current_conversation_dir, user_input), # 传递临时路径和问题
                daemon=True
            )
            rename_thread.start()

        # 获取用户输入的 temperature 和 top_p 参数
        try:
            temperature = float(self.temperature_entry.get())
            top_p = float(self.top_p_entry.get())
            self.agent.agent.temperature = temperature
            self.agent.agent.top_p = top_p
        except ValueError:
            # 使用默认值
            self.agent.agent.temperature = 0.3
            self.agent.agent.top_p = 1.0
    
        # 确保数据目录存在
        data_dir = os.path.join(os.getcwd(), '数据')  # 获取数据目录的绝对路径
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)  # 如果目录不存在，则创建
            print(f"创建数据目录: {data_dir}")
    
        # 保存用户输入到文件
        user_txt_path = os.path.join(data_dir, 'user.txt')  # 使用绝对路径
        with open(user_txt_path, 'w', encoding='utf-8') as file:
            file.write(user_input)
        print(f"用户输入已保存到文件: {user_txt_path}")
    
        # 清空输入框并重置高度
        self.text_input.delete("1.0", tk.END)
        self.text_input.config(height=3)
        self.input_frame.config(height=75)
    
        # 显示用户消息（在主线程执行）
        self._display_message(user_input, is_user=True)
        self.save_message_to_history("user", user_input) # 保存用户消息
    
        # 创建并启动工作线程
        thread = threading.Thread(
            target=self._agent_processing,
            args=(user_input,), # 将用户输入传递给线程
            daemon=True  # 设置为守护线程，随主线程结束
        )
        thread.start()

    def upload_document(self):
        """上传文档到知识库"""
        file_path = filedialog.askopenfilename(filetypes=[("Word文档", "*.docx")])
        if file_path:
            self.knowledge_base.add_document(file_path)
            self._display_message(f"已上传文档: {file_path}", is_user=False)

    def input_image(self):
        """选择图片并识别图片中的文字，自动填入输入框并提交"""
        file_path = filedialog.askopenfilename(
            initialdir=os.path.join(os.getcwd(), "图片识别"),
            filetypes=[("图片文件", "*.jpg;*.jpeg;*.png;*.bmp")]
        )
        if file_path:
            try:
                # 使用工具执行器调用图片识别工具
                from tool_executor import ToolExecutor
                executor = ToolExecutor()
                result = executor.execute_tool("recognize_image_text", {"image_path": file_path})
                
                # 提取识别结果中的文字部分
                if "图片识别结果：" in result:
                    text = result.replace("图片识别结果：", "").strip()
                else:
                    text = result
                
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, text)
                self.on_submit()  # 自动提交
            except Exception as e:
                self._show_error(f"图片识别失败: {e}")

    def doubao_image_to_text(self, image_path):
        api_key = "api"# 替换为您的豆包api
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": "ep-20250626092900-4dh5m",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请帮我识别图片中的所有文字内容，只返回文字，不要其它描述。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]
                }
            ]
        }
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _agent_processing(self,user_input):
        """在子线程中执行的AI处理逻辑"""
        try:
            # 确保数据目录存在
            data_dir = os.path.join(os.getcwd(), '数据')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                print(f"创建数据目录: {data_dir}")

            # # 读取用户输入
            # user_txt_path = os.path.join(data_dir, 'user.txt')
            # if not os.path.exists(user_txt_path):
            #     raise FileNotFoundError(f"用户输入文件不存在: {user_txt_path}")

            # with open(user_txt_path, "r", encoding='utf-8') as file:
            #     user_input = file.read().strip()+'\n'   # 去除首尾空白字符

            
            # 创建流式响应缓冲区
            self.stream_buffer = ""
            self.stream_bubble = None
        
            # 定义流式回调函数
            def stream_callback(chunk):
                self.stream_buffer += chunk
                self.root.after(0, self._update_stream_response, self.stream_buffer)
        
            # 获取AI响应（启用流式）
            ai_response = self.agent.response(user_input, stream_callback=stream_callback)
            self.save_message_to_history("assitant",ai_response)


            # 打印调试信息
            print("AI响应:", ai_response)
            if hasattr(self.agent.res, 'tool_calls'):
                print("工具调用:", [t.function.name for t in self.agent.res.tool_calls])
            if hasattr(self.agent.res, 'finish_reason'):
                print("完成原因:", self.agent.res.finish_reason)

            # 显示AI回复（通过after切换到主线程）
            print("AI响应处理完成（流式已更新界面）")
            
        except Exception as e:
            # 异常处理（通过after切换到主线程）
            print("处理异常:", e)
            error_msg = f"处理请求时出错: {str(e)}"
            self.root.after(0, self._show_error, error_msg)

    def _show_thinking_status(self):
        """显示思考状态（必须在主线程执行）"""
        self.loading_bubble = self._display_message("agent 正在思考...", is_user=False)
        self.canvas.yview_moveto(1.0)

    def _update_stream_response(self, chunk_text):
        """更新流式响应内容"""
        if not hasattr(self, 'stream_bubble') or not self.stream_bubble:
            # 首次更新，创建新气泡
            self.stream_bubble = self._display_message(chunk_text, is_user=False)
        else:
            # 更新现有气泡内容
            self.stream_bubble.config(text=chunk_text)
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
    
    def _update_ai_response(self, response):
        """更新AI回复（必须在主线程执行）"""
        if not response:  # 空响应处理
            response = "已执行工具"
    
        if hasattr(self, 'loading_bubble') and self.loading_bubble:
            # 更新现有气泡内容
            self.loading_bubble.config(text=response)
        else:
            # 创建新的气泡显示响应
            self._display_message(response, is_user=False)
    
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _show_error(self, error_msg):
        """显示错误信息（必须在主线程执行）"""
        self._display_message(f"发生错误：{error_msg}", is_user=False)
        self.canvas.yview_moveto(1.0)

    def _display_message(self, message, is_user, ai = "agent"):
        bubble_color = "#DCF8C6" if is_user else "#E5E5EA"
        align = "e" if is_user else "w"
        sender_label_text = ai
        if is_user:
            sender_label_text = "你"

        # 创建外层容器 Frame
        msg_frame = tk.Frame(self.conversation_inner)
        msg_frame.pack(anchor=align, pady=5, fill="x")

        # 发送者标签（位于头像上方）
        sender_label = tk.Label(
            msg_frame,
            text=sender_label_text,
            font=("Arial", 10, "bold"),
            fg="gray"
        )
        sender_label.grid(row=0, column=1 if is_user else 0, sticky="s" if is_user else "s")

        # 用户头像 以及 绑定
        avatar = tk.Label(
            msg_frame,
            text="👤" if is_user else "🤖",
            font=("Arial", 16),
            width=3,
            height=2,
            bg="#f0f0f0",
            relief="flat"
        )
        avatar.grid(row=1, column=1 if is_user else 0, sticky="n")

        if is_user:
            avatar.bind("<Button-1>", self.show_user_profile) # <--- 添加这行

       

        # 对话气泡
        bubble = tk.Label(
            msg_frame,
            text=message,
            wraplength=600,
            justify="left",
            bg=bubble_color,
            fg="black",
            font=("Arial", 12),
            padx=10,
            pady=5,
            borderwidth=1,
            relief="solid"
        )

        # 气泡位置：用户在左，AI 在右
        bubble.grid(row=1, column=0 if is_user else 1, sticky="ew", padx=5)

        # 设置气泡所在列的权重，使其自动扩展
        msg_frame.grid_columnconfigure(0 if is_user else 1, weight=1)

        # 更新画布滚动区域
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

        return bubble
    def _mock_ai_response(self, user_input):
        return f"这是对“{user_input}”的模拟回复。"
    
    def on_new_conversation(self):
        # 保存当前对话（如果存在）
        self.save_current_conversation()

        self.agent = Agent()
        # 清空对话容器内所有元素
        for widget in self.conversation_inner.winfo_children():
            widget.destroy()

        # 重置输入框（可选）
        self.text_input.delete("1.0", tk.END)
        self.text_input.config(height=3)
        self.input_frame.config(height=75)

        # 滚动条复位
        self.canvas.yview_moveto(0.0)

        # 新增：重置对话状态
        self.current_conversation_dir = None
        self.is_new_conversation = True
        self.root.title("大语言模型应用") # 重置标题



    # 历史对话功能
    def save_message_to_history(self, role, content):
        """将单条消息保存到当前对话文件夹"""
        if self.current_conversation_dir:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(self.current_conversation_dir, f"{timestamp}_{role}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def save_current_conversation(self):
        """在切换或关闭前，确保当前对话被处理"""
        # 这个函数可以扩展，比如标记未完成的对话等
        pass

    def update_history_menu(self):
        """更新历史对话下拉菜单"""
        self.history_menu.delete(0, tk.END) # 清空旧菜单
        
        try:
            folders = [d for d in os.listdir(self.history_dir) if os.path.isdir(os.path.join(self.history_dir, d))]
            # 按修改时间排序
            folders.sort(key=lambda x: os.path.getmtime(os.path.join(self.history_dir, x)), reverse=True)

            for folder in folders:
                self.history_menu.add_command(label=folder, command=lambda f=folder: self.load_conversation(f))
        except Exception as e:
            print(f"更新历史菜单时出错: {e}")

    def load_conversation(self, folder_name):
        """加载指定的历史对话"""
        self.on_new_conversation() # 先保存并清空当前界面

        self.current_conversation_dir = os.path.join(self.history_dir, folder_name)
        self.is_new_conversation = False
        self.root.title(f"大语言模型应用 - {folder_name}")

        try:
            message_files = sorted(os.listdir(self.current_conversation_dir))
            for filename in message_files:
                role = "user" if "_user.txt" in filename else "assistant"
                with open(os.path.join(self.current_conversation_dir, filename), 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self._display_message(content, is_user=(role == "user"))
                # 将历史消息加载到agent的messages中，以便继续对话
                self.agent.agent.messages.append({"role": role, "content": content})

        except Exception as e:
            self._show_error(f"加载对话失败: {e}")
  
    def _sanitize_filename(self, name):
        """清理字符串，使其成为合法的文件名。"""
        # 1.使用正则表达式匹配第一个有意义的字符
        match = re.search(r'[a-zA-Z0-9\u4e00-\u9fa5]', name)
        if match:
            name = name[match.start():]
        # 2.移除非法字符
        name = re.sub(r'[\\/*?:"<>|\n\r\t]', "", name) # 增加了对换行、回车、制表符的移除
        # 3.替换空格
        name = name.replace(" ", "_")
        # 4.避免名称过长
        return name[:50]

    def _rename_conversation_folder_async(self, temp_dir_path, first_question):
        """
        (在后台线程中运行)
        调用LLM获取标题并重命名文件夹。
        """
        try:
            # 1. 构造一个专门用于生成标题的prompt
            prompt = f"请将以下问题精简成一个不超过10个字的短标题，这个标题将用作文件夹名称，请不要包含任何标点符号或特殊字符：\n\n'{first_question}'"

            # 2. 调用LLM获取标题
            # 注意：这里我们直接使用 self.agent。如果担心与主对话冲突，可以创建一个新的临时Agent实例。
            agent_for_naming = Agent()
            title = agent_for_naming.response(prompt)
            # title = self.agent.response(prompt) # agent.response返回的是content字符串

            if title:
                # 3. 清理文件名
                sanitized_title = self._sanitize_filename(title.strip())
                
                if sanitized_title:
                    # 4. 计算新的文件夹路径并执行重命名
                    new_dir_path = os.path.join(self.history_dir, sanitized_title)

                    # 防止重名
                    if os.path.exists(new_dir_path):
                        timestamp = datetime.datetime.now().strftime("%H%M%S")
                        new_dir_path = f"{new_dir_path}_{timestamp}"

                    os.rename(temp_dir_path, new_dir_path)

                    # 5. 在主线程中更新UI
                    self.root.after(0, self._update_ui_after_rename, new_dir_path, os.path.basename(new_dir_path))

        except Exception as e:
            import traceback
            print("--- 异步重命名文件夹时出错 ---")
            traceback.print_exc()
            print("-----------------------------")

    def _update_ui_after_rename(self, new_path, new_name):
        """
        (在主线程中运行)
        重命名成功后更新UI元素。
        """
        # 只有当当前对话是刚刚被重命名的对话时，才更新UI
        if self.current_conversation_dir.endswith(os.path.basename(new_path)) or \
           os.path.dirname(self.current_conversation_dir) == os.path.dirname(new_path):
            
            self.current_conversation_dir = new_path
            self.root.title(f"大语言模型应用 - {new_name}")
            self.update_history_menu()

    # 用户画像功能
    def show_user_profile(self, event=None):
        """
        显示一个窗口，其中包含从对话历史中总结的用户画像。
        """
        # 创建一个新的 Toplevel 窗口
        profile_window = tk.Toplevel(self.root)
        profile_window.title("用户画像")
        profile_window.geometry("600x400")

        # 添加一个用于加载/显示画像的标签
        profile_label = tk.Label(
            profile_window,
            text="正在生成用户画像，请稍候...",
            font=("Arial", 12),
            wraplength=580,
            justify="left",
            pady=10,
            padx=10
        )
        profile_label.pack(expand=True, fill=tk.BOTH)

        # 启动一个线程来生成用户画像
        profile_thread = threading.Thread(
            target=self._generate_user_profile_async,
            args=(profile_label,),
            daemon=True
        )
        profile_thread.start()

    def _generate_user_profile_async(self, profile_label):
        """
        异步生成用户画像并更新 UI。
        """
        try:
            full_history_content = self._get_full_conversation_history()
            if not full_history_content:
                self.root.after(0, lambda: profile_label.config(text="没有足够的对话历史来生成用户画像。"))
                return

            prompt = f"请根据以下对话历史总结出用户画像（即用户特点），请用自然语言，不要包含任何标点符号或特殊字符，并且控制在50字以内:\n\n{full_history_content}"

            # 创建一个新的 Agent 实例专门用于此任务，以避免干扰
            # 主聊天代理的消息历史。
            profile_agent = Agent()
            user_profile_summary = profile_agent.response(prompt)

            self.root.after(0, lambda: profile_label.config(text=user_profile_summary))

        except Exception as e:
            import traceback
            print(f"生成用户画像时出错: {e}")
            traceback.print_exc()
            self.root.after(0, lambda: profile_label.config(text=f"生成用户画像时出错: {str(e)}"))

    def _get_full_conversation_history(self):
        """
        读取并连接所有本地对话历史。
        返回包含所有消息的单个字符串。
        """
        all_messages = []
        try:
            folders = [d for d in os.listdir(self.history_dir) if os.path.isdir(os.path.join(self.history_dir, d))]
            for folder in folders:
                folder_path = os.path.join(self.history_dir, folder)
                message_files = sorted(os.listdir(folder_path))
                for filename in message_files:
                    file_path = os.path.join(folder_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        role = "用户" if "_user.txt" in filename else "助手"
                        all_messages.append(f"{role}: {content}")
        except Exception as e:
            print(f"读取对话历史时出错: {e}")
        return "\n".join(all_messages)


# 创建主窗口并启动应用
if __name__ == "__main__":
    root = tk.Tk()
    app = Interface(root)
    root.mainloop()