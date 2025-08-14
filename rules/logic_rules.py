#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: rules/logic_rules.py
逻辑错误规则 - 检测常见的逻辑错误和编程陷阱
"""

from typing import List, Dict, Any
from .base_rule import BaseRule, ASTRule, Severity, Issue
import re

class AssignmentInConditionRule(BaseRule):
    """条件中赋值检查规则"""
    
    def __init__(self):
        super().__init__("L001", "条件中赋值检查", "Assignment in Condition")
        self.severity = Severity.CRITICAL
        self.category = "逻辑错误"
        self.description_cn = "检测条件语句中的赋值操作（可能是误写）"
        self.description_en = "Detect assignment in conditional statements"
        self.why_cn = """
在条件语句中使用赋值操作符(=)而不是比较操作符(==)是经典的C语言陷阱。
这会导致：
1. 逻辑错误
2. 意外的变量修改
3. 难以发现的bug

C语言中赋值表达式的值是被赋的值，所以 if(x = 5) 总是为真。
        """
        
        self.add_bad_example(
            """int x = 0;
if (x = 5) {  // 错误：应该是 x == 5
    printf("x is 5\\n");
}

while (flag = 1) {  // 错误：无限循环
    // ...
}""",
            "条件中使用了赋值而不是比较"
        )
        
        self.add_good_example(
            """int x = 0;
if (x == 5) {  // 正确：比较操作
    printf("x is 5\\n");
}

// 如果确实需要赋值并检查，使用明确的括号
if ((ptr = malloc(100)) != NULL) {
    // 这样写意图明确
}""",
            "正确的条件语句写法"
        )
        
        self.set_reference("《C陷阱与缺陷》", "第1章", "P8-P12",
                          quote="= 和 == 的混淆是C语言中最常见的错误之一")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查条件中的赋值"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找各种条件语句
        condition_statements = []
        
        # if语句
        if_nodes = parser.find_nodes_by_type(root_node, 'if_statement')
        condition_statements.extend(if_nodes)
        
        # while语句
        while_nodes = parser.find_nodes_by_type(root_node, 'while_statement')
        condition_statements.extend(while_nodes)
        
        # for语句
        for_nodes = parser.find_nodes_by_type(root_node, 'for_statement')
        condition_statements.extend(for_nodes)
        
        for stmt_node in condition_statements:
            # 查找条件表达式
            condition_node = self._find_condition_in_statement(stmt_node, parser, content)
            
            if condition_node:
                # 在条件中查找赋值操作
                assign_nodes = parser.find_nodes_by_type(condition_node, 'assignment_expression')
                
                for assign_node in assign_nodes:
                    # 检查是否是简单赋值（=）而不是复合赋值（+=等）
                    if self._is_simple_assignment(assign_node, parser, content):
                        # 检查是否是有意的赋值（用括号包围）
                        if not self._is_intentional_assignment(assign_node, parser, content):
                            issue = self.create_issue(
                                file_info, assign_node,
                                "条件语句中发现赋值操作，可能是误写了 '=' 而不是 '=='",
                                "检查是否应该使用 '==' 进行比较，或用括号明确表示有意赋值"
                            )
                            issues.append(issue)
                            
        return issues
    
    def _find_condition_in_statement(self, stmt_node, parser, content: str):
        """在语句中查找条件表达式"""
        # 查找括号表达式（条件通常在括号中）
        for child in stmt_node.children:
            if child.type == 'parenthesized_expression':
                return child
        return None
    
    def _is_simple_assignment(self, assign_node, parser, content: str) -> bool:
        """检查是否是简单赋值"""
        assign_text = parser.get_node_text(assign_node, content)
        # 检查是否包含简单的 = 而不是 ==, !=, +=, -= 等
        return ('=' in assign_text and 
                '==' not in assign_text and 
                '!=' not in assign_text and
                '+=' not in assign_text and
                '-=' not in assign_text and
                '*=' not in assign_text and
                '/=' not in assign_text)
    
    def _is_intentional_assignment(self, assign_node, parser, content: str) -> bool:
        """检查是否是有意的赋值（用额外括号包围）"""
        # 简化检查：如果赋值表达式外面还有括号，认为是有意的
        parent = assign_node.parent
        return (parent and parent.type == 'parenthesized_expression' and
                parent.parent and parent.parent.type == 'parenthesized_expression')

class SwitchFallthroughRule(BaseRule):
    """Switch语句缺少break检查"""
    
    def __init__(self):
        super().__init__("L002", "Switch缺少break", "Switch Fallthrough")
        self.severity = Severity.WARNING
        self.category = "逻辑错误"
        self.description_cn = "检测switch语句中缺少break的情况"
        self.description_en = "Detect missing break in switch statements"
        self.why_cn = """
Switch语句中缺少break会导致"穿透"效应，即执行完一个case后
继续执行下一个case，这通常不是程序员的本意。

常见问题：
1. 忘记添加break语句
2. 意外的逻辑错误
3. 难以调试的行为

虽然有时穿透是有意的，但应该用注释明确说明。
        """
        
        self.add_bad_example(
            """switch (value) {
    case 1:
        printf("One\\n");
        // 缺少break，会继续执行case 2
    case 2:
        printf("Two\\n");
        break;
    case 3:
        printf("Three\\n");
        // 缺少break
    default:
        printf("Default\\n");
}""",
            "Switch语句缺少break导致穿透"
        )
        
        self.add_good_example(
            """switch (value) {
    case 1:
        printf("One\\n");
        break;  // 正确：添加break
    case 2:
        printf("Two\\n");
        break;
    case 3:
        printf("Three\\n");
        // 有意穿透到default
        /* FALLTHROUGH */  // 用注释说明有意穿透
    default:
        printf("Default\\n");
        break;
}""",
            "正确的switch语句写法"
        )
        
        self.set_reference("《C陷阱与缺陷》", "第4章", "P45-P52",
                          quote="switch语句的穿透特性是C语言的一个陷阱")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查switch语句缺少break"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找switch语句
        switch_nodes = parser.find_nodes_by_type(root_node, 'switch_statement')
        
        for switch_node in switch_nodes:
            # 查找switch body
            switch_body = self._find_switch_body(switch_node)
            if not switch_body:
                continue
                
            # 查找所有case标签
            case_nodes = parser.find_nodes_by_type(switch_body, 'case_statement')
            
            for i, case_node in enumerate(case_nodes):
                # 检查case是否有break或return
                if not self._has_break_or_return(case_node, case_nodes, i, parser, content):
                    # 检查是否有fallthrough注释
                    if not self._has_fallthrough_comment(case_node, parser, content):
                        issue = self.create_issue(
                            file_info, case_node,
                            "case语句缺少break，可能导致意外的穿透执行",
                            "添加break语句，或用注释明确说明有意穿透"
                        )
                        issues.append(issue)
                        
        return issues
    
    def _find_switch_body(self, switch_node):
        """查找switch语句的主体"""
        for child in switch_node.children:
            if child.type == 'compound_statement':
                return child
        return None
    
    def _has_break_or_return(self, case_node, all_cases, case_index, parser, content: str) -> bool:
        """检查case是否有break或return"""
        # 获取当前case到下一个case之间的内容
        next_case_line = None
        if case_index + 1 < len(all_cases):
            next_case_line = all_cases[case_index + 1].start_point[0]
        
        case_start_line = case_node.start_point[0]
        
        # 在case的作用域内查找break或return
        break_nodes = parser.find_nodes_by_type(case_node.parent, 'break_statement')
        return_nodes = parser.find_nodes_by_type(case_node.parent, 'return_statement')
        
        # 检查break/return是否在当前case的范围内
        for break_node in break_nodes:
            break_line = break_node.start_point[0]
            if (break_line > case_start_line and 
                (next_case_line is None or break_line < next_case_line)):
                return True
                
        for return_node in return_nodes:
            return_line = return_node.start_point[0]
            if (return_line > case_start_line and 
                (next_case_line is None or return_line < next_case_line)):
                return True
                
        return False
    
    def _has_fallthrough_comment(self, case_node, parser, content: str) -> bool:
        """检查是否有fallthrough注释"""
        lines = content.split('\n')
        case_line = case_node.start_point[0]
        
        # 检查case后面几行是否有fallthrough注释
        for i in range(case_line, min(case_line + 5, len(lines))):
            line_content = lines[i].lower()
            if ('fallthrough' in line_content or 
                'fall through' in line_content or
                'falls through' in line_content):
                return True
                
        return False

class UnusedVariableRule(ASTRule):
    """未使用变量检查"""
    
    def __init__(self):
        super().__init__("L003", "未使用变量检查", "Unused Variable Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码质量"
        self.description_cn = "检测声明但未使用的变量"
        self.description_en = "Detect declared but unused variables"
        self.why_cn = """
未使用的变量会：
1. 增加代码复杂度
2. 浪费内存空间
3. 让代码难以维护
4. 可能掩盖真正的错误

删除未使用的变量可以提高代码质量。
        """
        
        self.add_bad_example(
            """void function() {
    int used_var = 10;
    int unused_var = 20;  // 声明但未使用
    char buffer[100];     // 声明但未使用
    
    printf("%d\\n", used_var);
    // unused_var 和 buffer 从未被使用
}""",
            "声明了但从未使用的变量"
        )
        
        self.add_good_example(
            """void function() {
    int used_var = 10;
    // 删除了未使用的变量
    
    printf("%d\\n", used_var);
}""",
            "只保留实际使用的变量"
        )
        
        self.set_reference("代码整洁之道", "变量管理", "",
                          quote="删除未使用的代码")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查未使用的变量"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找函数定义
        functions = parser.find_function_definitions(root_node)
        
        for func_info in functions:
            func_node = func_info['node']
            
            # 收集函数内的变量声明
            declared_vars = self._collect_variable_declarations(func_node, parser, content)
            
            # 收集变量使用
            used_vars = self._collect_variable_usages(func_node, parser, content)
            
            # 查找未使用的变量
            for var_info in declared_vars:
                var_name = var_info['name']
                if var_name not in used_vars:
                    issue = self.create_issue(
                        file_info, var_info['node'],
                        f"变量'{var_name}'声明但从未使用",
                        f"删除未使用的变量'{var_name}'"
                    )
                    issues.append(issue)
                    
        return issues
    
    def _collect_variable_declarations(self, func_node, parser, content: str) -> List[Dict[str, Any]]:
        """收集变量声明"""
        declarations = []
        
        # 查找声明语句
        decl_nodes = parser.find_nodes_by_type(func_node, 'declaration')
        
        for decl_node in decl_nodes:
            # 从声明中提取变量名
            var_names = self._extract_variable_names_from_declaration(decl_node, parser, content)
            for var_name in var_names:
                declarations.append({
                    'name': var_name,
                    'node': decl_node,
                    'line': decl_node.start_point[0] + 1
                })
                
        return declarations
    
    def _extract_variable_names_from_declaration(self, decl_node, parser, content: str) -> List[str]:
        """从声明节点中提取变量名"""
        var_names = []
        
        # 查找标识符
        identifiers = parser.find_nodes_by_type(decl_node, 'identifier')
        
        # 跳过类型名，只取变量名
        for identifier in identifiers:
            id_text = parser.get_node_text(identifier, content)
            # 简单的过滤：跳过一些明显的类型名
            if not self._is_likely_type_name(id_text):
                var_names.append(id_text)
                
        return var_names
    
    def _is_likely_type_name(self, name: str) -> bool:
        """判断是否可能是类型名"""
        type_keywords = {'int', 'char', 'float', 'double', 'void', 'long', 'short', 
                        'unsigned', 'signed', 'const', 'volatile', 'static', 'extern'}
        return name in type_keywords
    
    def _collect_variable_usages(self, func_node, parser, content: str) -> set:
        """收集变量使用"""
        used_vars = set()
        
        # 查找所有标识符使用（简化实现）
        identifiers = parser.find_nodes_by_type(func_node, 'identifier')
        
        for identifier in identifiers:
            # 跳过声明中的标识符，只统计使用
            if not self._is_in_declaration(identifier):
                var_name = parser.get_node_text(identifier, content)
                used_vars.add(var_name)
                
        return used_vars
    
    def _is_in_declaration(self, identifier_node) -> bool:
        """检查标识符是否在声明中"""
        parent = identifier_node.parent
        while parent:
            if parent.type == 'declaration':
                return True
            parent = parent.parent
        return False

class FunctionReturnRule(BaseRule):
    """函数返回值检查"""
    
    def __init__(self):
        super().__init__("L004", "函数返回值检查", "Function Return Value Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码质量"
        self.description_cn = "检测未检查的函数返回值"
        self.description_en = "Detect unchecked function return values"
        self.why_cn = """
某些函数的返回值包含重要的错误信息，忽略这些返回值可能导致：
1. 错误未被及时发现
2. 程序在错误状态下继续运行
3. 数据损坏或安全问题

特别是内存分配、文件操作等函数的返回值应该被检查。
        """
        
        self.add_bad_example(
            """FILE *fp;
fp = fopen("file.txt", "r");  // 未检查返回值
fread(buffer, 1, 100, fp);    // 如果fopen失败，这里会出错

malloc(1024);  // 未检查返回值
scanf("%d", &num);  // 未检查返回值""",
            "忽略了重要函数的返回值"
        )
        
        self.add_good_example(
            """FILE *fp = fopen("file.txt", "r");
if (fp == NULL) {  // 正确：检查返回值
    perror("fopen failed");
    return -1;
}

char *ptr = malloc(1024);
if (ptr == NULL) {  // 正确：检查malloc返回值
    fprintf(stderr, "Memory allocation failed\\n");
    return -1;
}""",
            "正确检查函数返回值"
        )
        
        self.set_reference("C编程最佳实践", "错误处理", "",
                          quote="始终检查可能失败的函数返回值")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查函数返回值"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 需要检查返回值的函数
        critical_functions = {
            'malloc', 'calloc', 'realloc',
            'fopen', 'fread', 'fwrite', 'fclose',
            'scanf', 'fscanf', 'sscanf',
            'system', 'exec', 'fork'
        }
        
        # 查找函数调用
        call_nodes = parser.find_nodes_by_type(root_node, 'call_expression')
        
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_node = call_node.children[0]
                func_name = parser.get_node_text(func_node, content)
                
                if func_name in critical_functions:
                    # 检查返回值是否被使用
                    if not self._is_return_value_used(call_node, parser, content):
                        issue = self.create_issue(
                            file_info, call_node,
                            f"函数'{func_name}'的返回值未被检查",
                            f"检查{func_name}的返回值以处理可能的错误"
                        )
                        issues.append(issue)
                        
        return issues
    
    def _is_return_value_used(self, call_node, parser, content: str) -> bool:
        """检查函数调用的返回值是否被使用"""
        parent = call_node.parent
        
        # 如果在赋值表达式中，认为返回值被使用
        if parent and parent.type == 'assignment_expression':
            return True
            
        # 如果在条件表达式中，认为返回值被使用
        if parent and parent.type in ['if_statement', 'while_statement', 'for_statement']:
            return True
            
        # 如果在比较表达式中，认为返回值被使用
        if parent and parent.type == 'binary_expression':
            return True
            
        # 如果在变量声明的初始化中，认为返回值被使用
        if parent and parent.type == 'init_declarator':
            return True
            
        return False

class DivisionByZeroRule(BaseRule):
    """除零检查规则"""
    
    def __init__(self):
        super().__init__("L005", "除零检查", "Division by Zero Check")
        self.severity = Severity.CRITICAL
        self.category = "逻辑错误"
        self.description_cn = "检测可能的除零操作"
        self.description_en = "Detect potential division by zero"
        self.why_cn = """
除零是未定义行为，会导致：
1. 程序崩溃
2. 浮点异常
3. 不可预测的结果

在进行除法运算前应该检查除数是否为零。
        """
        
        self.add_bad_example(
            """int a = 10, b = 0;
int result = a / b;  // 错误：除数为0

float x = 5.0, y = 0.0;
float result2 = x / y;  // 错误：浮点除零""",
            "直接进行除法运算，未检查除数"
        )
        
        self.add_good_example(
            """int a = 10, b = 0;
if (b != 0) {  // 正确：检查除数
    int result = a / b;
} else {
    printf("Error: Division by zero\\n");
}

// 或者使用条件表达式
int result = (b != 0) ? a / b : 0;""",
            "除法前检查除数是否为零"
        )
        
        self.set_reference("《C陷阱与缺陷》", "第6章", "P78-P82",
                          quote="除零是未定义行为")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查除零操作"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找二元表达式
        binary_nodes = parser.find_nodes_by_type(root_node, 'binary_expression')
        
        for binary_node in binary_nodes:
            if len(binary_node.children) >= 3:
                left_node = binary_node.children[0]
                op_node = binary_node.children[1]
                right_node = binary_node.children[2]
                
                op_text = parser.get_node_text(op_node, content)
                
                # 检查除法和取模运算
                if op_text in ['/', '%']:
                    right_text = parser.get_node_text(right_node, content).strip()
                    
                    # 检查是否为常量0
                    if right_text == '0' or right_text == '0.0':
                        issue = self.create_issue(
                            file_info, binary_node,
                            f"检测到{op_text}零操作",
                            "在进行除法运算前检查除数是否为零"
                        )
                        issues.append(issue)
                    
                    # 检查变量除法是否有保护
                    elif not self._has_zero_check(binary_node, right_text, parser, content):
                        issue = self.create_issue(
                            file_info, binary_node,
                            f"除法运算未检查除数'{right_text}'是否为零",
                            f"在除法前添加检查: if({right_text} != 0)",
                            Severity.WARNING
                        )
                        issues.append(issue)
                        
        return issues
    
    def _has_zero_check(self, division_node, divisor_name: str, parser, content: str) -> bool:
        """检查是否有零值检查"""
        # 简化检查：在同一个函数内查找条件检查
        func_node = self._find_containing_function(division_node)
        if not func_node:
            return False
            
        # 查找if语句
        if_nodes = parser.find_nodes_by_type(func_node, 'if_statement')
        
        for if_node in if_nodes:
            if_text = parser.get_node_text(if_node, content)
            if (f'{divisor_name} != 0' in if_text or 
                f'{divisor_name} > 0' in if_text or
                f'0 != {divisor_name}' in if_text):
                return True
                
        return False
    
    def _find_containing_function(self, node):
        """查找包含该节点的函数"""
        current = node.parent
        while current:
            if current.type == 'function_definition':
                return current
            current = current.parent
        return None


# 导出所有规则
__all__ = [
    'AssignmentInConditionRule',
    'SwitchFallthroughRule',
    'UnusedVariableRule', 
    'FunctionReturnRule',
    'DivisionByZeroRule'
]

# 使用示例
if __name__ == "__main__":
    # 测试逻辑错误规则
    from ..core.parser import CodeParser
    from pathlib import Path
    
    test_code = """
    #include <stdio.h>
    
    int main() {
        int x = 5;
        int unused_var = 10;  // 未使用变量
        
        if (x = 3) {  // 赋值写成判断
            printf("x is 3\\n");
        }
        
        switch (x) {
            case 1:
                printf("One\\n");
                // 缺少break
            case 2:
                printf("Two\\n");
                break;
        }
        
        int result = x / 0;  // 除零
        malloc(100);  // 未检查返回值
        
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
                AssignmentInConditionRule(),
                SwitchFallthroughRule(),
                UnusedVariableRule(),
                FunctionReturnRule(),
                DivisionByZeroRule()
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