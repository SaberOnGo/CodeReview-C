#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# base_rule.py
"""
规则基类 - 所有检查规则的基础类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Severity(Enum):
    """问题严重程度枚举"""
    CRITICAL = "严重"
    WARNING = "警告"
    SUGGESTION = "建议"

@dataclass
class CodeExample:
    """代码示例数据结构"""
    code: str
    description: str
    language: str = "c"

@dataclass
class RuleReference:
    """规则参考资料"""
    book: str = ""
    chapter: str = ""
    page: str = ""
    url: str = ""
    quote: str = ""

@dataclass
class Issue:
    """代码问题记录"""
    rule_id: str
    rule_name: str
    file_path: Path
    line_number: int
    column: int
    severity: Severity
    message: str
    description: str
    code_snippet: str
    suggestion: str = ""
    reference: str = ""
    
    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.file_path}:{self.line_number} - {self.message}"

class BaseRule(ABC):
    """
    规则基类 - 所有检查规则都必须继承此类
    
    这个基类定义了规则的基本属性和行为：
    - 规则标识和名称
    - 严重程度和分类
    - 教育内容（说明、示例、参考）
    - 检查逻辑接口
    """
    
    def __init__(self, rule_id: str, name_cn: str, name_en: str = ""):
        # 基本标识
        self.rule_id = rule_id
        self.name_cn = name_cn
        self.name_en = name_en or name_cn
        
        # 控制属性
        self.enabled = True
        self.severity = Severity.WARNING
        self.category = "通用"
        
        # 描述信息
        self.description_cn = ""
        self.description_en = ""
        self.why_cn = ""  # 为什么需要这个规则
        self.why_en = ""
        
        # 教育内容
        self.bad_examples: List[CodeExample] = []  # 错误示例
        self.good_examples: List[CodeExample] = []  # 正确示例
        self.reference = RuleReference()  # 参考资料
        
        # 规则配置
        self.config = {}  # 规则特定的配置参数
        
    @abstractmethod
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """
        检查代码并返回问题列表
        
        Args:
            file_info: 文件信息字典，包含path, content, tree, root_node等
            parser: 代码解析器实例，提供AST查询功能
            
        Returns:
            List[Issue]: 发现的问题列表
        """
        pass
    
    def is_applicable(self, file_info: Dict[str, Any]) -> bool:
        """
        判断规则是否适用于当前文件
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            bool: True表示适用，False表示跳过
        """
        # 默认适用于所有C文件
        file_path = file_info.get('path', Path())
        c_extensions = ['.c', '.h', '.cpp', '.hpp', '.cc', '.cxx']
        return file_path.suffix.lower() in c_extensions
    
    def create_issue(self, file_info: Dict[str, Any], node, message: str, 
                    suggestion: str = "", custom_severity: Optional[Severity] = None) -> Issue:
        """
        创建问题记录的便捷方法
        
        Args:
            file_info: 文件信息字典
            node: AST节点
            message: 问题描述
            suggestion: 修复建议
            custom_severity: 自定义严重程度（覆盖规则默认）
            
        Returns:
            Issue: 问题记录实例
        """
        line_num = node.start_point[0] + 1
        column = node.start_point[1]
        
        # 获取代码片段（前后各2行）
        lines = file_info.get('lines', [])
        start_line = max(0, line_num - 3)
        end_line = min(len(lines), line_num + 2)
        
        code_lines = []
        for i in range(start_line, end_line):
            prefix = ">>> " if i == line_num - 1 else "    "
            code_lines.append(f"{prefix}{i+1:4d}: {lines[i]}")
        
        code_snippet = '\n'.join(code_lines)
        
        return Issue(
            rule_id=self.rule_id,
            rule_name=self.name_cn,
            file_path=file_info['path'],
            line_number=line_num,
            column=column,
            severity=custom_severity or self.severity,
            message=message,
            description=self.description_cn,
            code_snippet=code_snippet,
            suggestion=suggestion,
            reference=self._format_reference()
        )
    
    def _format_reference(self) -> str:
        """格式化参考资料信息"""
        if not self.reference.book:
            return ""
            
        ref_parts = [self.reference.book]
        if self.reference.chapter:
            ref_parts.append(self.reference.chapter)
        if self.reference.page:
            ref_parts.append(self.reference.page)
            
        return " - ".join(ref_parts)
    
    def add_bad_example(self, code: str, description: str):
        """添加错误代码示例"""
        self.bad_examples.append(CodeExample(code, description))
        
    def add_good_example(self, code: str, description: str):
        """添加正确代码示例"""
        self.good_examples.append(CodeExample(code, description))
        
    def set_reference(self, book: str, chapter: str = "", page: str = "", 
                     url: str = "", quote: str = ""):
        """设置参考资料"""
        self.reference = RuleReference(
            book=book,
            chapter=chapter,
            page=page,
            url=url,
            quote=quote
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """将规则信息转换为字典格式（用于配置保存）"""
        return {
            'rule_id': self.rule_id,
            'name_cn': self.name_cn,
            'name_en': self.name_en,
            'enabled': self.enabled,
            'severity': self.severity.value,
            'category': self.category,
            'description_cn': self.description_cn,
            'description_en': self.description_en,
            'why_cn': self.why_cn,
            'why_en': self.why_en,
            'bad_examples': [
                {'code': ex.code, 'description': ex.description} 
                for ex in self.bad_examples
            ],
            'good_examples': [
                {'code': ex.code, 'description': ex.description}
                for ex in self.good_examples
            ],
            'reference': {
                'book': self.reference.book,
                'chapter': self.reference.chapter,
                'page': self.reference.page,
                'url': self.reference.url,
                'quote': self.reference.quote
            },
            'config': self.config
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """从字典数据加载规则信息（用于配置恢复）"""
        self.enabled = data.get('enabled', True)
        self.severity = Severity(data.get('severity', 'WARNING'))
        self.category = data.get('category', '通用')
        self.description_cn = data.get('description_cn', '')
        self.description_en = data.get('description_en', '')
        self.why_cn = data.get('why_cn', '')
        self.why_en = data.get('why_en', '')
        
        # 加载示例
        self.bad_examples = [
            CodeExample(ex['code'], ex['description'])
            for ex in data.get('bad_examples', [])
        ]
        self.good_examples = [
            CodeExample(ex['code'], ex['description'])
            for ex in data.get('good_examples', [])
        ]
        
        # 加载参考资料
        ref_data = data.get('reference', {})
        self.reference = RuleReference(
            book=ref_data.get('book', ''),
            chapter=ref_data.get('chapter', ''),
            page=ref_data.get('page', ''),
            url=ref_data.get('url', ''),
            quote=ref_data.get('quote', '')
        )
        
        self.config = data.get('config', {})
    
    def __str__(self) -> str:
        return f"{self.rule_id}: {self.name_cn} [{self.severity.value}]"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.rule_id}, enabled={self.enabled})>"

class PatternRule(BaseRule):
    """
    基于模式匹配的规则基类
    
    这个类简化了基于正则表达式或简单模式的规则实现
    """
    
    def __init__(self, rule_id: str, name_cn: str, name_en: str = ""):
        super().__init__(rule_id, name_cn, name_en)
        self.patterns = []  # 要匹配的模式列表
        self.node_types = []  # 要检查的AST节点类型
        
    def add_pattern(self, pattern: str, message_template: str):
        """添加检查模式"""
        self.patterns.append({
            'pattern': pattern,
            'message': message_template
        })
        
    def add_node_type(self, node_type: str):
        """添加要检查的节点类型"""
        self.node_types.append(node_type)
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """实现基于模式的检查逻辑"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 检查指定类型的节点
        for node_type in self.node_types:
            nodes = parser.find_nodes_by_type(root_node, node_type)
            
            for node in nodes:
                node_text = parser.get_node_text(node, content)
                
                # 检查所有模式
                for pattern_info in self.patterns:
                    if self._match_pattern(node_text, pattern_info['pattern']):
                        issue = self.create_issue(
                            file_info, node,
                            pattern_info['message'].format(text=node_text)
                        )
                        issues.append(issue)
                        
        return issues
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """模式匹配逻辑（子类可以重写）"""
        import re
        return bool(re.search(pattern, text))

class ASTRule(BaseRule):
    """
    基于AST分析的规则基类
    
    这个类提供了常用的AST分析工具方法
    """
    
    def __init__(self, rule_id: str, name_cn: str, name_en: str = ""):
        super().__init__(rule_id, name_cn, name_en)
        
    def find_function_calls(self, root_node, parser, content: str, 
                           function_name: str = None) -> List[Dict[str, Any]]:
        """查找函数调用"""
        calls = []
        call_nodes = parser.find_nodes_by_type(root_node, 'call_expression')
        
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_node = call_node.children[0]
                func_name = parser.get_node_text(func_node, content)
                
                if function_name is None or func_name == function_name:
                    calls.append({
                        'node': call_node,
                        'function_node': func_node,
                        'function_name': func_name,
                        'line': call_node.start_point[0] + 1
                    })
                    
        return calls
    
    def find_variable_references(self, root_node, parser, content: str,
                               variable_name: str) -> List[Dict[str, Any]]:
        """查找变量引用"""
        references = []
        identifier_nodes = parser.find_nodes_by_type(root_node, 'identifier')
        
        for id_node in identifier_nodes:
            var_name = parser.get_node_text(id_node, content)
            if var_name == variable_name:
                references.append({
                    'node': id_node,
                    'name': var_name,
                    'line': id_node.start_point[0] + 1,
                    'context': self._get_node_context(id_node, parser, content)
                })
                
        return references
    
    def _get_node_context(self, node, parser, content: str) -> str:
        """获取节点的上下文信息"""
        parent = node.parent
        if parent:
            return parser.get_node_text(parent, content)
        return parser.get_node_text(node, content)
    
    def is_in_condition(self, node) -> bool:
        """判断节点是否在条件表达式中"""
        current = node.parent
        while current:
            if current.type in ['if_statement', 'while_statement', 'for_statement', 
                              'conditional_expression', 'parenthesized_expression']:
                return True
            current = current.parent
        return False
    
    def is_in_function(self, node, function_name: str = None) -> bool:
        """判断节点是否在指定函数中"""
        current = node.parent
        while current:
            if current.type == 'function_definition':
                if function_name is None:
                    return True
                # 这里可以进一步检查函数名
                return True
            current = current.parent
        return False


# 使用示例
if __name__ == "__main__":
    # 创建一个简单的模式规则示例
    class SimplePatternRule(PatternRule):
        def __init__(self):
            super().__init__("DEMO001", "演示规则", "Demo Rule")
            self.severity = Severity.WARNING
            self.category = "演示"
            self.description_cn = "这是一个演示规则"
            
            # 添加检查模式
            self.add_pattern(r"printf\s*\(", "发现printf调用: {text}")
            self.add_node_type("call_expression")
            
            # 添加示例
            self.add_bad_example(
                'printf("Hello %s", name);',
                "直接使用printf可能不安全"
            )
            self.add_good_example(
                'snprintf(buffer, sizeof(buffer), "Hello %s", name);',
                "使用snprintf更安全"
            )
            
            # 设置参考
            self.set_reference("C安全编程指南", "第3章", "P45-P50")
    
    # 测试规则
    rule = SimplePatternRule()
    print(rule)
    print(f"规则配置: {rule.to_dict()}")