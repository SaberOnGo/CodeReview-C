#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: rules/embedded_rules.py
嵌入式专用规则 - 检测嵌入式开发中的特定问题
"""

from typing import List, Dict, Any
from .base_rule import BaseRule, ASTRule, PatternRule, Severity, Issue
import re

class VolatileUsageRule(BaseRule):
    """volatile关键字使用检查"""
    
    def __init__(self):
        super().__init__("E001", "volatile使用检查", "Volatile Usage Check")
        self.severity = Severity.WARNING
        self.category = "嵌入式安全"
        self.description_cn = "检测volatile关键字的正确使用"
        self.description_en = "Check proper usage of volatile keyword"
        self.why_cn = """
在嵌入式系统中，volatile关键字对于以下情况是必需的：
1. 硬件寄存器访问
2. 中断服务程序中使用的变量
3. 多线程共享变量
4. 信号处理函数中的变量

缺少volatile可能导致编译器优化错误。
        """
        
        self.add_bad_example(
            """uint32_t *gpio_register = (uint32_t*)0x40020000;
*gpio_register = 0x01;  // 可能被编译器优化掉

int interrupt_flag = 0;  // 在ISR中修改，应该是volatile
void timer_isr() {
    interrupt_flag = 1;  // 主循环可能看不到这个变化
}""",
            "缺少volatile导致编译器优化问题"
        )
        
        self.add_good_example(
            """volatile uint32_t *gpio_register = (volatile uint32_t*)0x40020000;
*gpio_register = 0x01;  // 不会被优化

volatile int interrupt_flag = 0;  // 正确使用volatile
void timer_isr() {
    interrupt_flag = 1;  // 保证主循环能看到变化
}""",
            "正确使用volatile关键字"
        )
        
        self.set_reference("嵌入式C编程", "volatile使用", "",
                          quote="volatile告诉编译器变量可能被意外修改")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查volatile使用"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找可能需要volatile的模式
        issues.extend(self._check_hardware_register_access(root_node, parser, content, file_info))
        issues.extend(self._check_global_variables_in_isr(root_node, parser, content, file_info))
        issues.extend(self._check_memory_mapped_io(root_node, parser, content, file_info))
        
        return issues
    
    def _check_hardware_register_access(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查硬件寄存器访问"""
        issues = []
        
        # 查找指针类型转换到特定地址（可能是寄存器地址）
        cast_nodes = parser.find_nodes_by_type(root_node, 'cast_expression')
        
        for cast_node in cast_nodes:
            cast_text = parser.get_node_text(cast_node, content)
            
            # 检查是否是转换到数字地址的指针
            if self._looks_like_register_address(cast_text):
                # 检查是否使用了volatile
                if 'volatile' not in cast_text:
                    issue = self.create_issue(
                        file_info, cast_node,
                        "硬件寄存器访问缺少volatile关键字",
                        "在指针类型前添加volatile关键字"
                    )
                    issues.append(issue)
                    
        return issues
    
    def _looks_like_register_address(self, text: str) -> bool:
        """判断是否像寄存器地址访问"""
        # 检查是否包含16进制地址
        hex_patterns = [
            r'0x[0-9A-Fa-f]{8}',  # 8位16进制地址
            r'0x[0-9A-Fa-f]{4}0{3,4}',  # 常见的寄存器基址
        ]
        
        for pattern in hex_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _check_global_variables_in_isr(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查ISR中使用的全局变量"""
        issues = []
        
        # 查找可能的ISR函数
        isr_functions = self._find_isr_functions(root_node, parser, content)
        
        for isr_func in isr_functions:
            # 在ISR中查找全局变量的使用
            global_vars = self._find_global_variable_usage(isr_func, parser, content)
            
            for var_name in global_vars:
                # 检查变量声明是否有volatile
                if not self._variable_has_volatile(root_node, var_name, parser, content):
                    issue = self.create_issue(
                        file_info, isr_func['node'],
                        f"ISR中使用的全局变量'{var_name}'缺少volatile",
                        f"将变量'{var_name}'声明为volatile"
                    )
                    issues.append(issue)
                    
        return issues
    
    def _find_isr_functions(self, root_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找中断服务程序函数"""
        isr_functions = []
        functions = parser.find_function_definitions(root_node)
        
        # 常见的ISR函数命名模式
        isr_patterns = [
            r'.*_isr\b',
            r'.*_handler\b', 
            r'.*_irq\b',
            r'isr_.*',
            r'handler_.*'
        ]
        
        for func_info in functions:
            func_name = parser.get_node_text(func_info['name_node'], content)
            
            for pattern in isr_patterns:
                if re.match(pattern, func_name, re.IGNORECASE):
                    isr_functions.append({
                        'node': func_info['node'],
                        'name': func_name
                    })
                    break
                    
        return isr_functions
    
    def _find_global_variable_usage(self, isr_func, parser, content: str) -> List[str]:
        """查找ISR中使用的全局变量"""
        # 简化实现：查找赋值操作中的标识符
        var_names = set()
        
        assign_nodes = parser.find_nodes_by_type(isr_func['node'], 'assignment_expression')
        for assign_node in assign_nodes:
            if len(assign_node.children) >= 1:
                left_node = assign_node.children[0]
                if left_node.type == 'identifier':
                    var_name = parser.get_node_text(left_node, content)
                    var_names.add(var_name)
                    
        return list(var_names)
    
    def _variable_has_volatile(self, root_node, var_name: str, parser, content: str) -> bool:
        """检查变量是否声明为volatile"""
        decl_nodes = parser.find_nodes_by_type(root_node, 'declaration')
        
        for decl_node in decl_nodes:
            decl_text = parser.get_node_text(decl_node, content)
            if var_name in decl_text and 'volatile' in decl_text:
                return True
                
        return False
    
    def _check_memory_mapped_io(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查内存映射IO访问"""
        issues = []
        
        # 查找解引用操作
        unary_nodes = parser.find_nodes_by_type(root_node, 'unary_expression')
        
        for unary_node in unary_nodes:
            if len(unary_node.children) >= 2:
                op_node = unary_node.children[0]
                operand_node = unary_node.children[1]
                
                op_text = parser.get_node_text(op_node, content)
                if op_text == '*':
                    operand_text = parser.get_node_text(operand_node, content)
                    
                    # 如果解引用的是类似寄存器的表达式
                    if self._looks_like_register_expression(operand_text):
                        # 检查上下文是否有volatile
                        context = self._get_surrounding_context(unary_node, parser, content)
                        if 'volatile' not in context:
                            issue = self.create_issue(
                                file_info, unary_node,
                                "内存映射IO访问建议使用volatile",
                                "在指针声明或类型转换中添加volatile"
                            )
                            issues.append(issue)
                            
        return issues
    
    def _looks_like_register_expression(self, text: str) -> bool:
        """判断是否像寄存器表达式"""
        register_patterns = [
            r'REG_\w+',
            r'\w+_REG',
            r'GPIO\w*',
            r'TIMER\w*',
            r'UART\w*'
        ]
        
        for pattern in register_patterns:
            if re.search(pattern, text):
                return True
                
        return False
    
    def _get_surrounding_context(self, node, parser, content: str) -> str:
        """获取节点的周围上下文"""
        # 获取包含该节点的语句
        current = node.parent
        while current and current.type not in ['expression_statement', 'declaration']:
            current = current.parent
            
        if current:
            return parser.get_node_text(current, content)
        
        return ""

class ISRFunctionRule(BaseRule):
    """中断服务程序规范检查"""
    
    def __init__(self):
        super().__init__("E002", "ISR函数规范", "ISR Function Rules")
        self.severity = Severity.WARNING
        self.category = "嵌入式安全"
        self.description_cn = "检测中断服务程序的规范性"
        self.description_en = "Check ISR function compliance"
        self.why_cn = """
中断服务程序应该遵循以下规范：
1. 尽可能短小和快速
2. 避免调用可能阻塞的函数
3. 避免使用浮点运算
4. 限制栈使用
5. 正确保存和恢复寄存器

违反这些规范可能导致系统不稳定。
        """
        
        self.add_bad_example(
            """void timer_isr() {
    printf("Timer interrupt\\n");  // 不应在ISR中使用printf
    
    float result = calculate_pi();  // 避免浮点运算
    
    delay_ms(100);  // 不应在ISR中延时
    
    malloc(1024);   // 不应在ISR中分配内存
}""",
            "ISR中使用了不当的函数调用"
        )
        
        self.add_good_example(
            """volatile int timer_count = 0;
volatile bool timer_flag = false;

void timer_isr() {
    timer_count++;      // 简单的计数操作
    timer_flag = true;  // 设置标志供主循环检查
    // ISR保持简短和快速
}""",
            "ISR只做必要的操作"
        )
        
        self.set_reference("嵌入式系统设计", "中断处理", "",
                          quote="ISR应该尽可能短小和快速")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查ISR函数规范"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 查找ISR函数
        isr_functions = self._find_isr_functions(root_node, parser, content)
        
        for isr_func in isr_functions:
            func_node = isr_func['node']
            func_name = isr_func['name']
            
            # 检查函数长度
            if self._is_function_too_long(func_node):
                issue = self.create_issue(
                    file_info, func_node,
                    f"ISR函数'{func_name}'过长",
                    "将复杂逻辑移至主循环，ISR只设置标志"
                )
                issues.append(issue)
            
            # 检查不当的函数调用
            bad_calls = self._find_bad_function_calls(func_node, parser, content)
            for call_info in bad_calls:
                issue = self.create_issue(
                    file_info, call_info['node'],
                    f"ISR中不应调用'{call_info['function']}'",
                    f"将'{call_info['function']}'调用移至主循环"
                )
                issues.append(issue)
            
            # 检查浮点运算
            if self._has_floating_point_operations(func_node, parser, content):
                issue = self.create_issue(
                    file_info, func_node,
                    f"ISR函数'{func_name}'中包含浮点运算",
                    "避免在ISR中使用浮点运算，改用整数运算"
                )
                issues.append(issue)
                
        return issues
    
    def _find_isr_functions(self, root_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找ISR函数（重用VolatileUsageRule中的方法）"""
        return VolatileUsageRule()._find_isr_functions(root_node, parser, content)
    
    def _is_function_too_long(self, func_node) -> bool:
        """检查函数是否过长"""
        start_line = func_node.start_point[0]
        end_line = func_node.end_point[0]
        line_count = end_line - start_line + 1
        
        # ISR函数建议不超过20行
        return line_count > 20
    
    def _find_bad_function_calls(self, func_node, parser, content: str) -> List[Dict[str, Any]]:
        """查找不当的函数调用"""
        bad_calls = []
        
        # 不应在ISR中调用的函数
        forbidden_functions = {
            'printf', 'fprintf', 'sprintf', 'scanf',  # IO函数
            'malloc', 'free', 'calloc', 'realloc',    # 内存分配
            'sleep', 'delay', 'usleep',               # 延时函数
            'wait', 'signal', 'mutex_lock',           # 同步函数
            'fopen', 'fclose', 'fread', 'fwrite'      # 文件操作
        }
        
        call_nodes = parser.find_nodes_by_type(func_node, 'call_expression')
        
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_name_node = call_node.children[0]
                func_name = parser.get_node_text(func_name_node, content)
                
                if func_name in forbidden_functions:
                    bad_calls.append({
                        'node': call_node,
                        'function': func_name
                    })
                    
        return bad_calls
    
    def _has_floating_point_operations(self, func_node, parser, content: str) -> bool:
        """检查是否有浮点运算"""
        func_text = parser.get_node_text(func_node, content)
        
        # 查找浮点类型声明
        float_types = ['float', 'double', 'long double']
        for float_type in float_types:
            if float_type in func_text:
                return True
        
        # 查找浮点常量
        if re.search(r'\d+\.\d+', func_text):
            return True
            
        return False

class HardwareRegisterRule(PatternRule):
    """硬件寄存器访问规范"""
    
    def __init__(self):
        super().__init__("E003", "硬件寄存器访问", "Hardware Register Access")
        self.severity = Severity.SUGGESTION
        self.category = "嵌入式规范"
        self.description_cn = "检测硬件寄存器访问的规范性"
        self.description_en = "Check hardware register access patterns"
        self.why_cn = """
硬件寄存器访问应该遵循以下规范：
1. 使用结构体而不是魔术数字偏移
2. 使用有意义的宏定义
3. 考虑寄存器访问的原子性
4. 正确处理只读和只写寄存器

规范的寄存器访问提高代码可读性和可维护性。
        """
        
        self.add_bad_example(
            """// 使用魔术数字偏移
*(uint32_t*)(0x40020000 + 0x14) = 0x01;

// 直接位操作没有宏定义
uint32_t reg = *(uint32_t*)0x40020000;
reg |= (1 << 5);  // 位5是什么意思？
*(uint32_t*)0x40020000 = reg;""",
            "使用魔术数字和不清晰的位操作"
        )
        
        self.add_good_example(
            """// 使用结构体定义
typedef struct {
    volatile uint32_t CR;     // 控制寄存器
    volatile uint32_t SR;     // 状态寄存器
    volatile uint32_t DR;     // 数据寄存器
} GPIO_TypeDef;

#define GPIO_BASE 0x40020000
#define GPIO ((GPIO_TypeDef*)GPIO_BASE)

// 使用有意义的宏
#define GPIO_PIN5_ENABLE  (1U << 5)

GPIO->CR |= GPIO_PIN5_ENABLE;""",
            "使用结构体和有意义的宏定义"
        )
        
        self.set_reference("嵌入式C编程规范", "寄存器访问", "",
                          quote="使用结构体定义提高寄存器访问的可读性")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查硬件寄存器访问"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 检查魔术数字地址
        issues.extend(self._check_magic_addresses(root_node, parser, content, file_info))
        
        # 检查位操作规范
        issues.extend(self._check_bit_operations(root_node, parser, content, file_info))
        
        return issues
    
    def _check_magic_addresses(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查魔术数字地址"""
        issues = []
        
        # 查找16进制数字字面量
        number_nodes = parser.find_nodes_by_type(root_node, 'number_literal')
        
        for number_node in number_nodes:
            number_text = parser.get_node_text(number_node, content)
            
            # 检查是否是地址模式的16进制数
            if self._looks_like_register_address(number_text):
                # 检查是否在指针转换中
                if self._is_in_pointer_cast(number_node):
                    issue = self.create_issue(
                        file_info, number_node,
                        f"使用了魔术地址 {number_text}",
                        "定义有意义的宏或使用寄存器结构体"
                    )
                    issues.append(issue)
                    
        return issues
    
    def _looks_like_register_address(self, text: str) -> bool:
        """判断是否像寄存器地址"""
        # 8位16进制地址模式
        return bool(re.match(r'0x[0-9A-Fa-f]{8}', text))
    
    def _is_in_pointer_cast(self, number_node) -> bool:
        """检查是否在指针转换中"""
        parent = number_node.parent
        while parent:
            if parent.type == 'cast_expression':
                return True
            parent = parent.parent
        return False
    
    def _check_bit_operations(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查位操作规范"""
        issues = []
        
        # 查找位操作表达式
        binary_nodes = parser.find_nodes_by_type(root_node, 'binary_expression')
        
        for binary_node in binary_nodes:
            if len(binary_node.children) >= 3:
                left_node = binary_node.children[0]
                op_node = binary_node.children[1]
                right_node = binary_node.children[2]
                
                op_text = parser.get_node_text(op_node, content)
                
                # 检查位操作
                if op_text in ['|', '&', '^', '<<', '>>']:
                    right_text = parser.get_node_text(right_node, content)
                    
                    # 检查是否使用了魔术数字
                    if self._is_magic_bit_pattern(right_text):
                        issue = self.create_issue(
                            file_info, binary_node,
                            f"位操作使用了魔术数字 {right_text}",
                            "定义有意义的位掩码宏"
                        )
                        issues.append(issue)
                        
        return issues
    
    def _is_magic_bit_pattern(self, text: str) -> bool:
        """判断是否是魔术位模式"""
        text = text.strip()
        
        # 检查16进制位模式
        if re.match(r'0x[0-9A-Fa-f]+', text):
            return True
        
        # 检查二进制位移模式 (1 << number)
        if re.match(r'\(\s*1\s*<<\s*\d+\s*\)', text):
            return False  # 这是好的模式
        
        # 检查裸露的位移数字
        if text.isdigit() and int(text) > 7:
            return True
            
        return False

class TaskStackRule(ASTRule):
    """任务栈检查规则（针对RTOS）"""
    
    def __init__(self):
        super().__init__("E004", "任务栈检查", "Task Stack Check")
        self.severity = Severity.SUGGESTION
        self.category = "嵌入式RTOS"
        self.description_cn = "检测RTOS任务栈使用问题"
        self.description_en = "Check RTOS task stack usage"
        self.why_cn = """
在RTOS环境中，任务栈管理很重要：
1. 避免栈溢出
2. 合理分配栈大小
3. 避免在栈上分配大对象
4. 检查栈使用情况

栈溢出是嵌入式系统中常见的问题。
        """
        
        self.add_bad_example(
            """void task_function() {
    char huge_buffer[4096];  // 在栈上分配大缓冲区
    
    recursive_function(100); // 深度递归可能栈溢出
}

// 栈大小可能不足
xTaskCreate(task_function, "Task", 128, NULL, 1, NULL);""",
            "栈上分配大对象和可能的栈溢出"
        )
        
        self.add_good_example(
            """// 使用静态或动态分配
static char shared_buffer[4096];  // 静态分配

void task_function() {
    char small_buffer[64];  // 小缓冲区可以在栈上
    
    // 或者使用动态分配
    char *buffer = malloc(4096);
    if (buffer) {
        // 使用buffer
        free(buffer);
    }
}

// 合理的栈大小
xTaskCreate(task_function, "Task", 512, NULL, 1, NULL);""",
            "合理的内存分配策略"
        )
        
        self.set_reference("FreeRTOS开发指南", "任务管理", "",
                          quote="合理分配任务栈大小避免溢出")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查任务栈使用"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 检查大数组声明
        issues.extend(self._check_large_stack_arrays(root_node, parser, content, file_info))
        
        # 检查任务创建的栈大小
        issues.extend(self._check_task_stack_sizes(root_node, parser, content, file_info))
        
        # 检查递归函数
        issues.extend(self._check_recursive_functions(root_node, parser, content, file_info))
        
        return issues
    
    def _check_large_stack_arrays(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查大数组声明"""
        issues = []
        
        # 查找数组声明
        array_declarators = parser.find_nodes_by_type(root_node, 'array_declarator')
        
        for array_decl in array_declarators:
            if len(array_decl.children) >= 3:
                size_node = array_decl.children[2]  # 跳过name和'['
                size_text = parser.get_node_text(size_node, content).strip()
                
                try:
                    size = int(size_text)
                    if size > 1024:  # 大于1KB的数组
                        # 检查是否在函数内（局部变量）
                        if self._is_local_variable(array_decl):
                            issue = self.create_issue(
                                file_info, array_decl,
                                f"在栈上声明了大数组（{size}字节）",
                                "考虑使用静态分配或动态分配"
                            )
                            issues.append(issue)
                except ValueError:
                    pass  # 非数字大小，跳过
                    
        return issues
    
    def _is_local_variable(self, decl_node) -> bool:
        """检查是否是局部变量"""
        # 检查是否在函数内
        current = decl_node.parent
        while current:
            if current.type == 'function_definition':
                return True
            current = current.parent
        return False
    
    def _check_task_stack_sizes(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查任务栈大小"""
        issues = []
        
        # 查找任务创建函数调用
        task_create_functions = [
            'xTaskCreate', 'xTaskCreateStatic', 
            'osThreadCreate', 'osThreadNew'
        ]
        
        call_nodes = parser.find_nodes_by_type(root_node, 'call_expression')
        
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                func_name_node = call_node.children[0]
                func_name = parser.get_node_text(func_name_node, content)
                
                if func_name in task_create_functions:
                    # 分析栈大小参数
                    stack_size = self._extract_stack_size_parameter(call_node, parser, content)
                    if stack_size and stack_size < 256:
                        issue = self.create_issue(
                            file_info, call_node,
                            f"任务栈大小可能过小（{stack_size}字节）",
                            "考虑增加栈大小以避免栈溢出"
                        )
                        issues.append(issue)
                        
        return issues
    
    def _extract_stack_size_parameter(self, call_node, parser, content: str) -> int:
        """提取栈大小参数"""
        if len(call_node.children) >= 2:
            args_node = call_node.children[1]
            if args_node.type == 'argument_list':
                # xTaskCreate的第3个参数通常是栈大小
                args = [child for child in args_node.children if child.type != ',']
                if len(args) >= 3:
                    stack_size_node = args[2]
                    stack_size_text = parser.get_node_text(stack_size_node, content)
                    try:
                        return int(stack_size_text)
                    except ValueError:
                        pass
        return None
    
    def _check_recursive_functions(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查递归函数"""
        issues = []
        
        functions = parser.find_function_definitions(root_node)
        
        for func_info in functions:
            func_node = func_info['node']
            func_name = parser.get_node_text(func_info['name_node'], content)
            
            # 检查函数是否调用自身
            if self._calls_itself(func_node, func_name, parser, content):
                issue = self.create_issue(
                    file_info, func_node,
                    f"函数'{func_name}'是递归函数",
                    "在嵌入式系统中避免深度递归，考虑使用迭代方式"
                )
                issues.append(issue)
                
        return issues
    
    def _calls_itself(self, func_node, func_name: str, parser, content: str) -> bool:
        """检查函数是否调用自身"""
        call_nodes = parser.find_nodes_by_type(func_node, 'call_expression')
        
        for call_node in call_nodes:
            if len(call_node.children) > 0:
                called_func_node = call_node.children[0]
                called_func_name = parser.get_node_text(called_func_node, content)
                
                if called_func_name == func_name:
                    return True
                    
        return False

class PowerManagementRule(BaseRule):
    """电源管理检查规则"""
    
    def __init__(self):
        super().__init__("E005", "电源管理检查", "Power Management Check")
        self.severity = Severity.SUGGESTION
        self.category = "嵌入式优化"
        self.description_cn = "检测电源管理相关问题"
        self.description_en = "Check power management issues"
        self.why_cn = """
在电池供电的嵌入式系统中，电源管理很重要：
1. 及时关闭未使用的外设
2. 使用低功耗模式
3. 避免忙等待循环
4. 合理使用睡眠模式

良好的电源管理可以显著延长电池寿命。
        """
        
        self.add_bad_example(
            """void main_loop() {
    while (1) {
        if (button_pressed()) {
            handle_button();
        }
        // 忙等待，浪费电力
    }
}

void init_peripherals() {
    // 启用所有外设，即使不需要
    RCC->APB1ENR = 0xFFFFFFFF;
}""",
            "忙等待和不必要的外设启用"
        )
        
        self.add_good_example(
            """void main_loop() {
    while (1) {
        if (button_pressed()) {
            handle_button();
        } else {
            // 进入低功耗模式
            __WFI();  // 等待中断
        }
    }
}

void init_peripherals() {
    // 只启用需要的外设
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN | RCC_APB1ENR_USART2EN;
}""",
            "使用睡眠模式和选择性启用外设"
        )
        
        self.set_reference("嵌入式低功耗设计", "电源管理", "",
                          quote="合理的电源管理是嵌入式系统设计的关键")
    
    def check(self, file_info: Dict[str, Any], parser) -> List[Issue]:
        """检查电源管理"""
        issues = []
        root_node = file_info['root_node']
        content = file_info['content']
        
        # 检查忙等待循环
        issues.extend(self._check_busy_wait_loops(root_node, parser, content, file_info))
        
        # 检查外设时钟管理
        issues.extend(self._check_peripheral_clock_management(root_node, parser, content, file_info))
        
        return issues
    
    def _check_busy_wait_loops(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查忙等待循环"""
        issues = []
        
        # 查找while循环
        while_nodes = parser.find_nodes_by_type(root_node, 'while_statement')
        
        for while_node in while_nodes:
            # 检查是否是无限循环
            if self._is_infinite_loop(while_node, parser, content):
                # 检查循环体是否有睡眠或等待语句
                if not self._has_sleep_or_wait(while_node, parser, content):
                    issue = self.create_issue(
                        file_info, while_node,
                        "发现可能的忙等待循环",
                        "在循环中添加睡眠模式或中断等待"
                    )
                    issues.append(issue)
                    
        return issues
    
    def _is_infinite_loop(self, while_node, parser, content: str) -> bool:
        """检查是否是无限循环"""
        if len(while_node.children) >= 2:
            condition_node = while_node.children[1]  # 跳过'while'
            condition_text = parser.get_node_text(condition_node, content)
            
            # 检查常见的无限循环模式
            infinite_patterns = ['(1)', '(true)', '(TRUE)']
            return any(pattern in condition_text for pattern in infinite_patterns)
        
        return False
    
    def _has_sleep_or_wait(self, while_node, parser, content: str) -> bool:
        """检查是否有睡眠或等待语句"""
        loop_body_text = parser.get_node_text(while_node, content)
        
        sleep_patterns = [
            '__WFI', '__WFE',  # ARM睡眠指令
            'sleep', 'delay', 'wait',
            'osDelay', 'vTaskDelay',  # RTOS延时函数
            'HAL_PWR_EnterSLEEPMode'  # HAL睡眠函数
        ]
        
        return any(pattern in loop_body_text for pattern in sleep_patterns)
    
    def _check_peripheral_clock_management(self, root_node, parser, content: str, file_info) -> List[Issue]:
        """检查外设时钟管理"""
        issues = []
        
        # 查找可能的时钟启用操作
        assignment_nodes = parser.find_nodes_by_type(root_node, 'assignment_expression')
        
        for assign_node in assignment_nodes:
            assign_text = parser.get_node_text(assign_node, content)
            
            # 检查是否是批量启用所有时钟
            if self._is_bulk_clock_enable(assign_text):
                issue = self.create_issue(
                    file_info, assign_node,
                    "批量启用所有外设时钟",
                    "只启用实际需要的外设时钟以节省电力"
                )
                issues.append(issue)
                
        return issues
    
    def _is_bulk_clock_enable(self, text: str) -> bool:
        """检查是否是批量时钟启用"""
        # 检查是否设置所有位为1
        bulk_patterns = [
            r'0xFFFFFFFF',
            r'0xFFF',
            r'.*ENR\s*=\s*-1'
        ]
        
        return any(re.search(pattern, text) for pattern in bulk_patterns)


# 导出所有规则
__all__ = [
    'VolatileUsageRule',
    'ISRFunctionRule',
    'HardwareRegisterRule', 
    'TaskStackRule',
    'PowerManagementRule'
]

# 使用示例
if __name__ == "__main__":
    # 测试嵌入式规则
    from ..core.parser import CodeParser
    from pathlib import Path
    
    test_code = """
    #include <stdint.h>
    
    // 全局变量，在ISR中使用但没有volatile
    int global_counter = 0;
    
    void timer_isr() {
        printf("Timer interrupt\\n");  // 不应在ISR中使用
        global_counter++;  // 应该是volatile
        
        float result = 3.14 * 2.0;  // ISR中的浮点运算
    }
    
    void main_task() {
        char huge_buffer[4096];  // 栈上的大数组
        
        // 硬件寄存器访问
        *(uint32_t*)0x40020000 = 0x01;
        
        while (1) {
            if (global_counter > 100) {
                // 处理
            }
            // 忙等待循环
        }
    }
    
    void init() {
        // 批量启用时钟
        *(uint32_t*)0x40023830 = 0xFFFFFFFF;
        
        // 创建任务，栈可能过小
        xTaskCreate(main_task, "Main", 128, NULL, 1, NULL);
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
                VolatileUsageRule(),
                ISRFunctionRule(),
                HardwareRegisterRule(),
                TaskStackRule(),
                PowerManagementRule()
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