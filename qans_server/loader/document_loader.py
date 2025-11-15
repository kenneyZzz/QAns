"""
文档加载器模块
支持多种文档格式的加载，包括txt、pdf、docx、md、xlsx、xls等
"""
from pathlib import Path
from typing import List
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
    UnstructuredExcelLoader,
    UnstructuredHTMLLoader,
)
from langchain_core.documents import Document


class DocumentLoader:
    """统一的文档加载器，支持多种文档格式"""
    
    # 支持的文档格式及其对应的加载器
    SUPPORTED_FORMATS = {
        '.txt': TextLoader,
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.md': UnstructuredMarkdownLoader,
        '.markdown': UnstructuredMarkdownLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.xls': UnstructuredExcelLoader,
        '.html': UnstructuredHTMLLoader,
        '.htm': UnstructuredHTMLLoader,
        '.json': TextLoader,
    }
    
    def __init__(self, encoding: str = 'utf-8'):
        """
        初始化文档加载器
        
        Args:
            encoding: 文本文件的编码格式，默认utf-8
        """
        self.encoding = encoding
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        加载单个文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            文档列表，每个文档包含page_content和metadata
            
        Raises:
            ValueError: 文件格式不支持或文件不存在
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_ext = file_path.suffix.lower()
        
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的文件格式: {file_ext}。"
                f"支持的格式: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )
        
        loader_class = self.SUPPORTED_FORMATS[file_ext]
        
        # 根据文件类型选择不同的加载方式
        if file_ext == '.txt':
            loader = loader_class(str(file_path), encoding=self.encoding)
        elif file_ext in ['.xlsx', '.xls']:
            # Excel文件使用elements模式，将每个工作表解析为独立元素
            loader = loader_class(str(file_path), mode="elements")
        else:
            loader = loader_class(str(file_path))
        
        try:
            documents = loader.load()
            
            # 为每个文档添加文件路径元数据
            for doc in documents:
                if 'source' not in doc.metadata:
                    doc.metadata['source'] = str(file_path)
                doc.metadata['file_name'] = file_path.name
                doc.metadata['file_type'] = file_ext[1:]  # 去掉点号
            
            return documents
        except Exception as e:
            raise RuntimeError(f"加载文档失败 {file_path}: {str(e)}")
    
    def load_directory(self, directory_path: str, recursive: bool = True) -> List[Document]:
        """
        加载目录下的所有支持的文档
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归加载子目录，默认True
            
        Returns:
            所有文档的列表
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not directory_path.is_dir():
            raise ValueError(f"路径不是目录: {directory_path}")
        
        all_documents = []
        
        # 获取所有支持的文档文件
        pattern = '**/*' if recursive else '*'
        for file_path in directory_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                try:
                    documents = self.load_document(str(file_path))
                    all_documents.extend(documents)
                    print(f"✓ 成功加载: {file_path.name}")
                except Exception as e:
                    print(f"✗ 加载失败: {file_path.name} - {str(e)}")
        
        return all_documents
    
    def load_files(self, file_paths: List[str]) -> List[Document]:
        """
        批量加载多个文档文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            所有文档的列表
        """
        all_documents = []
        
        for file_path in file_paths:
            try:
                documents = self.load_document(file_path)
                all_documents.extend(documents)
                print(f"✓ 成功加载: {Path(file_path).name}")
            except Exception as e:
                print(f"✗ 加载失败: {Path(file_path).name} - {str(e)}")
        
        return all_documents
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """
        获取支持的文件格式列表
        
        Returns:
            支持的文件格式列表
        """
        return list(DocumentLoader.SUPPORTED_FORMATS.keys())


