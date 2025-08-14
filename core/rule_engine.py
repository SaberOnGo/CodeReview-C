#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: core/rule_engine.py
规则引擎 - 代码规则检查核心引擎 (更新版本)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import importlib

# 导入规则基类
from ..rules.base_rule import BaseRule, Issue, Severity

class RuleEngine:
    """规则引擎主类 - 更新版本"""
    
    def __init__(self):
        self.rules: List[BaseRule] = []
        self.rule_templates = {}
        self.rule_modules = {}
        
        # 自动加载所有规则
        self._load_all_rules()
        self._load_templates()
        
    def _load_all_rules(self):
        """自动加载所有规则模块"""
        try:
            # 导入内存安全规则
            from ..rules.memory_rules import (
                ArrayBoundsRule, NullPointerRule, MemoryLeakRule,
                BufferOverflowRule, UseAfterFreeRule
            )
            
            # 导入逻辑错误规则
            from ..rules.logic_rules import (
                AssignmentInConditionRule, SwitchFallthroughRule,
                UnusedVariableRule, FunctionReturnRule, DivisionByZeroRule
            )
            
            # 创建规则实例
            self.rules = [
                # 内存安全规则
                ArrayBoundsRule(),
                NullPointerRule(),
                MemoryLeakRule(),
                BufferOverflowRule(),
                UseAfterFreeRule(),
                
                # 逻辑错误规则
                AssignmentInConditionRule(),
                SwitchFallthroughRule(),
                UnusedVariableRule(),
                FunctionReturnRule(),
                DivisionByZeroRule(),
            ]
            
            print(f"✅ 成功加载 {len(self.rules)} 个规则")
            
        except ImportError as e:
            print(f"⚠️ 规则加载失败: {e}")
            # 如果导入失败，创建基本规则
            self._create_basic_rules()
    
    def _create_basic_rules(self):
        """创建基本规则（如果模块导入失败）"""
        from ..rules.base_rule import BaseRule, Severity
        
        class BasicArrayBoundsRule(BaseRule):
            def __init__(self):
                super().__init__("C001", "数组越界检查", "Array Bounds Check")
                self.severity = Severity.CRITICAL
                self.category = "内存安全"
                
            def check(self, file_info, parser):
                return []  # 简化实现
        
        class BasicAssignmentRule(BaseRule):
            def __init__(self):
                super().__init__("L001", "赋值写成判断", "Assignment in Condition")
                self.severity = Severity.CRITICAL
                self.category = "逻辑错误"
                
            def check(self, file_info, parser):
                return []  # 简化实现
        
        self.rules = [
            BasicArrayBoundsRule(),
            BasicAssignmentRule(),
        ]
        
    def _load_templates(self):
        """加载规则模板"""
        templates_dir = Path(__file__).parent.parent / 'templates'
        
        # 内置模板
        self.rule_templates = {
            "beginner": {
                "name": "新手友好版",
                "description": "包含最基础和最重要的代码检查规则",
                "enabled_rules": ["C001", "C002", "L001", "L002", "L005"],
                "rule_settings": {}
            },
            "c_traps": {
                "name": "C陷阱与缺陷版",
                "description": "基于《C陷阱与缺陷》书籍的规则集",
                "enabled_rules": ["C001", "C002", "C004", "L001", "L002", "L005"],
                "rule_settings": {}
            },
            "embedded": {
                "name": "嵌入式专用版",
                "description": "适用于ESP32/STM32等嵌入式开发",
                "enabled_rules": ["C001", "C002", "C003", "C004", "L001", "L005"],
                "rule_settings": {}
            },
            "misra_c": {
                "name": "MISRA-C精选版",
                "description": "工业级代码标准规则",
                "enabled_rules": ["C001", "C002", "C003", "C004", "C005", "L001", "L002"],
                "rule_settings": {}
            },
            "enterprise": {
                "name": "企业级严格版",
                "description": "包含所有规则的完整检查",
                "enabled_rules": [rule.rule_id for rule in self.rules],
                "rule_settings": {}
            }
        }
        
        # 尝试从文件加载模板
        if templates_dir.exists():
            for template_file in templates_dir.glob('*.json'):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        self.rule_templates[template_file.stem] = template_data
                except Exception as e:
                    print(f"⚠️ 加载模板失败 {template_file}: {e}")
    
    def apply_template(self, template_name: str):
        """应用规则模板"""
        if template_name not in self.rule_templates:
            print(f"⚠️ 未找到模板: {template_name}")
            return
            
        template = self.rule_templates[template_name]
        enabled_rules = template.get('enabled_rules', [])
        rule_settings = template.get('rule_settings', {})
        
        # 启用/禁用规则
        for rule in self.rules:
            rule.enabled = rule.rule_id in enabled_rules
            
            # 应用规则特定设置
            if rule.rule_id in rule_settings:
                settings = rule_settings[rule.rule_id]
                if 'severity' in settings:
                    rule.severity = Severity(settings['severity'])
                    
        print(f"✅ 已应用模板: {template['name']} ({len(enabled_rules)}个规则)")
    
    def get_enabled_rules(self) -> List[BaseRule]:
        """获取启用的规则"""
        return [rule for rule in self.rules if rule.enabled]
    
    def get_rules_by_category(self) -> Dict[str, List[BaseRule]]:
        """按分类获取规则"""
        categories = {}
        for rule in self.rules:
            category = rule.category
            if category not in categories:
                categories[category] = []
            categories[category].append(rule)
        return categories
    
    def get_rule_by_id(self, rule_id: str) -> Optional[BaseRule]:
        """根据ID获取规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def add_rule(self, rule: BaseRule):
        """添加新规则"""
        if self.get_rule_by_id(rule.rule_id):
            print(f"⚠️ 规则 {rule.rule_id} 已存在，将被替换")
            self.remove_rule(rule.rule_id)
        
        self.rules.append(rule)
        print(f"✅ 已添加规则: {rule.rule_id} - {rule.name_cn}")
    
    def remove_rule(self, rule_id: str):
        """移除规则"""
        self.rules = [rule for rule in self.rules if rule.rule_id != rule_id]
    
    def check_files(self, parsed_files: List[Dict[str, Any]], parser) -> List[Issue]:
        """检查文件列表"""
        all_issues = []
        enabled_rules = self.get_enabled_rules()
        
        if not enabled_rules:
            print("⚠️ 没有启用的规则")
            return all_issues
        
        print(f"🔍 使用 {len(enabled_rules)} 个规则检查 {len(parsed_files)} 个文件")
        
        for i, file_info in enumerate(parsed_files):
            file_path = file_info.get('path', 'unknown')
            print(f"📄 检查文件 [{i+1}/{len(parsed_files)}]: {file_path}")
            
            file_issues = []
            
            for rule in enabled_rules:
                try:
                    # 检查规则是否适用于当前文件
                    if rule.is_applicable(file_info):
                        issues = rule.check(file_info, parser)
                        file_issues.extend(issues)
                        
                        if issues:
                            print(f"  ⚠️ {rule.rule_id}: 发现 {len(issues)} 个问题")
                            
                except Exception as e:
                    print(f"  ❌ 规则 {rule.rule_id} 检查失败: {e}")
                    
            all_issues.extend(file_issues)
            print(f"  📊 文件总问题数: {len(file_issues)}")
        
        print(f"🎯 检查完成，总计发现 {len(all_issues)} 个问题")
        return all_issues
    
    def generate_rule_summary(self) -> Dict[str, Any]:
        """生成规则摘要"""
        categories = self.get_rules_by_category()
        enabled_rules = self.get_enabled_rules()
        
        summary = {
            'total_rules': len(self.rules),
            'enabled_rules': len(enabled_rules),
            'categories': {},
            'severity_distribution': {
                '严重': 0,
                '警告': 0,
                '建议': 0
            }
        }
        
        # 按分类统计
        for category, rules in categories.items():
            enabled_count = sum(1 for rule in rules if rule.enabled)
            summary['categories'][category] = {
                'total': len(rules),
                'enabled': enabled_count
            }
        
        # 按严重程度统计
        for rule in enabled_rules:
            summary['severity_distribution'][rule.severity.value] += 1
        
        return summary
    
    def export_config(self, config_path: Path):
        """导出当前配置"""
        config = {
            'version': '1.0',
            'export_time': str(Path().cwd()),
            'enabled_rules': [rule.rule_id for rule in self.rules if rule.enabled],
            'rule_settings': {}
        }
        
        # 导出每个规则的详细设置
        for rule in self.rules:
            config['rule_settings'][rule.rule_id] = {
                'enabled': rule.enabled,
                'severity': rule.severity.value,
                'category': rule.category,
                'config': getattr(rule, 'config', {})
            }
        
        # 写入文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 配置已导出到: {config_path}")
    
    def import_config(self, config_path: Path):
        """导入配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            enabled_rules = config.get('enabled_rules', [])
            rule_settings = config.get('rule_settings', {})
            
            # 应用配置
            for rule in self.rules:
                rule.enabled = rule.rule_id in enabled_rules
                
                if rule.rule_id in rule_settings:
                    settings = rule_settings[rule.rule_id]
                    
                    # 更新严重程度
                    if 'severity' in settings:
                        try:
                            rule.severity = Severity(settings['severity'])
                        except ValueError:
                            print(f"⚠️ 无效的严重程度: {settings['severity']}")
                    
                    # 更新规则配置
                    if 'config' in settings:
                        rule.config = settings['config']
            
            print(f"✅ 配置已从 {config_path} 导入")
            
        except Exception as e:
            print(f"❌ 导入配置失败: {e}")
            raise
    
    def validate_rules(self) -> List[str]:
        """验证规则完整性"""
        issues = []
        rule_ids = set()
        
        for rule in self.rules:
            # 检查重复ID
            if rule.rule_id in rule_ids:
                issues.append(f"重复的规则ID: {rule.rule_id}")
            rule_ids.add(rule.rule_id)
            
            # 检查必需属性
            if not rule.name_cn:
                issues.append(f"规则 {rule.rule_id} 缺少中文名称")
                
            if not rule.description_cn:
                issues.append(f"规则 {rule.rule_id} 缺少中文描述")
                
            if not rule.category:
                issues.append(f"规则 {rule.rule_id} 缺少分类")
        
        return issues
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """获取模板信息"""
        template = self.rule_templates.get(template_name)
        if not template:
            return None
            
        # 计算模板统计
        enabled_rules = template.get('enabled_rules', [])
        categories = {}
        severity_count = {'严重': 0, '警告': 0, '建议': 0}
        
        for rule_id in enabled_rules:
            rule = self.get_rule_by_id(rule_id)
            if rule:
                category = rule.category
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
                
                severity_count[rule.severity.value] += 1
        
        return {
            'name': template.get('name', template_name),
            'description': template.get('description', ''),
            'rule_count': len(enabled_rules),
            'categories': categories,
            'severity_distribution': severity_count
        }
    
    def search_rules(self, query: str) -> List[BaseRule]:
        """搜索规则"""
        query = query.lower()
        matching_rules = []
        
        for rule in self.rules:
            if (query in rule.rule_id.lower() or
                query in rule.name_cn.lower() or
                query in rule.description_cn.lower() or
                query in rule.category.lower()):
                matching_rules.append(rule)
        
        return matching_rules
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则统计信息"""
        stats = {
            'total_rules': len(self.rules),
            'enabled_rules': len(self.get_enabled_rules()),
            'categories': {},
            'severity_distribution': {'严重': 0, '警告': 0, '建议': 0},
            'templates_available': len(self.rule_templates)
        }
        
        # 按分类统计
        for rule in self.rules:
            category = rule.category
            if category not in stats['categories']:
                stats['categories'][category] = {'total': 0, 'enabled': 0}
            
            stats['categories'][category]['total'] += 1
            if rule.enabled:
                stats['categories'][category]['enabled'] += 1
                stats['severity_distribution'][rule.severity.value] += 1
        
        return stats

    def create_custom_template(self, name: str, description: str, enabled_rule_ids: List[str]) -> bool:
        """创建自定义模板"""
        try:
            # 验证规则ID
            valid_rule_ids = []
            for rule_id in enabled_rule_ids:
                if self.get_rule_by_id(rule_id):
                    valid_rule_ids.append(rule_id)
                else:
                    print(f"⚠️ 无效的规则ID: {rule_id}")
            
            # 创建模板
            template_key = name.lower().replace(' ', '_')
            self.rule_templates[template_key] = {
                'name': name,
                'description': description,
                'enabled_rules': valid_rule_ids,
                'rule_settings': {},
                'custom': True
            }
            
            print(f"✅ 已创建自定义模板: {name} ({len(valid_rule_ids)}个规则)")
            return True
            
        except Exception as e:
            print(f"❌ 创建模板失败: {e}")
            return False


# 规则加载器工具类
class RuleLoader:
    """规则加载器 - 用于动态加载规则模块"""
    
    @staticmethod
    def load_rules_from_module(module_path: str) -> List[BaseRule]:
        """从模块加载规则"""
        try:
            module = importlib.import_module(module_path)
            rules = []
            
            # 查找模块中的规则类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseRule) and 
                    attr != BaseRule):
                    try:
                        rule_instance = attr()
                        rules.append(rule_instance)
                    except Exception as e:
                        print(f"⚠️ 创建规则实例失败 {attr_name}: {e}")
            
            return rules
            
        except ImportError as e:
            print(f"❌ 模块导入失败 {module_path}: {e}")
            return []
    
    @staticmethod
    def discover_rule_modules(rules_dir: Path) -> List[str]:
        """发现规则模块"""
        module_paths = []
        
        if not rules_dir.exists():
            return module_paths
        
        for py_file in rules_dir.glob('*_rules.py'):
            if py_file.name != '__init__.py':
                module_name = py_file.stem
                module_paths.append(f'rules.{module_name}')
        
        return module_paths


# 使用示例
if __name__ == "__main__":
    # 测试规则引擎
    engine = RuleEngine()
    
    # 显示规则统计
    stats = engine.get_rule_statistics()
    print("📊 规则统计:")
    print(f"  总规则数: {stats['total_rules']}")
    print(f"  已启用: {stats['enabled_rules']}")
    print(f"  可用模板: {stats['templates_available']}")
    
    # 显示分类统计
    print("\n📁 分类统计:")
    for category, count_info in stats['categories'].items():
        print(f"  {category}: {count_info['enabled']}/{count_info['total']}")
    
    # 测试模板应用
    print("\n🔧 测试模板应用:")
    engine.apply_template('beginner')
    
    # 生成规则摘要
    summary = engine.generate_rule_summary()
    print(f"\n📋 当前配置摘要:")
    print(f"  启用规则: {summary['enabled_rules']}/{summary['total_rules']}")
    
    # 验证规则
    validation_issues = engine.validate_rules()
    if validation_issues:
        print(f"\n⚠️ 发现 {len(validation_issues)} 个规则问题:")
        for issue in validation_issues:
            print(f"  - {issue}")
    else:
        print("\n✅ 所有规则验证通过")