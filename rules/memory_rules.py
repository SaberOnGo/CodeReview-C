#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: rules/memory_rules.py
内存安全规则 - 检测内存相关的安全问题
"""

from typing import List, Dict, Any
from .base_rule import BaseRule, ASTRule, Severity, Issue
import re

class ArrayBoundsRule(BaseRule):
    """数组越界检查规则"""
    
    def __init__(self):
        super().__init__("C001", "数组越界检查", "Array Bounds Check")
        self.severity = Severity.CRITICAL
        self.category = "内存安全"
        self.description_cn = "检测可能的数组下标越界访问"
        self.description_en = "Detect potential array out-of-bounds access"
        self.why_cn = """
数组越界是C语言中最常见也最危险的错误之一。它可能导致：
1. 程序崩溃
2. 数据损坏  
3. 安全漏洞
4. 难以调试的随机错误

数组下标从0开始，对于大小为n的数组，有效下标范围是0到n-1。
        """
        
        self.add_bad_example(
            """int arr[10];
arr[10] = 5;  // 错误：数组大小为10，有效下标0-9
arr[-1] = 3;  // 错误：负数下标""",
            "访问了不存在的数组元素"
        )
        
        self.add_good_example(
            """int arr[10];
arr[9] = 5;   // 正确：最大下标为9
// 或者使用sizeof确保安全
for(int i = 0; i < sizeof(arr)/sizeof(arr[0]); i++) {
    arr[i] = i;
}""",
            "安全的数组访问方式"
        )
        
        self.set_reference("《C陷阱与缺陷》", "第2章", "P23-P27", 
                          quote="数组下标从0开始是C语言的一个陷阱...")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查数组越界"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找数组访问
        subscript_nodes = parser.find_nodes_by_type(root_node, 'subscript_expression')
        
        for node in subscript_nodes:
            if len(node.children) >= 3:  # array[index]
                array_node = node.children[0]
                index_node = node.children[2]  # 跳过'['
                
                # 获取索引文本
                index_text = parser.get_node_text(index_node, content).strip()
                
                # 检查是否为数字常量
                if self._is_numeric_constant(index_text):
                    index_value = int(index_text)
                    
                    # 查找数组声明
                    array_name = parser.get_node_text(array_node, content)
                    array_size = self._find_array_size(root_node, array_name, parser, content)
                    
                    if array_size is not None:
                        if index_value >= array_size:
                            issue = self.create_issue(
                                file_info, node,
                                f"数组'{array_name}'大小为{array_size}，但访问索引{index_value}超出范围",
                                f"将索引改为0到{array_size-1}之间的值"
                            )
                            issues.append(issue)
                        elif index_value < 0:
                            issue = self.create_issue(
                                file_info, node,
                                f"数组'{array_name}'使用负数索引{index_value}",
                                "数组索引必须为非负数"
                            )
                            issues.append(issue)
                            
        return issues
    
    def _is_numeric_constant(self, text: str) -> bool:
        """检查是否为数字常量"""
        try:
            int(text)
            return True
        except ValueError:
            return False
    
    def _find_array_size(self, root_node, array_name: str, parser, content: str) -> int:
        """查找数组大小"""
        # 查找数组声明
        decl_nodes = parser.find_nodes_by_type(root_node, 'array_declarator')
        
        for decl_node in decl_nodes:
            if len(decl_node.children) >= 3:  # name[size]
                name_node = decl_node.children[0]
                size_node = decl_node.children[2]  # 跳过'['
                
                name_text = parser.get_node_text(name_node, content)
                if name_text == array_name:
                    size_text = parser.get_node_text(size_node, content).strip()
                    if self._is_numeric_constant(size_text):
                        return int(size_text)
        return None

class NullPointerRule(BaseRule):
    """空指针检查规则"""
    
    def __init__(self):
        super().__init__("C002", "空指针检查", "Null Pointer Check")
        self.severity = Severity.CRITICAL
        self.category = "内存安全"
        self.description_cn = "检测空指针解引用"
        self.description_en = "Detect null pointer dereference"
        self.why_cn = """
空指针解引用是导致程序崩溃的常见原因。当指针为NULL时，
对其进行解引用操作会导致段错误(Segmentation Fault)。

常见的空指针问题：
1. malloc返回NULL但未检查
2. 函数参数指针未验证
3. 指针在使用前被设置为NULL
        """
        
        self.add_bad_example(
            """char *ptr = malloc(100);
*ptr = 'a';  // 错误：未检查malloc是否返回NULL

char *p = NULL;
printf("%s", p);  // 错误：直接使用NULL指针""",
            "直接使用可能为NULL的指针"
        )
        
        self.add_good_example(
            """char *ptr = malloc(100);
if (ptr != NULL) {
    *ptr = 'a';  // 正确：先检查再使用
    free(ptr);
}

// 或者更简洁的写法
if (ptr) {
    *ptr = 'a';
}""",
            "使用前检查指针是否为NULL"
        )
        
        self.set_reference("《C陷阱与缺陷》", "第5章", "P67-P73",
                          quote="空指针的解引用是未定义行为...")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查空指针解引用"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找可能的空指针赋值
        null_assignments = self._find_null_assignments(root_node, parser, content)
        
        # 查找指针解引用
        pointer_dereferences = self._find_pointer_dereferences(root_node, parser, content)
        
        # 检查malloc等内存分配函数的返回值
        malloc_calls = self._find_malloc_calls(root_node, parser, content)
        
        for call_info in malloc_calls:
            # 检查malloc调用后是否立即检查返回值
            if not self._has_null_check_after(call_info, root_node, parser, content):
                issue = self.create_issue(
                    file_info, call_info['node'],
                    f"调用{call_info['function_name']}后未检查返回值是否为NULL",
                    "在使用返回的指针前检查是否为NULL"
                )
                issues.append(issue)
        
        return issues
    
    def _find_null_assignments(self, root_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找NULL赋值"""
        assignments = []
        assign_nodes = parser.find_nodes_by_type(root_node, 'assignment_expression')
        
        for assign_node in assign_nodes:
            if len(assign_node.children) >= 3:
                left_node = assign_node.children[0]
                right_node = assign_node.children[2]
                
                right_text = parser.get_node_text(right_node, content).strip()
                if right_text.upper() in ['NULL', '0', 'nullptr']:
                    var_name = parser.get_node_text(left_node, content)
                    assignments.append({
                        'node': assign_node,
                        'variable': var_name,
                        'line': assign_node.start_point[0] + 1
                    })
                    
        return assignments
    
    def _find_pointer_dereferences(self, root_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找指针解引用"""
        dereferences = []
        
        # 查找*ptr形式的解引用
        unary_nodes = parser.find_nodes_by_type(root_node, 'unary_expression')
        for unary_node in unary_nodes:
            if len(unary_node.children) >= 2:
                op_node = unary_node.children[0]
                operand_node = unary_node.children[1]
                
                op_text = parser.get_node_text(op_node, content)
                if op_text == '*':
                    var_name = parser.get_node_text(operand_node, content)
                    dereferences.append({
                        'node': unary_node,
                        'variable': var_name,
                        'line': unary_node.start_point[0] + 1
                    })
        
        # 查找ptr->member形式的解引用
        field_nodes = parser.find_nodes_by_type(root_node, 'field_expression')
        for field_node in field_nodes:
            if len(field_node.children) >= 3:
                ptr_node = field_node.children[0]
                op_node = field_node.children[1]
                
                op_text = parser.get_node_text(op_node, content)
                if op_text == '->':
                    var_name = parser.get_node_text(ptr_node, content)
                    dereferences.append({
                        'node': field_node,
                        'variable': var_name,
                        'line': field_node.start_point[0] + 1
                    })
                    
        return dereferences
    
    def _find_malloc_calls(self, root_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找内存分配函数调用"""
        malloc_functions = ['malloc', 'calloc', 'realloc', 'strdup']
        calls = []
        
        call_nodes = parser.find_nodes_by_type(root_node, 'call_expression')
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_node = call_node.children[0]
                func_name = parser.get_node_text(func_node, content)
                
                if func_name in malloc_functions:
                    calls.append({
                        'node': call_node,
                        'function_node': func_node,
                        'function_name': func_name,
                        'line': call_node.start_point[0] + 1
                    })
                    
        return calls
    
    def _has_null_check_after(self, malloc_info, root_node, parser, content: str) -> bool:
        """检查malloc调用后是否有NULL检查"""
        # 这是一个简化的实现，实际应该进行更复杂的控制流分析
        malloc_line = malloc_info['line']
        
        # 在后续几行中查找NULL检查
        statements = parser.find_nodes_by_type(root_node, 'if_statement')
        for stmt in statements:
            stmt_line = stmt.start_point[0] + 1
            if stmt_line > malloc_line and stmt_line - malloc_line <= 5:
                stmt_text = parser.get_node_text(stmt, content)
                if 'NULL' in stmt_text or '!=' in stmt_text:
                    return True
                    
        return False

class MemoryLeakRule(ASTRule):
    """内存泄漏检查规则"""
    
    def __init__(self):
        super().__init__("C003", "内存泄漏检查", "Memory Leak Check")
        self.severity = Severity.WARNING
        self.category = "内存安全"
        self.description_cn = "检测malloc后未free的情况"
        self.description_en = "Detect memory allocation without corresponding free"
        self.why_cn = """
内存泄漏是指程序分配的内存没有被正确释放，导致可用内存逐渐减少。
在长时间运行的程序中，内存泄漏可能导致系统内存耗尽。

常见的内存泄漏情况：
1. malloc/calloc后忘记调用free
2. 在函数返回前未释放局部指针
3. 异常退出路径未释放内存
        """
        
        self.add_bad_example(
            """void bad_function() {
    char *buffer = malloc(1024);
    if (some_condition) {
        return;  // 错误：未释放buffer就返回
    }
    // 其他处理...
    free(buffer);  // 只有部分路径会执行到这里
}""",
            "部分执行路径未释放内存"
        )
        
        self.add_good_example(
            """void good_function() {
    char *buffer = malloc(1024);
    if (buffer == NULL) {
        return;  // 分配失败，无需释放
    }
    
    if (some_condition) {
        free(buffer);  // 正确：所有路径都释放内存
        return;
    }
    
    // 其他处理...
    free(buffer);
}""",
            "确保所有执行路径都释放内存"
        )
        
        self.set_reference("C编程最佳实践", "内存管理", "",
                          quote="每个malloc都应该有对应的free")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查内存泄漏（简化实现）"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找函数定义
        functions = parser.find_function_definitions(root_node)
        
        for func_info in functions:
            func_node = func_info['node']
            func_name = parser.get_node_text(func_info['name_node'], content)
            
            # 在函数内查找malloc和free调用
            malloc_calls = self._find_malloc_in_function(func_node, parser, content)
            free_calls = self._find_free_in_function(func_node, parser, content)
            
            # 简单的匹配检查（实际需要更复杂的分析）
            if len(malloc_calls) > len(free_calls):
                # 可能存在内存泄漏
                for malloc_call in malloc_calls:
                    issue = self.create_issue(
                        file_info, malloc_call['node'],
                        f"函数'{func_name}'中可能存在内存泄漏",
                        "确保每个malloc/calloc都有对应的free调用"
                    )
                    issues.append(issue)
                    break  # 每个函数只报告一次
                    
        return issues
    
    def _find_malloc_in_function(self, func_node, parser, content: str) -> List[Dict[str, Any]]:
        """在函数内查找malloc调用"""
        malloc_functions = ['malloc', 'calloc', 'realloc']
        calls = []
        
        call_nodes = parser.find_nodes_by_type(func_node, 'call_expression')
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_node_name = call_node.children[0]
                func_name = parser.get_node_text(func_node_name, content)
                
                if func_name in malloc_functions:
                    calls.append({
                        'node': call_node,
                        'function_name': func_name,
                        'line': call_node.start_point[0] + 1
                    })
                    
        return calls
    
    def _find_free_in_function(self, func_node, parser, content: str) -> List[Dict[str, Any]]:
        """在函数内查找free调用"""
        calls = []
        
        call_nodes = parser.find_nodes_by_type(func_node, 'call_expression')
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_node_name = call_node.children[0]
                func_name = parser.get_node_text(func_node_name, content)
                
                if func_name == 'free':
                    calls.append({
                        'node': call_node,
                        'line': call_node.start_point[0] + 1
                    })
                    
        return calls

class BufferOverflowRule(BaseRule):
    """缓冲区溢出检查规则"""
    
    def __init__(self):
        super().__init__("C004", "缓冲区溢出检查", "Buffer Overflow Check")
        self.severity = Severity.CRITICAL
        self.category = "内存安全"
        self.description_cn = "检测可能的缓冲区溢出"
        self.description_en = "Detect potential buffer overflow"
        self.why_cn = """
缓冲区溢出是最危险的安全漏洞之一，可能导致：
1. 程序崩溃
2. 数据损坏
3. 代码注入攻击
4. 系统被完全控制

常见的危险函数：strcpy, strcat, sprintf, gets等
        """
        
        self.add_bad_example(
            """char buffer[10];
char *input = "This is a very long string";
strcpy(buffer, input);  // 错误：可能溢出

gets(buffer);  // 错误：gets不检查边界""",
            "使用不安全的字符串函数"
        )
        
        self.add_good_example(
            """char buffer[10];
char *input = "This is a very long string";
strncpy(buffer, input, sizeof(buffer) - 1);
buffer[sizeof(buffer) - 1] = '\\0';  // 确保字符串终止

// 或者使用更安全的函数
snprintf(buffer, sizeof(buffer), "%s", input);""",
            "使用安全的字符串函数"
        )
        
        self.set_reference("安全编程指南", "缓冲区溢出防护", "",
                          quote="避免使用不安全的字符串函数")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查缓冲区溢出"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 危险的字符串函数
        dangerous_functions = {
            'strcpy': 'strncpy',
            'strcat': 'strncat', 
            'sprintf': 'snprintf',
            'scanf': 'fgets + sscanf',
            'gets': 'fgets'
        }
        
        # 查找函数调用
        call_nodes = parser.find_nodes_by_type(root_node, 'call_expression')
        
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_node = call_node.children[0]
                func_name = parser.get_node_text(func_node, content)
                
                if func_name in dangerous_functions:
                    safer_alternative = dangerous_functions[func_name]
                    issue = self.create_issue(
                        file_info, call_node,
                        f"使用了不安全的函数'{func_name}'，可能导致缓冲区溢出",
                        f"考虑使用更安全的替代函数: {safer_alternative}"
                    )
                    issues.append(issue)
                    
        return issues

class UseAfterFreeRule(ASTRule):
    """释放后使用检查规则"""
    
    def __init__(self):
        super().__init__("C005", "释放后使用检查", "Use After Free Check")
        self.severity = Severity.CRITICAL
        self.category = "内存安全"
        self.description_cn = "检测释放后使用指针的情况"
        self.description_en = "Detect use of pointer after free"
        self.why_cn = """
释放后使用(Use After Free)是一种严重的内存错误，指在调用free()
释放内存后继续使用该指针。这可能导致：

1. 程序崩溃
2. 数据损坏
3. 安全漏洞
4. 不可预测的行为

正确的做法是在free后将指针设置为NULL。
        """
        
        self.add_bad_example(
            """char *ptr = malloc(100);
strcpy(ptr, "Hello");
free(ptr);
printf("%s", ptr);  // 错误：使用已释放的指针""",
            "在free后继续使用指针"
        )
        
        self.add_good_example(
            """char *ptr = malloc(100);
strcpy(ptr, "Hello");
printf("%s", ptr);  // 正确：在free前使用
free(ptr);
ptr = NULL;  // 正确：free后设置为NULL""",
            "free后将指针设置为NULL"
        )
        
        self.set_reference("《C陷阱与缺陷》", "内存管理", "",
                          quote="free后的指针变成了悬空指针")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查释放后使用（简化实现）"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找函数定义
        functions = parser.find_function_definitions(root_node)
        
        for func_info in functions:
            func_node = func_info['node']
            
            # 查找free调用
            free_calls = self._find_free_calls_in_function(func_node, parser, content)
            
            for free_call in free_calls:
                # 获取被释放的变量名
                freed_var = self._get_freed_variable(free_call, parser, content)
                if freed_var:
                    # 检查free后是否还有对该变量的使用
                    if self._has_usage_after_free(func_node, free_call, freed_var, parser, content):
                        issue = self.create_issue(
                            file_info, free_call['node'],
                            f"指针'{freed_var}'在释放后可能被继续使用",
                            f"在free({freed_var})后将其设置为NULL，或避免后续使用"
                        )
                        issues.append(issue)
                        
        return issues
    
    def _find_free_calls_in_function(self, func_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找函数内的free调用"""
        calls = []
        
        call_nodes = parser.find_nodes_by_type(func_node, 'call_expression')
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_name_node = call_node.children[0]
                func_name = parser.get_node_text(func_name_node, content)
                
                if func_name == 'free':
                    calls.append({
                        'node': call_node,
                        'line': call_node.start_point[0] + 1
                    })
                    
        return calls
    
    def _get_freed_variable(self, free_call, parser, content: str) -> str:
        """获取被释放的变量名"""
        call_node = free_call['node']
        
        # free(ptr) - 获取参数
        if len(call_node.children) >= 2:
            args_node = call_node.children[1]  # argument_list
            if args_node.type == 'argument_list' and len(args_node.children) > 0:
                # 找到第一个参数
                for child in args_node.children:
                    if child.type == 'identifier':
                        return parser.get_node_text(child, content)
                        
        return None
    
    def _has_usage_after_free(self, func_node, free_call, var_name: str, parser, content: str) -> bool:
        """检查free后是否还有使用"""
        free_line = free_call['line']
        
        # 查找变量的所有使用
        var_references = self.find_variable_references(func_node, parser, content, var_name)
        
        # 检查是否有在free之后的使用
        for ref in var_references:
            if ref['line'] > free_line:
                # 检查是否是赋值为NULL（这是允许的）
                if not self._is_null_assignment(ref, parser, content):
                    return True
                    
        return False
    
    def _is_null_assignment(self, var_ref, parser, content: str) -> bool:
        """检查是否是NULL赋值"""
        # 简化检查：看看是否在赋值语句中
        node = var_ref['node']
        parent = node.parent
        
        while parent and parent.type != 'assignment_expression':
            parent = parent.parent
            
        if parent and parent.type == 'assignment_expression':
            # 检查右侧是否为NULL
            assign_text = parser.get_node_text(parent, content)
            return 'NULL' in assign_text or '= 0' in assign_text
            
        return False


# 导出所有规则
__all__ = [
    'ArrayBoundsRule',
    'NullPointerRule', 
    'MemoryLeakRule',
    'BufferOverflowRule',
    'UseAfterFreeRule'
]

# 使用示例
if __name__ == "__main__":
    # 测试内存安全规则
    from ..core.parser import CodeParser
    
    test_code = """
    #include <stdio.h>
    #include <stdlib.h>
    
    int main() {
        int arr[10];
        arr[10] = 5;  // 数组越界
        
        char *ptr = malloc(100);
        strcpy(ptr, "test");  // 缓冲区溢出风险
        free(ptr);
        printf("%s", ptr);  // 释放后使用
        
        return 0;
    }
    """
    
    # 创建临时文件进行测试
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_code)
        test_file = f.name
    
    try:
        # 解析代码
        parser = CodeParser()
        file_info = parser.parse_file(Path(test_file))
        
        if file_info:
            # 测试各个规则
            rules = [
                ArrayBoundsRule(),
                NullPointerRule(),
                MemoryLeakRule(),
                BufferOverflowRule(),
                UseAfterFreeRule()
            ]
            
            for rule in rules:
                print(f"\n测试规则: {rule.name_cn}")
                issues = rule.check(file_info, parser)
                for issue in issues:
                    print(f"  - {issue}")
                    
    finally:
        # 清理临时文件
        import os
        os.unlink(test_file)