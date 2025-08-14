#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# main_window.py
"""
主界面 - CodeReview-C 主窗口
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
import threading
from typing import List, Optional

# 设置外观
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title("CodeReview-C v1.0 - C语言代码评审工具")
        self.root.geometry("1200x800")
        
        # 初始化组件
        self.project_path = tk.StringVar()
        self.project_info = None
        self.parsed_files = []
        self.issues = []
        
        # 导入核心模块（延迟导入避免循环依赖）
        from ..core.parser import CodeParser
        from ..core.rule_engine import RuleEngine
        from ..core.project_detector import ProjectDetector
        
        self.parser = CodeParser()
        self.rule_engine = RuleEngine()
        self.project_detector = ProjectDetector()
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建主布局
        self.create_header()
        self.create_project_section()
        self.create_rules_section()
        self.create_results_section()
        self.create_status_bar()
        
    def create_header(self):
        """创建头部区域"""
        header_frame = ctk.CTkFrame(self.root)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # 标题
        title_label = ctk.CTkLabel(
            header_frame,
            text="CodeReview-C",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # 副标题
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="专业的C语言代码静态分析工具",
            font=ctk.CTkFont(size=14)
        )
        subtitle_label.pack(side="left", padx=(0, 20), pady=15)
        
        # 右侧按钮
        help_button = ctk.CTkButton(
            header_frame,
            text="帮助",
            width=80,
            command=self.show_help
        )
        help_button.pack(side="right", padx=20, pady=15)
        
    def create_project_section(self):
        """创建项目选择区域"""
        project_frame = ctk.CTkFrame(self.root)
        project_frame.pack(fill="x", padx=20, pady=5)
        
        # 标题
        ctk.CTkLabel(
            project_frame,
            text="📁 项目设置",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        # 项目路径选择
        path_frame = ctk.CTkFrame(project_frame)
        path_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(path_frame, text="项目路径:").pack(side="left", padx=10, pady=10)
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.project_path,
            placeholder_text="选择包含C代码的项目目录...",
            width=400
        )
        self.path_entry.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        browse_button = ctk.CTkButton(
            path_frame,
            text="浏览",
            width=80,
            command=self.browse_project
        )
        browse_button.pack(side="right", padx=10, pady=10)
        
        scan_button = ctk.CTkButton(
            path_frame,
            text="扫描项目",
            width=100,
            command=self.scan_project
        )
        scan_button.pack(side="right", padx=(0, 10), pady=10)
        
        # 项目信息显示
        self.project_info_label = ctk.CTkLabel(
            project_frame,
            text="请选择项目目录并点击扫描",
            font=ctk.CTkFont(size=12)
        )
        self.project_info_label.pack(anchor="w", padx=20, pady=(0, 15))
        
    def create_rules_section(self):
        """创建规则配置区域"""
        rules_frame = ctk.CTkFrame(self.root)
        rules_frame.pack(fill="x", padx=20, pady=5)
        
        # 标题和控制按钮
        rules_header = ctk.CTkFrame(rules_frame)
        rules_header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            rules_header,
            text="🛡️ 规则配置",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        
        config_button = ctk.CTkButton(
            rules_header,
            text="配置规则",
            width=100,
            command=self.show_rule_config
        )
        config_button.pack(side="right", padx=5)
        
        # 模板选择
        template_frame = ctk.CTkFrame(rules_frame)
        template_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(template_frame, text="规则模板:").pack(side="left", padx=10, pady=10)
        
        self.template_var = tk.StringVar(value="新手友好版")
        template_menu = ctk.CTkOptionMenu(
            template_frame,
            variable=self.template_var,
            values=["新手友好版", "C陷阱与缺陷版", "嵌入式专用版", "MISRA-C精选版", "企业级严格版"],
            command=self.on_template_change
        )
        template_menu.pack(side="left", padx=10, pady=10)
        
        # 规则统计
        self.rules_stats_label = ctk.CTkLabel(
            template_frame,
            text="已启用规则: 25/120  严重:8 警告:12 建议:5",
            font=ctk.CTkFont(size=12)
        )
        self.rules_stats_label.pack(side="left", padx=20, pady=10)
        
    def create_results_section(self):
        """创建结果显示区域"""
        results_frame = ctk.CTkFrame(self.root)
        results_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # 标题和操作按钮
        results_header = ctk.CTkFrame(results_frame)
        results_header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            results_header,
            text="📊 检查结果",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        
        # 右侧按钮组
        button_frame = ctk.CTkFrame(results_header)
        button_frame.pack(side="right")
        
        self.check_button = ctk.CTkButton(
            button_frame,
            text="开始检查",
            width=100,
            command=self.start_check,
            state="disabled"
        )
        self.check_button.pack(side="left", padx=5)
        
        export_button = ctk.CTkButton(
            button_frame,
            text="导出报告",
            width=100,
            command=self.export_report
        )
        export_button.pack(side="left", padx=5)
        
        # 结果统计
        self.results_stats_frame = ctk.CTkFrame(results_frame)
        self.results_stats_frame.pack(fill="x", padx=20, pady=5)
        
        self.stats_label = ctk.CTkLabel(
            self.results_stats_frame,
            text="暂无检查结果",
            font=ctk.CTkFont(size=14)
        )
        self.stats_label.pack(pady=10)
        
        # 结果列表
        self.create_results_tree(results_frame)
        
    def create_results_tree(self, parent):
        """创建结果树形视图"""
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 使用tkinter的Treeview（customtkinter暂不支持）
        style = ttk.Style()
        style.theme_use("clam")
        
        columns = ("severity", "file", "line", "rule", "message")
        self.results_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # 设置列标题
        self.results_tree.heading("severity", text="严重程度")
        self.results_tree.heading("file", text="文件")
        self.results_tree.heading("line", text="行号")
        self.results_tree.heading("rule", text="规则")
        self.results_tree.heading("message", text="问题描述")
        
        # 设置列宽
        self.results_tree.column("severity", width=80)
        self.results_tree.column("file", width=200)
        self.results_tree.column("line", width=60)
        self.results_tree.column("rule", width=100)
        self.results_tree.column("message", width=400)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        # 绑定双击事件
        self.results_tree.bind("<Double-1>", self.on_result_double_click)
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_frame = ctk.CTkFrame(self.root)
        self.status_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="就绪",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=20, pady=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(
            self.status_frame,
            variable=self.progress_var,
            width=200
        )
        self.progress_bar.pack(side="right", padx=20, pady=10)
        self.progress_bar.set(0)
        
    def browse_project(self):
        """浏览选择项目目录"""
        directory = filedialog.askdirectory(
            title="选择C语言项目目录",
            initialdir=Path.home()
        )
        if directory:
            self.project_path.set(directory)
            
    def scan_project(self):
        """扫描项目"""
        if not self.project_path.get():
            messagebox.showerror("错误", "请先选择项目目录")
            return
            
        project_dir = Path(self.project_path.get())
        if not project_dir.exists():
            messagebox.showerror("错误", "项目目录不存在")
            return
            
        # 在后台线程中执行扫描
        self.status_label.configure(text="正在扫描项目...")
        self.progress_bar.set(0.2)
        
        def scan_thread():
            try:
                # 检测项目类型
                self.project_info = self.project_detector.detect_project_type(project_dir)
                
                # 解析文件
                self.parsed_files = self.parser.parse_project(project_dir)
                
                # 更新UI
                self.root.after(0, self.on_scan_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self.on_scan_error(str(e)))
                
        threading.Thread(target=scan_thread, daemon=True).start()
        
    def on_scan_complete(self):
        """扫描完成回调"""
        self.progress_bar.set(1.0)
        
        if self.project_info:
            info_text = (f"检测到: {self.project_info.description} "
                        f"(C{self.project_info.c_standard}标准, "
                        f"置信度: {self.project_info.confidence:.1%})")
            self.project_info_label.configure(text=info_text)
            
            # 应用推荐的规则模板
            recommended_template = self.get_recommended_template()
            if recommended_template:
                self.template_var.set(recommended_template)
                self.on_template_change(recommended_template)
        
        self.status_label.configure(text=f"扫描完成 - 找到 {len(self.parsed_files)} 个C文件")
        self.check_button.configure(state="normal")
        
    def on_scan_error(self, error_msg: str):
        """扫描错误回调"""
        self.progress_bar.set(0)
        self.status_label.configure(text="扫描失败")
        messagebox.showerror("扫描错误", f"项目扫描失败:\n{error_msg}")
        
    def get_recommended_template(self) -> Optional[str]:
        """根据项目类型获取推荐模板"""
        if not self.project_info:
            return None
            
        template_mapping = {
            "ESP32": "嵌入式专用版",
            "STM32_HAL": "嵌入式专用版",
            "STM32_LL": "嵌入式专用版",
            "Arduino": "新手友好版",
            "Linux_GNU": "C陷阱与缺陷版",
            "Generic_C": "新手友好版"
        }
        
        return template_mapping.get(self.project_info.project_type, "新手友好版")
        
    def on_template_change(self, template_name: str):
        """模板改变回调"""
        # 应用规则模板
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
            self.update_rules_stats()
            
    def update_rules_stats(self):
        """更新规则统计"""
        enabled_rules = self.rule_engine.get_enabled_rules()
        total_rules = len(self.rule_engine.rules)
        
        # 按严重程度统计
        critical_count = sum(1 for r in enabled_rules if r.severity.value == "严重")
        warning_count = sum(1 for r in enabled_rules if r.severity.value == "警告")
        suggestion_count = sum(1 for r in enabled_rules if r.severity.value == "建议")
        
        stats_text = (f"已启用规则: {len(enabled_rules)}/{total_rules}  "
                     f"严重:{critical_count} 警告:{warning_count} 建议:{suggestion_count}")
        
        self.rules_stats_label.configure(text=stats_text)
        
    def start_check(self):
        """开始代码检查"""
        if not self.parsed_files:
            messagebox.showerror("错误", "请先扫描项目")
            return
            
        enabled_rules = self.rule_engine.get_enabled_rules()
        if not enabled_rules:
            messagebox.showerror("错误", "请至少启用一个检查规则")
            return
            
        # 在后台线程中执行检查
        self.status_label.configure(text="正在检查代码...")
        self.progress_bar.set(0)
        self.check_button.configure(state="disabled")
        
        def check_thread():
            try:
                # 执行代码检查
                self.issues = self.rule_engine.check_files(self.parsed_files, self.parser)
                
                # 更新UI
                self.root.after(0, self.on_check_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self.on_check_error(str(e)))
                
        threading.Thread(target=check_thread, daemon=True).start()
        
    def on_check_complete(self):
        """检查完成回调"""
        self.progress_bar.set(1.0)
        self.check_button.configure(state="normal")
        
        # 更新结果统计
        self.update_results_stats()
        
        # 更新结果列表
        self.update_results_tree()
        
        self.status_label.configure(text=f"检查完成 - 发现 {len(self.issues)} 个问题")
        
        # 如果有问题，显示提示
        if self.issues:
            messagebox.showinfo("检查完成", f"代码检查完成！\n发现 {len(self.issues)} 个问题，请查看详细结果。")
        else:
            messagebox.showinfo("检查完成", "恭喜！未发现任何问题。")
            
    def on_check_error(self, error_msg: str):
        """检查错误回调"""
        self.progress_bar.set(0)
        self.check_button.configure(state="normal")
        self.status_label.configure(text="检查失败")
        messagebox.showerror("检查错误", f"代码检查失败:\n{error_msg}")
        
    def update_results_stats(self):
        """更新结果统计"""
        if not self.issues:
            self.stats_label.configure(text="✅ 未发现任何问题")
            return
            
        # 按严重程度统计
        critical_count = sum(1 for issue in self.issues if issue.severity.value == "严重")
        warning_count = sum(1 for issue in self.issues if issue.severity.value == "警告")
        suggestion_count = sum(1 for issue in self.issues if issue.severity.value == "建议")
        
        stats_text = (f"📊 总计: {len(self.issues)}个问题  "
                     f"🔴 严重: {critical_count}个  "
                     f"🟡 警告: {warning_count}个  "
                     f"💡 建议: {suggestion_count}个")
        
        self.stats_label.configure(text=stats_text)
        
    def update_results_tree(self):
        """更新结果树"""
        # 清空现有项目
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        if not self.issues:
            return
            
        # 添加问题项目
        for issue in self.issues:
            # 获取相对路径
            try:
                rel_path = issue.file_path.relative_to(Path(self.project_path.get()))
            except ValueError:
                rel_path = issue.file_path
                
            # 严重程度图标
            severity_icon = {
                "严重": "🔴",
                "警告": "🟡", 
                "建议": "💡"
            }.get(issue.severity.value, "❓")
            
            self.results_tree.insert("", "end", values=(
                f"{severity_icon} {issue.severity.value}",
                str(rel_path),
                issue.line_number,
                issue.rule_id,
                issue.message
            ))
            
    def on_result_double_click(self, event):
        """结果双击事件"""
        selection = self.results_tree.selection()
        if not selection:
            return
            
        item = self.results_tree.item(selection[0])
        values = item['values']
        
        if len(values) >= 4:
            file_path = values[1]
            line_number = values[2]
            rule_id = values[3]
            
            # 查找对应的问题
            target_issue = None
            for issue in self.issues:
                try:
                    rel_path = issue.file_path.relative_to(Path(self.project_path.get()))
                except ValueError:
                    rel_path = issue.file_path
                    
                if str(rel_path) == file_path and issue.line_number == line_number:
                    target_issue = issue
                    break
                    
            if target_issue:
                self.show_issue_detail(target_issue)
                
    def show_issue_detail(self, issue):
        """显示问题详情"""
        detail_window = ctk.CTkToplevel(self.root)
        detail_window.title(f"问题详情 - {issue.rule_id}")
        detail_window.geometry("800x600")
        
        # 基本信息
        info_frame = ctk.CTkFrame(detail_window)
        info_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            info_frame,
            text=f"规则: {issue.rule_name} ({issue.rule_id})",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            info_frame,
            text=f"文件: {issue.file_path}",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=2)
        
        ctk.CTkLabel(
            info_frame,
            text=f"位置: 第{issue.line_number}行, 第{issue.column}列",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=2)
        
        ctk.CTkLabel(
            info_frame,
            text=f"严重程度: {issue.severity.value}",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(2, 15))
        
        # 问题描述
        desc_frame = ctk.CTkFrame(detail_window)
        desc_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            desc_frame,
            text="问题描述:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        desc_text = ctk.CTkTextbox(desc_frame, height=80)
        desc_text.pack(fill="x", padx=20, pady=(0, 15))
        desc_text.insert("0.0", issue.description)
        desc_text.configure(state="disabled")
        
        # 代码片段
        code_frame = ctk.CTkFrame(detail_window)
        code_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            code_frame,
            text="问题代码:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        code_text = ctk.CTkTextbox(code_frame, height=150)
        code_text.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        code_text.insert("0.0", issue.code_snippet)
        code_text.configure(state="disabled")
        
        # 修复建议
        if issue.suggestion:
            suggestion_frame = ctk.CTkFrame(detail_window)
            suggestion_frame.pack(fill="x", padx=20, pady=(0, 20))
            
            ctk.CTkLabel(
                suggestion_frame,
                text="修复建议:",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w", padx=20, pady=(15, 5))
            
            suggestion_text = ctk.CTkTextbox(suggestion_frame, height=60)
            suggestion_text.pack(fill="x", padx=20, pady=(0, 15))
            suggestion_text.insert("0.0", issue.suggestion)
            suggestion_text.configure(state="disabled")
            
    def show_rule_config(self):
        """显示规则配置窗口"""
        from .rule_config import RuleConfigWindow
        config_window = RuleConfigWindow(self.root, self.rule_engine)
        config_window.show()
        
    def export_report(self):
        """导出检查报告"""
        if not self.issues:
            messagebox.showwarning("警告", "没有检查结果可以导出")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="保存检查报告",
            defaultextension=".html",
            filetypes=[
                ("HTML文件", "*.html"),
                ("PDF文件", "*.pdf"),
                ("文本文件", "*.txt")
            ]
        )
        
        if file_path:
            try:
                from ..core.report_generator import ReportGenerator
                generator = ReportGenerator()
                
                if file_path.endswith('.html'):
                    generator.generate_html_report(self.issues, self.project_info, file_path)
                elif file_path.endswith('.pdf'):
                    generator.generate_pdf_report(self.issues, self.project_info, file_path)
                else:
                    generator.generate_text_report(self.issues, self.project_info, file_path)
                    
                messagebox.showinfo("导出成功", f"报告已保存到:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("导出失败", f"报告导出失败:\n{str(e)}")
                
    def show_help(self):
        """显示帮助信息"""
        help_window = ctk.CTkToplevel(self.root)
        help_window.title("帮助 - CodeReview-C")
        help_window.geometry("600x500")
        
        help_text = """
CodeReview-C 使用说明

🚀 快速开始:
1. 点击"浏览"选择包含C代码的项目目录
2. 点击"扫描项目"自动检测项目类型和C标准
3. 选择合适的规则模板或自定义规则配置
4. 点击"开始检查"执行代码分析
5. 查看检查结果，双击可查看详细信息

📋 规则模板说明:
• 基本规则版: 包含最基础的50个规则，适合基本C语言规则
• C陷阱与缺陷版: 基于经典书籍的实用规则集
• 嵌入式专用版: 针对ESP32/STM32等嵌入式平台优化
• MISRA-C精选版: 工业级代码标准规则
• 企业级严格版: 包含所有规则的完整检查

🔧 支持的项目类型:
• ESP32 IoT项目 (自动检测)
• STM32 HAL/LL项目 (自动检测)
• Arduino项目 (自动检测)
• Linux GNU C项目
• 通用C项目

💡 使用技巧:
• 工具会自动检测项目类型并推荐合适的规则模板
• 双击结果列表可查看问题详情和修复建议
• 支持导出HTML、PDF、TXT格式的检查报告
• 可以保存和导入自定义的规则配置

📖 参考资料:
本工具基于《C陷阱与缺陷》、MISRA-C标准等经典资料设计规则，
每个规则都提供了详细的说明和实例。

GitHub: https://github.com/SaberOnGo/CodeReview-C
"""
        
        help_textbox = ctk.CTkTextbox(help_window)
        help_textbox.pack(fill="both", expand=True, padx=20, pady=20)
        help_textbox.insert("0.0", help_text)
        help_textbox.configure(state="disabled")
        
    def run(self):
        """运行主程序"""
        self.root.mainloop()


# 使用示例
if __name__ == "__main__":
    app = MainWindow()
    app.run()