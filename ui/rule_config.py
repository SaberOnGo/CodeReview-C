#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: ui/rule_config.py
规则配置界面 - 图形化的规则管理和配置界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from typing import Dict, List, Optional
from pathlib import Path
import json

class RuleConfigWindow:
    """规则配置窗口类"""
    
    def __init__(self, parent, rule_engine):
        self.parent = parent
        self.rule_engine = rule_engine
        self.window = None
        
        # 界面组件
        self.category_tree = None
        self.rule_listbox = None
        self.detail_text = None
        self.example_notebook = None
        
        # 数据
        self.categories = {}
        self.selected_rule = None
        self.changes_made = False
        
        self._organize_rules_by_category()
        
    def _organize_rules_by_category(self):
        """按分类组织规则"""
        self.categories = {}
        
        for rule in self.rule_engine.rules:
            category = rule.category
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(rule)
            
        # 按规则ID排序
        for category in self.categories:
            self.categories[category].sort(key=lambda r: r.rule_id)
    
    def show(self):
        """显示配置窗口"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("规则配置 - CTrapsDetector")
        self.window.geometry("1000x700")
        self.window.transient(self.parent)
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.setup_ui()
        self.load_rule_data()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主容器
        main_container = ctk.CTkFrame(self.window)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        self.create_toolbar(main_container)
        
        # 主要内容区域 - 使用PanedWindow分割
        content_frame = ctk.CTkFrame(main_container)
        content_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # 左侧：分类和规则列表
        self.create_rule_list_panel(content_frame)
        
        # 右侧：规则详情
        self.create_rule_detail_panel(content_frame)
        
        # 底部按钮
        self.create_bottom_buttons(main_container)
        
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ctk.CTkFrame(parent)
        toolbar.pack(fill="x", pady=(0, 10))
        
        # 左侧 - 模板选择
        ctk.CTkLabel(toolbar, text="规则模板:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        
        self.template_var = tk.StringVar(value="当前配置")
        template_menu = ctk.CTkOptionMenu(
            toolbar,
            variable=self.template_var,
            values=["当前配置", "新手友好版", "C陷阱与缺陷版", "嵌入式专用版", "MISRA-C精选版", "企业级严格版"],
            command=self.on_template_change,
            width=150
        )
        template_menu.pack(side="left", padx=10, pady=10)
        
        # 右侧 - 操作按钮
        button_frame = ctk.CTkFrame(toolbar)
        button_frame.pack(side="right", padx=10, pady=5)
        
        ctk.CTkButton(
            button_frame,
            text="全部启用",
            width=80,
            command=self.enable_all_rules
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            button_frame,
            text="全部禁用", 
            width=80,
            command=self.disable_all_rules
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            button_frame,
            text="重置默认",
            width=80,
            command=self.reset_to_default
        ).pack(side="left", padx=2)
        
    def create_rule_list_panel(self, parent):
        """创建规则列表面板"""
        # 左侧面板容器
        left_panel = ctk.CTkFrame(parent)
        left_panel.pack(side="left", fill="both", expand=False, padx=(0, 5))
        left_panel.configure(width=400)
        
        # 搜索框
        search_frame = ctk.CTkFrame(left_panel)
        search_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(search_frame, text="🔍 搜索规则:").pack(side="left", padx=5, pady=8)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="输入规则ID或名称..."
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=5, pady=8)
        
        # 分类树和规则列表容器
        list_container = ctk.CTkFrame(left_panel)
        list_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 分类标签
        ctk.CTkLabel(
            list_container,
            text="规则分类",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # 创建分类树状视图
        tree_frame = ctk.CTkFrame(list_container)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 使用tkinter的Treeview
        self.category_tree = ttk.Treeview(tree_frame, height=20)
        self.category_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # 滚动条
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.category_tree.yview)
        tree_scroll.pack(side="right", fill="y", pady=5)
        self.category_tree.configure(yscrollcommand=tree_scroll.set)
        
        # 绑定选择事件
        self.category_tree.bind('<<TreeviewSelect>>', self.on_rule_select)
        
    def create_rule_detail_panel(self, parent):
        """创建规则详情面板"""
        # 右侧面板容器
        right_panel = ctk.CTkFrame(parent)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # 规则标题和控制
        header_frame = ctk.CTkFrame(right_panel)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.rule_title_label = ctk.CTkLabel(
            header_frame,
            text="选择规则查看详情",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.rule_title_label.pack(side="left", padx=10, pady=10)
        
        # 启用/禁用开关
        self.rule_enabled_var = tk.BooleanVar()
        self.rule_enabled_switch = ctk.CTkSwitch(
            header_frame,
            text="启用",
            variable=self.rule_enabled_var,
            command=self.on_rule_enabled_change
        )
        self.rule_enabled_switch.pack(side="right", padx=10, pady=10)
        
        # 严重程度选择
        severity_frame = ctk.CTkFrame(header_frame)
        severity_frame.pack(side="right", padx=(0, 10), pady=10)
        
        ctk.CTkLabel(severity_frame, text="严重程度:").pack(side="left", padx=5)
        
        self.severity_var = tk.StringVar()
        severity_menu = ctk.CTkOptionMenu(
            severity_frame,
            variable=self.severity_var,
            values=["严重", "警告", "建议"],
            command=self.on_severity_change,
            width=80
        )
        severity_menu.pack(side="left", padx=5)
        
        # 详情内容 - 使用Notebook标签页
        self.detail_notebook = ctk.CTkTabview(right_panel)
        self.detail_notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 基本信息标签页
        self.create_basic_info_tab()
        
        # 代码示例标签页
        self.create_examples_tab()
        
        # 参考资料标签页
        self.create_reference_tab()
        
    def create_basic_info_tab(self):
        """创建基本信息标签页"""
        basic_tab = self.detail_notebook.add("基本信息")
        
        # 规则描述
        desc_frame = ctk.CTkFrame(basic_tab)
        desc_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            desc_frame,
            text="规则描述:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.description_text = ctk.CTkTextbox(desc_frame, height=80)
        self.description_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # 为什么需要这个规则
        why_frame = ctk.CTkFrame(basic_tab)
        why_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(
            why_frame,
            text="为什么需要这个规则:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.why_text = ctk.CTkTextbox(why_frame)
        self.why_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
    def create_examples_tab(self):
        """创建代码示例标签页"""
        examples_tab = self.detail_notebook.add("代码示例")
        
        # 错误示例
        bad_frame = ctk.CTkFrame(examples_tab)
        bad_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            bad_frame,
            text="❌ 错误示例:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.bad_example_text = ctk.CTkTextbox(bad_frame)
        self.bad_example_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 正确示例
        good_frame = ctk.CTkFrame(examples_tab)
        good_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(
            good_frame,
            text="✅ 正确示例:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.good_example_text = ctk.CTkTextbox(good_frame)
        self.good_example_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
    def create_reference_tab(self):
        """创建参考资料标签页"""
        reference_tab = self.detail_notebook.add("参考资料")
        
        # 参考信息
        ref_frame = ctk.CTkFrame(reference_tab)
        ref_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 书籍信息
        book_frame = ctk.CTkFrame(ref_frame)
        book_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(book_frame, text="参考书籍:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.ref_book_label = ctk.CTkLabel(book_frame, text="")
        self.ref_book_label.pack(anchor="w", padx=20, pady=(0, 5))
        
        ctk.CTkLabel(book_frame, text="章节页码:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5, 5))
        self.ref_chapter_label = ctk.CTkLabel(book_frame, text="")
        self.ref_chapter_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        # 引用内容
        quote_frame = ctk.CTkFrame(ref_frame)
        quote_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(
            quote_frame,
            text="相关引用:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.quote_text = ctk.CTkTextbox(quote_frame)
        self.quote_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
    def create_bottom_buttons(self, parent):
        """创建底部按钮"""
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # 左侧 - 配置管理
        left_buttons = ctk.CTkFrame(button_frame)
        left_buttons.pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(
            left_buttons,
            text="导入配置",
            width=100,
            command=self.import_config
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            left_buttons,
            text="导出配置",
            width=100,
            command=self.export_config
        ).pack(side="left", padx=2)
        
        # 右侧 - 确认取消
        right_buttons = ctk.CTkFrame(button_frame)
        right_buttons.pack(side="right", padx=10, pady=10)
        
        ctk.CTkButton(
            right_buttons,
            text="取消",
            width=80,
            command=self.on_cancel
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            right_buttons,
            text="应用",
            width=80,
            command=self.on_apply
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            right_buttons,
            text="确定",
            width=80,
            command=self.on_ok
        ).pack(side="left", padx=2)
        
    def load_rule_data(self):
        """加载规则数据到界面"""
        # 清空树
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
            
        # 添加分类和规则
        for category, rules in self.categories.items():
            # 统计启用的规则数量
            enabled_count = sum(1 for rule in rules if rule.enabled)
            total_count = len(rules)
            
            category_text = f"📁 {category} ({enabled_count}/{total_count})"
            category_item = self.category_tree.insert("", "end", text=category_text, open=True)
            
            # 添加规则
            for rule in rules:
                status_icon = "✅" if rule.enabled else "❌"
                severity_icon = {"严重": "🔴", "警告": "🟡", "建议": "💡"}[rule.severity.value]
                
                rule_text = f"{status_icon} {severity_icon} {rule.rule_id}: {rule.name_cn}"
                rule_item = self.category_tree.insert(category_item, "end", text=rule_text)
                
                # 存储规则引用
                self.category_tree.set(rule_item, "rule_id", rule.rule_id)
                
    def on_rule_select(self, event):
        """规则选择事件"""
        selection = self.category_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        rule_id = self.category_tree.set(item, "rule_id")
        
        if rule_id:  # 是规则项，不是分类项
            rule = self.rule_engine.get_rule_by_id(rule_id)
            if rule:
                self.selected_rule = rule
                self.display_rule_details(rule)
                
    def display_rule_details(self, rule):
        """显示规则详情"""
        # 更新标题
        self.rule_title_label.configure(text=f"{rule.rule_id}: {rule.name_cn}")
        
        # 更新启用状态
        self.rule_enabled_var.set(rule.enabled)
        
        # 更新严重程度
        self.severity_var.set(rule.severity.value)
        
        # 更新基本信息
        self.description_text.delete("0.0", "end")
        self.description_text.insert("0.0", rule.description_cn)
        
        self.why_text.delete("0.0", "end")
        self.why_text.insert("0.0", rule.why_cn)
        
        # 更新代码示例
        bad_examples = "\n\n".join([
            f"// {ex.description}\n{ex.code}" 
            for ex in rule.bad_examples
        ])
        self.bad_example_text.delete("0.0", "end")
        self.bad_example_text.insert("0.0", bad_examples)
        
        good_examples = "\n\n".join([
            f"// {ex.description}\n{ex.code}"
            for ex in rule.good_examples
        ])
        self.good_example_text.delete("0.0", "end")
        self.good_example_text.insert("0.0", good_examples)
        
        # 更新参考资料
        self.ref_book_label.configure(text=rule.reference.book or "无")
        
        chapter_info = ""
        if rule.reference.chapter:
            chapter_info += rule.reference.chapter
        if rule.reference.page:
            chapter_info += f" {rule.reference.page}"
        self.ref_chapter_label.configure(text=chapter_info or "无")
        
        self.quote_text.delete("0.0", "end")
        self.quote_text.insert("0.0", rule.reference.quote or "")
        
    def on_rule_enabled_change(self):
        """规则启用状态改变"""
        if self.selected_rule:
            self.selected_rule.enabled = self.rule_enabled_var.get()
            self.changes_made = True
            self.load_rule_data()  # 刷新显示
            
    def on_severity_change(self, value):
        """严重程度改变"""
        if self.selected_rule:
            from ..rules.base_rule import Severity
            self.selected_rule.severity = Severity(value)
            self.changes_made = True
            self.load_rule_data()  # 刷新显示
            
    def on_search_change(self, *args):
        """搜索内容改变"""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            self.load_rule_data()
            return
            
        # 过滤规则
        filtered_categories = {}
        for category, rules in self.categories.items():
            filtered_rules = [
                rule for rule in rules
                if (search_text in rule.rule_id.lower() or 
                    search_text in rule.name_cn.lower() or
                    search_text in rule.description_cn.lower())
            ]
            if filtered_rules:
                filtered_categories[category] = filtered_rules
                
        # 更新显示
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
            
        for category, rules in filtered_categories.items():
            category_text = f"📁 {category} ({len(rules)}个匹配)"
            category_item = self.category_tree.insert("", "end", text=category_text, open=True)
            
            for rule in rules:
                status_icon = "✅" if rule.enabled else "❌"
                severity_icon = {"严重": "🔴", "警告": "🟡", "建议": "💡"}[rule.severity.value]
                
                rule_text = f"{status_icon} {severity_icon} {rule.rule_id}: {rule.name_cn}"
                rule_item = self.category_tree.insert(category_item, "end", text=rule_text)
                self.category_tree.set(rule_item, "rule_id", rule.rule_id)
                
    def on_template_change(self, template_name):
        """模板改变事件"""
        if template_name == "当前配置":
            return
            
        result = messagebox.askyesno(
            "应用模板",
            f"确定要应用 '{template_name}' 模板吗？\n这会覆盖当前的规则配置。"
        )
        
        if result:
            # 应用模板
            template_mapping = {
                "新手友好版": "beginner",
                "C陷阱与缺陷版": "c_traps",
                "嵌入式专用版": "embedded", 
                "MISRA-C精选版": "misra_c",
                "企业级严格版": "enterprise"
            }
            
            template_key = template_mapping.get(template_name)
            if template_key:
                self.rule_engine.apply_template(template_key)
                self.changes_made = True
                self.load_rule_data()
                
                # 重置模板选择
                self.template_var.set("当前配置")
                
    def enable_all_rules(self):
        """启用所有规则"""
        for rule in self.rule_engine.rules:
            rule.enabled = True
        self.changes_made = True
        self.load_rule_data()
        
    def disable_all_rules(self):
        """禁用所有规则"""
        for rule in self.rule_engine.rules:
            rule.enabled = False
        self.changes_made = True
        self.load_rule_data()
        
    def reset_to_default(self):
        """重置为默认配置"""
        result = messagebox.askyesno(
            "重置配置",
            "确定要重置为默认配置吗？\n这会丢失所有自定义设置。"
        )
        
        if result:
            # 应用新手友好版模板
            self.rule_engine.apply_template("beginner")
            self.changes_made = True
            self.load_rule_data()
            
    def import_config(self):
        """导入配置"""
        file_path = filedialog.askopenfilename(
            title="导入规则配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                self.rule_engine.import_config(Path(file_path))
                self.changes_made = True
                self.load_rule_data()
                messagebox.showinfo("导入成功", "规则配置已成功导入")
            except Exception as e:
                messagebox.showerror("导入失败", f"配置导入失败:\n{str(e)}")
                
    def export_config(self):
        """导出配置"""
        file_path = filedialog.asksaveasfilename(
            title="导出规则配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                self.rule_engine.export_config(Path(file_path))
                messagebox.showinfo("导出成功", f"规则配置已导出到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"配置导出失败:\n{str(e)}")
                
    def on_apply(self):
        """应用更改"""
        if self.changes_made:
            # 这里可以添加配置验证逻辑
            messagebox.showinfo("应用成功", "规则配置已应用")
            self.changes_made = False
            
    def on_ok(self):
        """确定并关闭"""
        self.on_apply()
        self.window.destroy()
        
    def on_cancel(self):
        """取消更改"""
        if self.changes_made:
            result = messagebox.askyesno(
                "未保存的更改",
                "有未保存的更改，确定要取消吗？"
            )
            if not result:
                return
                
        self.window.destroy()
        
    def on_close(self):
        """窗口关闭事件"""
        self.on_cancel()


# 使用示例
if __name__ == "__main__":
    # 测试规则配置窗口
    root = ctk.CTk()
    
    # 模拟规则引擎
    class MockRuleEngine:
        def __init__(self):
            from ..rules.base_rule import BaseRule, Severity
            
            # 创建一些测试规则
            self.rules = []
            
        def get_rule_by_id(self, rule_id):
            for rule in self.rules:
                if rule.rule_id == rule_id:
                    return rule
            return None
            
        def apply_template(self, template_name):
            print(f"应用模板: {template_name}")
            
        def export_config(self, path):
            print(f"导出配置到: {path}")
            
        def import_config(self, path):
            print(f"导入配置从: {path}")
    
    mock_engine = MockRuleEngine()
    config_window = RuleConfigWindow(root, mock_engine)
    config_window.show()
    
    root.mainloop()