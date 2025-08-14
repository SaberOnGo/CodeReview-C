#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#parse.py
"""
代码解析器 - 基于tree-sitter的C语言代码解析
"""

import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
from pathlib import Path
from typing import List, Dict, Any, Optional
import chardet

class CodeParser:
    """C语言代码解析器"""
    
    def __init__(self):
        # 初始化tree-sitter
        C_LANGUAGE = Language(tsc.language(), "c")
        self.parser = Parser()
        self.parser.set_language(C_LANGUAGE)
        
        # 文件统计
        self.file_count = 0
        self.parsed_files = []
        
    def detect_encoding(self, file_path: Path) -> str:
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except Exception:
            return 'utf-8'
    
    def read_file_content(self, file_path: Path) -> Optional[str]:
        """安全读取文件内容"""
        encoding = self.detect_encoding(file_path)
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None
    
    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """解析单个C文件"""
        content = self.read_file_content(file_path)
        if not content:
            return None
            
        try:
            # 解析为AST
            tree = self.parser.parse(bytes(content, 'utf8'))
            
            file_info = {
                'path': file_path,
                'content': content,
                'tree': tree,
                'root_node': tree.root_node,
                'lines': content.split('\n'),
                'line_count': len(content.split('\n')),
                'encoding': self.detect_encoding(file_path)
            }
            
            self.parsed_files.append(file_info)
            self.file_count += 1
            
            return file_info
            
        except Exception as e:
            print(f"解析文件失败 {file_path}: {e}")
            return None
    
    def find_c_files(self, directory: Path) -> List[Path]:
        """查找目录下所有C文件"""
        c_extensions = ['.c', '.h', '.cpp', '.hpp', '.cc', '.cxx']
        c_files = []
        
        for ext in c_extensions:
            c_files.extend(directory.rglob(f'*{ext}'))
            
        return sorted(c_files)
    
    def parse_project(self, project_path: Path) -> List[Dict[str, Any]]:
        """解析整个项目"""
        print(f"开始解析项目: {project_path}")
        
        c_files = self.find_c_files(project_path)
        print(f"找到 {len(c_files)} 个C文件")
        
        parsed_results = []
        for file_path in c_files:
            result = self.parse_file(file_path)
            if result:
                parsed_results.append(result)
                
        print(f"成功解析 {len(parsed_results)} 个文件")
        return parsed_results
    
    def get_node_text(self, node, content: str) -> str:
        """获取AST节点对应的源代码文本"""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content[start_byte:end_byte]
    
    def find_nodes_by_type(self, root_node, node_type: str) -> List:
        """递归查找指定类型的所有节点"""
        nodes = []
        
        def traverse(node):
            if node.type == node_type:
                nodes.append(node)
            for child in node.children:
                traverse(child)
                
        traverse(root_node)
        return nodes
    
    def find_function_definitions(self, root_node) -> List[Dict[str, Any]]:
        """查找所有函数定义"""
        functions = []
        func_nodes = self.find_nodes_by_type(root_node, 'function_definition')
        
        for func_node in func_nodes:
            # 查找函数名
            declarator = None
            for child in func_node.children:
                if child.type == 'function_declarator':
                    declarator = child
                    break
                    
            if declarator:
                func_name = None
                for child in declarator.children:
                    if child.type == 'identifier':
                        func_name = child
                        break
                        
                if func_name:
                    functions.append({
                        'node': func_node,
                        'name_node': func_name,
                        'declarator': declarator,
                        'start_line': func_node.start_point[0] + 1,
                        'end_line': func_node.end_point[0] + 1
                    })
                    
        return functions
    
    def find_variable_declarations(self, root_node) -> List[Dict[str, Any]]:
        """查找所有变量声明"""
        variables = []
        decl_nodes = self.find_nodes_by_type(root_node, 'declaration')
        
        for decl_node in decl_nodes:
            # 查找变量名
            for child in decl_node.children:
                if child.type == 'init_declarator':
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            variables.append({
                                'node': decl_node,
                                'name_node': grandchild,
                                'line': decl_node.start_point[0] + 1
                            })
                            
        return variables


# 使用示例
if __name__ == "__main__":
    parser = CodeParser()
    
    # 解析单个文件
    test_file = Path("test.c")
    if test_file.exists():
        result = parser.parse_file(test_file)
        if result:
            print(f"解析成功: {result['path']}")
            print(f"行数: {result['line_count']}")
            
            # 查找函数
            functions = parser.find_function_definitions(result['root_node'])
            print(f"找到 {len(functions)} 个函数")
            
            for func in functions:
                func_name = parser.get_node_text(func['name_node'], result['content'])
                print(f"  函数: {func_name} (第{func['start_line']}行)")