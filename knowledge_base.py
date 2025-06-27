from docx import Document
from sentence_transformers import SentenceTransformer
from transformers import AutoModel
import faiss
import numpy as np
import os
from pathlib import Path

class KnowledgeBase:
    def __init__(self, index_path='knowledge_base.index', texts_path='knowledge_base_texts.txt'):
        # 1. 强制离线模式
        os.environ['HF_HUB_OFFLINE'] = '1'
        
        # 2. 使用POSIX格式路径（关键修改）
        model_dir = Path(r"C:\Users\文学明\Downloads\202506aicode\all-MiniLM-L6-v2").as_posix()  # 转换为正斜杠
        
        # 3. 双重验证
        if not os.path.exists(model_dir):
            raise FileNotFoundError(f"模型路径不存在: {model_dir}")
        
        # 4. 使用原生transformers加载（绕过验证）
        from transformers import AutoModel, AutoTokenizer
        model = AutoModel.from_pretrained(model_dir)
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        
        # 5. 手动构建SentenceTransformer
        from sentence_transformers import models
        word_embedding_model = models.Transformer(model_dir)
        pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension())
        self.model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
        
        print("模型已加载，向量维度:", self.model.get_sentence_embedding_dimension())
        
        self.index_path = index_path
        self.texts_path = texts_path
        self.index = None
        self.texts = []
        self.load_existing_index()

    def load_existing_index(self):
        """加载已存在的索引和文本内容"""
        if os.path.exists(self.index_path) and os.path.exists(self.texts_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.texts_path, 'r', encoding='utf-8') as f:
                self.texts = [line.strip() for line in f.readlines()]
            print("已加载现有知识库索引和文本。")

    def add_document(self, file_path):
        """添加文档到知识库"""
        doc = Document(file_path)
        text = ' '.join([para.text for para in doc.paragraphs])
        self.texts.append(text)
        embeddings = self.model.encode(text)
        if self.index is None:
            d = embeddings.shape[0]
            self.index = faiss.IndexFlatL2(d)
        embeddings = embeddings.reshape(1, -1).astype('float32')
        self.index.add(embeddings)
        self.save_index_and_texts()

    def save_index_and_texts(self):
        """保存索引和文本内容"""
        faiss.write_index(self.index, self.index_path)
        with open(self.texts_path, 'w', encoding='utf-8') as f:
            for text in self.texts:
                f.write(text + '\n')
        print("知识库索引和文本已保存。")
    
    def search(self, question, top_k=1):
        """根据问题搜索答案"""
        question_embedding = self.model.encode(question).reshape(1, -1).astype('float32')
        if self.index is None or not self.texts:
            return [""]
        distances, indices = self.index.search(question_embedding, top_k)
        results = []
        for idx in indices[0]:
            text = self.texts[idx]
            # 简单的关键词匹配，提取与问题相关的部分
            relevant_text = ' '.join([sentence for sentence in text.split('. ') if any(word in sentence for word in question.split())])
            if relevant_text:
                results.append(relevant_text)
            else:
                results.append(text)
        return results