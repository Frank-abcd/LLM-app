#所有可调用的工具在这里，解释在每个工具的代码里面有写
tools =[
    {
        "type":"function",
        "function":{
            "name": "exec_code",  #这是工具名字
            "description":"执行任意Python代码，并返回执行结果或报错信息", #这是工具的作用
            "parameters":{    #这是该工具的参数信息
                "type":"object",
                "properties": {   
                    "code":{
                        "type":"string",
                        "description":"要执行的Python代码片段。"
                    }
                },
                "required": ["code"]
            }
        },
        "strict": True
    },
    {
        "type":"function",
        "function":{
            "name": "create_ppt",
            "description":"智能生成PPT演示文稿，会调用大模型生成高质量的内容来填充PPT页面",
            "parameters":{
                "type":"object",
                "properties": {
                    "topic":{
                        "type":"string",
                        "description":"PPT的主题或题目，例如：'深度学习技术介绍'、'公司年度总结'等"
                    },
                    "requirements":{
                        "type":"string",
                        "description":"对PPT的特殊要求，例如：'适合学术报告'、'面向企业高管'、'包含技术细节'、'简洁明了'等，没有特殊要求可填写'无'"
                    },
                    "slide_count":{
                        "type":"integer",
                        "description":"期望的PPT页面数量（不包括标题页），建议5-15页，默认8页"
                    },
                    "style":{
                        "type":"string",
                        "description":"PPT风格类型，可选值：'学术风格'、'商务风格'、'教学风格'、'简约风格'，默认为'商务风格'"
                    },
                    "filename":{
                        "type":"string", 
                        "description":"生成的PPT文件名（可选），不需要包含.pptx后缀，如果不指定会自动生成"
                    }
                },
                "required": ["topic"]
            }
        },
        "strict": True
    },
    {
        "type":"function",
        "function":{
            "name": "recognize_image_text",
            "description":"识别图片中的文字内容，使用豆包多模态API进行OCR文字识别",
            "parameters":{
                "type":"object",
                "properties": {
                    "image_path":{
                        "type":"string",
                        "description":"图片文件的完整路径，支持jpg、jpeg、png、bmp格式"
                    }
                },
                "required": ["image_path"]
            }
        },
        "strict": True
    },
    {
        "type": "function",
        "function": {
            "name": "search_cnki",
            "description": "从中国知网搜索文献，提取关键词相关的文献信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词，用于在知网中搜索相关文献"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "搜索结果的页数，默认为1"
                    }
                },
                "required": ["keywords"]
            }
        },
        "strict": True
    }
]

