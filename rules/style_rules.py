#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: rules/style_rules.py
代码风格规则 - 检测代码风格和可读性问题
"""

from typing import List, Dict, Any
from .base_rule import BaseRule, ASTRule, PatternRule, Severity, Issue
import re

class MagicNumberRule(PatternRule):
    """魔术数字检查规则"""
    
    def __init__(self):
        super().__init__("S001", "魔术数字检查", "Magic Number Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码风格"
        self.description_cn = "检测硬编码的数字常量"
        self.description_en = "Detect hardcoded numeric constants"
        self.why_cn = """
魔术数字是指在代码中出现的没有明确含义的数字字面量。它们会导致：
1. 代码难以理解
2. 维护困难
3. 容易出错
4. 可读性差

应该使用有意义的常量名或宏定义来替代魔术数字。
        """
        
        self.add_bad_example(
            """if (status == 3) {  // 3是什么意思？
    handle_error();
}

char buffer[1024];  // 1024为什么选这个大小？
for (int i = 0; i < 42; i++) {  // 42有什么特殊含义？
    process(i);
}""",
            "使用了没有明确含义的数字"
        )
        
        self.add_good_example(
            """#define STATUS_ERROR 3
#define BUFFER_SIZE 1024
#define MAX_ITERATIONS 42

if (status == STATUS_ERROR) {  // 清楚表达含义
    handle_error();
}

char buffer[BUFFER_SIZE];
for (int i = 0; i < MAX_ITERATIONS; i++) {
    process(i);
}""",
            "使用有意义的常量名"
        )
        
        self.set_reference("代码整洁之道", "第17章", "P289-P295",
                          quote="避免使用魔术数字")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查魔术数字"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找数字字面量
        number_nodes = parser.find_nodes_by_type(root_node, 'number_literal')
        
        for number_node in number_nodes:
            number_text = parser.get_node_text(number_node, content).strip()
            
            if self._is_magic_number(number_text, number_node, parser, content):
                issue = self.create_issue(
                    file_info, number_node,
                    f"发现魔术数字 '{number_text}'",
                    f"考虑定义常量: #define MEANINGFUL_NAME {number_text}"
                )
                issues.append(issue)
                
        return issues
    
    def _is_magic_number(self, number_text: str, number_node, parser, content: str) -> bool:
        """判断是否为魔术数字"""
        try:
            number_value = float(number_text)
        except ValueError:
            return False
        
        # 常见的非魔术数字
        common_numbers = {0, 1, -1, 2, 10, 100, 1000}
        if number_value in common_numbers:
            return False
        
        # 检查是否在数组声明中
        if self._is_in_array_declaration(number_node):
            return True
        
        # 检查是否在比较表达式中
        if self._is_in_comparison(number_node):
            return True
        
        # 检查是否在循环条件中
        if self._is_in_loop_condition(number_node):
            return True
            
        return False
    
    def _is_in_array_declaration(self, number_node) -> bool:
        """检查是否在数组声明中"""
        parent = number_node.parent
        while parent:
            if parent.type == 'array_declarator':
                return True
            parent = parent.parent
        return False
    
    def _is_in_comparison(self, number_node) -> bool:
        """检查是否在比较表达式中"""
        parent = number_node.parent
        while parent:
            if parent.type == 'binary_expression':
                return True
            parent = parent.parent
        return False
    
    def _is_in_loop_condition(self, number_node) -> bool:
        """检查是否在循环条件中"""
        parent = number_node.parent
        while parent:
            if parent.type in ['for_statement', 'while_statement']:
                return True
            parent = parent.parent
        return False

class FunctionLengthRule(ASTRule):
    """函数长度检查规则"""
    
    def __init__(self):
        super().__init__("S002", "函数长度检查", "Function Length Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码风格"
        self.description_cn = "检测过长的函数"
        self.description_en = "Detect functions that are too long"
        self.why_cn = """
过长的函数会导致：
1. 难以理解和维护
2. 测试困难
3. 代码重用性差
4. 职责不清晰

建议将大函数拆分为多个小函数，每个函数只做一件事。
        """
        
        # 配置参数
        self.config = {
            'max_lines': 50,        # 最大行数
            'warning_lines': 30     # 警告行数
        }
        
        self.add_bad_example(
            """void huge_function() {
    // 超过50行的函数
    int a, b, c, d, e;
    // ... 很多变量声明
    
    // 第一部分逻辑
    if (condition1) {
        // ... 20行代码
    }
    
    // 第二部分逻辑
    for (int i = 0; i < 100; i++) {
        // ... 20行代码
    }
    
    // 第三部分逻辑
    while (condition2) {
        // ... 20行代码
    }
    // 总共超过60行
}""",
            "函数过长，职责不清晰"
        )
        
        self.add_good_example(
            """void well_structured_function() {
    initialize_variables();
    process_first_part();
    process_second_part();
    cleanup_resources();
}

void initialize_variables() {
    // 专门处理变量初始化
}

void process_first_part() {
    // 专门处理第一部分逻辑
}""",
            "将大函数拆分为多个小函数"
        )
        
        self.set_reference("代码整洁之道", "第3章", "P34-P42",
                          quote="函数应该短小")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查函数长度"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找函数定义
        functions = parser.find_function_definitions(root_node)
        
        for func_info in functions:
            func_node = func_info['node']
            func_name = parser.get_node_text(func_info['name_node'], content)
            
            # 计算函数行数
            start_line = func_node.start_point[0]
            end_line = func_node.end_point[0]
            line_count = end_line - start_line + 1
            
            max_lines = self.config.get('max_lines', 50)
            warning_lines = self.config.get('warning_lines', 30)
            
            if line_count > max_lines:
                issue = self.create_issue(
                    file_info, func_node,
                    f"函数'{func_name}'过长（{line_count}行），超过建议的{max_lines}行",
                    f"考虑将函数拆分为多个更小的函数",
                    Severity.WARNING
                )
                issues.append(issue)
            elif line_count > warning_lines:
                issue = self.create_issue(
                    file_info, func_node,
                    f"函数'{func_name}'较长（{line_count}行），接近建议的{max_lines}行限制",
                    f"考虑重构函数以提高可读性"
                )
                issues.append(issue)
                
        return issues

class VariableNamingRule(BaseRule):
    """变量命名检查规则"""
    
    def __init__(self):
        super().__init__("S003", "变量命名检查", "Variable Naming Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码风格"
        self.description_cn = "检测不规范的变量命名"
        self.description_en = "Detect improper variable naming"
        self.why_cn = """
良好的变量命名应该：
1. 具有描述性
2. 易于理解
3. 遵循一致的命名规范
4. 避免误导性名称

糟糕的变量名会降低代码可读性和维护性。
        """
        
        # 配置参数
        self.config = {
            'min_length': 2,            # 最小长度
            'allow_single_char': ['i', 'j', 'k', 'x', 'y', 'z'],  # 允许的单字符
            'forbidden_names': ['temp', 'tmp', 'data', 'var', 'val'],  # 禁用的通用名
            'require_camel_case': False  # 是否要求驼峰命名
        }
        
        self.add_bad_example(
            """int a, b, c;           // 无意义的单字符名
char temp[100];        // 通用的临时名称
int data;              // 过于宽泛
float x1, x2, x3;      // 数字后缀命名""",
            "变量名缺乏描述性"
        )
        
        self.add_good_example(
            """int width, height, depth;     // 有意义的名称
char user_name[100];           // 描述性命名
int student_count;             // 清楚表达用途
float temperature_celsius;     // 包含单位信息""",
            "使用有意义的变量名"
        )
        
        self.set_reference("C编程规范", "命名约定", "",
                          quote="变量名应该清楚地表达其用途")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查变量命名"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找变量声明
        variables = self._find_variable_declarations(root_node, parser, content)
        
        for var_info in variables:
            var_name = var_info['name']
            var_node = var_info['node']
            
            # 检查各种命名问题
            issue_msg = self._check_variable_name(var_name)
            if issue_msg:
                suggestion = self._suggest_better_name(var_name)
                issue = self.create_issue(
                    file_info, var_node,
                    f"变量'{var_name}'{issue_msg}",
                    suggestion
                )
                issues.append(issue)
                
        return issues
    
    def _find_variable_declarations(self, root_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找变量声明"""
        variables = []
        
        # 查找声明语句
        decl_nodes = parser.find_nodes_by_type(root_node, 'declaration')
        
        for decl_node in decl_nodes:
            # 查找声明中的变量名
            declarators = parser.find_nodes_by_type(decl_node, 'declarator')
            declarators.extend(parser.find_nodes_by_type(decl_node, 'init_declarator'))
            
            for declarator in declarators:
                var_name = self._extract_variable_name(declarator, parser, content)
                if var_name and not self._is_function_name(var_name, decl_node, parser, content):
                    variables.append({
                        'name': var_name,
                        'node': declarator,
                        'declaration': decl_node
                    })
                    
        return variables
    
    def _extract_variable_name(self, declarator_node, parser, content: str) -> str:
        """从声明器中提取变量名"""
        # 查找标识符
        identifiers = parser.find_nodes_by_type(declarator_node, 'identifier')
        if identifiers:
            return parser.get_node_text(identifiers[0], content)
        return ""
    
    def _is_function_name(self, name: str, decl_node, parser, content: str) -> bool:
        """判断是否为函数名"""
        # 简单检查：如果声明中包含括号，可能是函数
        decl_text = parser.get_node_text(decl_node, content)
        return '(' in decl_text and ')' in decl_text
    
    def _check_variable_name(self, var_name: str) -> str:
        """检查变量名是否有问题"""
        min_length = self.config.get('min_length', 2)
        allow_single_char = self.config.get('allow_single_char', [])
        forbidden_names = self.config.get('forbidden_names', [])
        
        # 检查长度
        if len(var_name) < min_length and var_name not in allow_single_char:
            return "名称过短，缺乏描述性"
        
        # 检查禁用名称
        if var_name.lower() in [name.lower() for name in forbidden_names]:
            return "使用了过于通用的名称"
        
        # 检查是否全是单字符+数字
        if re.match(r'^[a-z]\d+$', var_name):
            return "使用了数字后缀命名"
        
        # 检查是否全是大写（可能是宏）
        if var_name.isupper() and len(var_name) > 1:
            return "可能是宏定义，应使用小写变量名"
        
        return ""
    
    def _suggest_better_name(self, var_name: str) -> str:
        """建议更好的变量名"""
        suggestions = {
            'temp': 'temporary_buffer, working_data',
            'tmp': 'temporary_value, temp_result', 
            'data': 'user_data, input_buffer, message_content',
            'var': 'variable_name, current_value',
            'val': 'current_value, input_value, result_value',
            'i': 'index, counter, loop_var',
            'j': 'inner_index, column_index',
            'k': 'item_index, depth_level'
        }
        
        suggestion = suggestions.get(var_name.lower())
        if suggestion:
            return f"建议使用更具描述性的名称，如: {suggestion}"
        else:
            return "使用更具描述性的变量名，清楚表达变量的用途"

class CommentQualityRule(BaseRule):
    """注释质量检查规则"""
    
    def __init__(self):
        super().__init__("S004", "注释质量检查", "Comment Quality Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码风格"
        self.description_cn = "检测注释质量问题"
        self.description_en = "Detect comment quality issues"
        self.why_cn = """
良好的注释应该：
1. 解释为什么，而不是什么
2. 保持与代码同步
3. 避免冗余信息
4. 使用清晰的语言

糟糕的注释比没有注释更危险。
        """
        
        self.add_bad_example(
            """int i = 0;  // 将i设置为0
i++;        // i自增1
// TODO: 修复这个bug（已经存在6个月）

/* 这个函数很重要 */
void important_function() {
    // 重要的代码
    do_something();
}""",
            "注释冗余或过时"
        )
        
        self.add_good_example(
            """// 使用二分查找提高搜索效率
int binary_search(int arr[], int target) {
    // 为了避免整数溢出，使用 low + (high - low) / 2
    int mid = low + (high - low) / 2;
    
    /* 
     * 特殊处理边界情况：
     * 当数组只有一个元素时的比较逻辑
     */
    return result;
}""",
            "注释解释了实现原理和特殊处理"
        )
        
        self.set_reference("代码整洁之道", "第4章", "P53-P66",
                          quote="好的注释解释为什么，而不是什么")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查注释质量"""
        issues = []
        content = file_info['content']
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检查单行注释
            if '//' in line:
                comment = self._extract_comment(line, '//')
                issue_msg = self._check_comment_quality(comment, line_stripped)
                if issue_msg:
                    # 创建一个虚拟节点用于报告位置
                    issue = Issue(
                        rule_id=self.rule_id,
                        rule_name=self.name_cn,
                        file_path=file_info['path'],
                        line_number=i + 1,
                        column=line.find('//'),
                        severity=self.severity,
                        message=f"注释质量问题: {issue_msg}",
                        description=self.description_cn,
                        code_snippet=line,
                        suggestion="改进注释，解释代码的目的而不是描述代码做什么"
                    )
                    issues.append(issue)
            
            # 检查TODO/FIXME注释
            if any(keyword in line.upper() for keyword in ['TODO', 'FIXME', 'XXX', 'HACK']):
                if self._is_old_todo(line):
                    issue = Issue(
                        rule_id=self.rule_id,
                        rule_name=self.name_cn,
                        file_path=file_info['path'],
                        line_number=i + 1,
                        column=0,
                        severity=Severity.WARNING,
                        message="发现可能过时的TODO/FIXME注释",
                        description=self.description_cn,
                        code_snippet=line,
                        suggestion="清理过时的TODO注释或将其转换为正式的任务跟踪"
                    )
                    issues.append(issue)
                    
        return issues
    
    def _extract_comment(self, line: str, comment_start: str) -> str:
        """提取注释内容"""
        comment_index = line.find(comment_start)
        if comment_index != -1:
            return line[comment_index + len(comment_start):].strip()
        return ""
    
    def _check_comment_quality(self, comment: str, code_line: str) -> str:
        """检查注释质量"""
        if not comment:
            return ""
        
        comment_lower = comment.lower()
        
        # 检查是否是显而易见的注释
        obvious_patterns = [
            r'设置.*为.*',
            r'将.*设置为.*',
            r'.*自增.*',
            r'.*自减.*',
            r'调用.*函数',
            r'返回.*'
        ]
        
        for pattern in obvious_patterns:
            if re.search(pattern, comment):
                return "注释描述了显而易见的操作"
        
        # 检查是否过短
        if len(comment) < 5:
            return "注释过短，缺乏有用信息"
        
        # 检查是否只是重复变量名
        words_in_comment = set(re.findall(r'\w+', comment_lower))
        words_in_code = set(re.findall(r'\w+', code_line.lower()))
        
        if words_in_comment.issubset(words_in_code):
            return "注释只是重复了代码中的信息"
        
        return ""
    
    def _is_old_todo(self, line: str) -> bool:
        """检查是否是过时的TODO"""
        # 简单检查：包含日期或时间的TODO可能是过时的
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d+\s*(月|个月|年)\s*前',  # X月前
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, line):
                return True
        
        return False

class IndentationRule(BaseRule):
    """缩进检查规则"""
    
    def __init__(self):
        super().__init__("S005", "缩进检查", "Indentation Check")
        self.severity = Severity.SUGGESTION
        self.category = "代码风格"
        self.description_cn = "检测不一致的缩进"
        self.description_en = "Detect inconsistent indentation"
        self.why_cn = """
一致的缩进对于代码可读性至关重要：
1. 提高代码可读性
2. 减少理解错误
3. 体现代码结构
4. 团队协作标准化

应该在整个项目中使用一致的缩进方式。
        """
        
        # 配置参数
        self.config = {
            'indent_size': 4,      # 缩进大小
            'use_spaces': True,    # 使用空格而不是制表符
            'check_consistency': True  # 检查一致性
        }
        
        self.add_bad_example(
            """void function() {
  int a = 1;      // 2个空格
    int b = 2;    // 4个空格
\tint c = 3;     // 制表符
      int d = 4;  // 6个空格
}""",
            "缩进不一致"
        )
        
        self.add_good_example(
            """void function() {
    int a = 1;    // 一致的4个空格
    int b = 2;
    int c = 3;
    int d = 4;
}""",
            "使用一致的缩进"
        )
        
        self.set_reference("C编程规范", "代码格式", "",
                          quote="使用一致的缩进提高可读性")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查缩进"""
        issues = []
        content = file_info['content']
        lines = content.split('\n')
        
        indent_stats = {'spaces': [], 'tabs': 0, 'mixed': 0}
        
        for i, line in enumerate(lines):
            if not line.strip():  # 跳过空行
                continue
                
            indent_info = self._analyze_indentation(line)
            
            if indent_info['has_tabs'] and indent_info['has_spaces']:
                # 混合使用制表符和空格
                issue = Issue(
                    rule_id=self.rule_id,
                    rule_name=self.name_cn,
                    file_path=file_info['path'],
                    line_number=i + 1,
                    column=0,
                    severity=Severity.WARNING,
                    message="混合使用制表符和空格进行缩进",
                    description=self.description_cn,
                    code_snippet=line,
                    suggestion="统一使用空格或制表符进行缩进"
                )
                issues.append(issue)
                indent_stats['mixed'] += 1
            elif indent_info['has_tabs']:
                indent_stats['tabs'] += 1
            elif indent_info['spaces'] > 0:
                indent_stats['spaces'].append(indent_info['spaces'])
        
        # 分析整体缩进一致性
        if self.config.get('check_consistency', True):
            consistency_issues = self._check_indentation_consistency(
                indent_stats, file_info, lines
            )
            issues.extend(consistency_issues)
        
        return issues
    
    def _analyze_indentation(self, line: str) -> Dict[str, Any]:
        """分析行的缩进"""
        leading_spaces = 0
        has_tabs = False
        has_spaces = False
        
        for char in line:
            if char == ' ':
                leading_spaces += 1
                has_spaces = True
            elif char == '\t':
                has_tabs = True
            else:
                break
        
        return {
            'spaces': leading_spaces,
            'has_tabs': has_tabs,
            'has_spaces': has_spaces and leading_spaces > 0
        }
    
    def _check_indentation_consistency(self, stats: Dict[str, Any], 
                                     file_info: Dict[str, Any], lines: List[str]) -> List[Issue]:
        """检查缩进一致性"""
        issues = []
        
        if not stats['spaces']:
            return issues
        
        # 分析空格缩进模式
        space_counts = stats['spaces']
        if len(set(space_counts)) > 3:  # 如果有超过3种不同的缩进
            # 找到最常见的缩进
            from collections import Counter
            indent_counter = Counter(space_counts)
            most_common_indent = indent_counter.most_common(1)[0][0]
            
            # 报告不一致的缩进
            for i, line in enumerate(lines):
                if line.strip():  # 非空行
                    indent_info = self._analyze_indentation(line)
                    if (indent_info['spaces'] > 0 and 
                        indent_info['spaces'] != most_common_indent and
                        not indent_info['has_tabs']):
                        
                        issue = Issue(
                            rule_id=self.rule_id,
                            rule_name=self.name_cn,
                            file_path=file_info['path'],
                            line_number=i + 1,
                            column=0,
                            severity=self.severity,
                            message=f"缩进不一致：使用了{indent_info['spaces']}个空格，建议使用{most_common_indent}个",
                            description=self.description_cn,
                            code_snippet=line,
                            suggestion=f"调整缩进为{most_common_indent}个空格"
                        )
                        issues.append(issue)
        
        return issues


# 导出所有规则
__all__ = [
    'MagicNumberRule',
    'FunctionLengthRule', 
    'VariableNamingRule',
    'CommentQualityRule',
    'IndentationRule'
]

# 使用示例
if __name__ == "__main__":
    # 测试代码风格规则
    from ..core.parser import CodeParser
    from pathlib import Path
    
    test_code = """
    #include <stdio.h>
    
    void bad_function() {
        int a, b, temp;  // 变量名不规范
        char buffer[1024];  // 魔术数字
      int c = 3;  // 缩进不一致
    \tint d = 4;  // 混合缩进
        
        if (status == 3) {  // 魔术数字
            // i自增1
            i++;  // 显而易见的注释
        }
        
        // TODO: 修复这个bug（2020年写的）
        
        // 这是一个很长的函数，超过了建议的行数限制
        // 应该被拆分为多个小函数来提高可读性和维护性
        for (int i = 0; i < 100; i++) {
            // 大量重复代码
            process_data();
            validate_input();
            generate_output();
            cleanup_resources();
        }
    }
    
    int main() {
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
                MagicNumberRule(),
                FunctionLengthRule(),
                VariableNamingRule(),
                CommentQualityRule(),
                IndentationRule()
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