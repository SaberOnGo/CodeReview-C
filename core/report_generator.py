#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: core/report_generator.py
报告生成器 - 生成HTML、PDF、TXT格式的检查报告
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
from collections import Counter

# 导入模板引擎
try:
    from jinja2 import Template, Environment, FileSystemLoader
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

# 导入PDF生成库
try:
    import weasyprint
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

class ReportGenerator:
    """报告生成器主类"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / "templates" / "reports"
        self.output_dir = Path(__file__).parent.parent / "output" / "reports"
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化模板环境
        if HAS_JINJA2:
            try:
                self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))
            except:
                self.jinja_env = None
        else:
            self.jinja_env = None
            
    def generate_html_report(self, issues: List, project_info=None, output_path: str = None) -> str:
        """生成HTML格式报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"report_{timestamp}.html"
        else:
            output_path = Path(output_path)
            
        # 生成报告数据
        report_data = self._prepare_report_data(issues, project_info)
        
        if self.jinja_env:
            # 使用Jinja2模板
            try:
                template = self.jinja_env.get_template('html_report.html')
                html_content = template.render(**report_data)
            except:
                # 模板文件不存在，使用内置模板
                html_content = self._generate_html_builtin(report_data)
        else:
            # 使用内置HTML生成
            html_content = self._generate_html_builtin(report_data)
            
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return str(output_path)
    
    def generate_pdf_report(self, issues: List, project_info=None, output_path: str = None) -> str:
        """生成PDF格式报告"""
        if not HAS_WEASYPRINT:
            raise ImportError("需要安装 weasyprint 库来生成PDF报告: pip install weasyprint")
            
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"report_{timestamp}.pdf"
        else:
            output_path = Path(output_path)
            
        # 先生成HTML内容
        report_data = self._prepare_report_data(issues, project_info)
        html_content = self._generate_html_for_pdf(report_data)
        
        # 转换为PDF
        try:
            weasyprint.HTML(string=html_content).write_pdf(str(output_path))
        except Exception as e:
            raise RuntimeError(f"PDF生成失败: {str(e)}")
            
        return str(output_path)
    
    def generate_text_report(self, issues: List, project_info=None, output_path: str = None) -> str:
        """生成纯文本格式报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"report_{timestamp}.txt"
        else:
            output_path = Path(output_path)
            
        # 生成报告数据
        report_data = self._prepare_report_data(issues, project_info)
        
        # 生成文本内容
        text_content = self._generate_text_content(report_data)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
            
        return str(output_path)
    
    def _prepare_report_data(self, issues: List, project_info=None) -> Dict[str, Any]:
        """准备报告数据"""
        # 基本统计
        total_issues = len(issues)
        critical_count = sum(1 for issue in issues if issue.severity.value == "严重")
        warning_count = sum(1 for issue in issues if issue.severity.value == "警告")
        suggestion_count = sum(1 for issue in issues if issue.severity.value == "建议")
        
        # 按文件分组
        files_issues = {}
        for issue in issues:
            file_path = str(issue.file_path)
            if file_path not in files_issues:
                files_issues[file_path] = []
            files_issues[file_path].append(issue)
            
        # 按规则分组
        rules_stats = Counter(issue.rule_id for issue in issues)
        
        # 按严重程度分组
        severity_issues = {
            "严重": [issue for issue in issues if issue.severity.value == "严重"],
            "警告": [issue for issue in issues if issue.severity.value == "警告"],
            "建议": [issue for issue in issues if issue.severity.value == "建议"]
        }
        
        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'project_info': project_info,
            'total_issues': total_issues,
            'critical_count': critical_count,
            'warning_count': warning_count,
            'suggestion_count': suggestion_count,
            'files_count': len(files_issues),
            'issues': issues,
            'files_issues': files_issues,
            'rules_stats': rules_stats,
            'severity_issues': severity_issues,
            'top_rules': rules_stats.most_common(10)
        }
    
    def _generate_html_builtin(self, data: Dict[str, Any]) -> str:
        """生成内置HTML报告"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CTrapsDetector 代码检查报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }}
        .header .subtitle {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 16px;
        }}
        .summary {{
            padding: 30px;
            background: #fff;
        }}
        .summary h2 {{
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        .stat-card.critical {{ border-left-color: #e74c3c; }}
        .stat-card.warning {{ border-left-color: #f39c12; }}
        .stat-card.suggestion {{ border-left-color: #2ecc71; }}
        .stat-number {{
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .issues-section {{
            padding: 0 30px 30px 30px;
        }}
        .issue-item {{
            background: #fff;
            margin: 10px 0;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #ddd;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .issue-item.critical {{
            border-left-color: #e74c3c;
            background-color: #fdf2f2;
        }}
        .issue-item.warning {{
            border-left-color: #f39c12;
            background-color: #fefcf3;
        }}
        .issue-item.suggestion {{
            border-left-color: #2ecc71;
            background-color: #f1fdf6;
        }}
        .issue-header {{
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .issue-title {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .issue-severity {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }}
        .severity-critical {{ background-color: #e74c3c; }}
        .severity-warning {{ background-color: #f39c12; }}
        .severity-suggestion {{ background-color: #2ecc71; }}
        .issue-file {{
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .issue-description {{
            color: #555;
            line-height: 1.6;
        }}
        .code-snippet {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre;
        }}
        .suggestion {{
            background: #e8f5e8;
            border: 1px solid #c3e6c3;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }}
        .suggestion-title {{
            font-weight: bold;
            color: #27ae60;
            margin-bottom: 5px;
        }}
        .footer {{
            padding: 20px 30px;
            background: #ecf0f1;
            color: #7f8c8d;
            text-align: center;
            font-size: 14px;
        }}
        .project-info {{
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 6px;
        }}
        .project-info h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ CTrapsDetector 代码检查报告</h1>
            <div class="subtitle">生成时间: {data['timestamp']}</div>
        </div>
        
        <div class="summary">
            <h2>📊 检查摘要</h2>
            
            {self._generate_project_info_html(data.get('project_info'))}
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{data['total_issues']}</div>
                    <div class="stat-label">总问题数</div>
                </div>
                <div class="stat-card critical">
                    <div class="stat-number">{data['critical_count']}</div>
                    <div class="stat-label">严重问题</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-number">{data['warning_count']}</div>
                    <div class="stat-label">警告问题</div>
                </div>
                <div class="stat-card suggestion">
                    <div class="stat-number">{data['suggestion_count']}</div>
                    <div class="stat-label">建议问题</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{data['files_count']}</div>
                    <div class="stat-label">涉及文件</div>
                </div>
            </div>
        </div>
        
        <div class="issues-section">
            <h2>🔍 问题详情</h2>
            {self._generate_issues_html(data['issues'])}
        </div>
        
        <div class="footer">
            <p>报告由 CTrapsDetector v1.0 生成 | GitHub: https://github.com/SaberOnGo/CTrapsDetector</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_project_info_html(self, project_info) -> str:
        """生成项目信息HTML"""
        if not project_info:
            return ""
            
        return f"""
        <div class="project-info">
            <h3>📁 项目信息</h3>
            <p><strong>项目类型:</strong> {project_info.description}</p>
            <p><strong>C标准:</strong> {project_info.c_standard}</p>
            <p><strong>检测置信度:</strong> {project_info.confidence:.1%}</p>
        </div>
        """
    
    def _generate_issues_html(self, issues: List) -> str:
        """生成问题列表HTML"""
        if not issues:
            return '<p style="text-align: center; color: #27ae60; font-size: 18px;">🎉 恭喜！未发现任何问题。</p>'
            
        html_parts = []
        
        for issue in issues:
            severity_class = issue.severity.value.lower()
            if severity_class == "严重":
                severity_class = "critical"
            elif severity_class == "警告":
                severity_class = "warning"
            elif severity_class == "建议":
                severity_class = "suggestion"
                
            # 处理代码片段
            code_snippet = issue.code_snippet.replace('<', '&lt;').replace('>', '&gt;')
            
            # 处理修复建议
            suggestion_html = ""
            if issue.suggestion:
                suggestion_html = f"""
                <div class="suggestion">
                    <div class="suggestion-title">💡 修复建议:</div>
                    <div>{issue.suggestion}</div>
                </div>
                """
            
            issue_html = f"""
            <div class="issue-item {severity_class}">
                <div class="issue-header">
                    <div class="issue-title">{issue.rule_id}: {issue.rule_name}</div>
                    <span class="issue-severity severity-{severity_class}">{issue.severity.value}</span>
                </div>
                <div class="issue-file">📄 {issue.file_path} (第{issue.line_number}行)</div>
                <div class="issue-description">{issue.message}</div>
                <div class="code-snippet">{code_snippet}</div>
                {suggestion_html}
            </div>
            """
            html_parts.append(issue_html)
            
        return '\n'.join(html_parts)
    
    def _generate_html_for_pdf(self, data: Dict[str, Any]) -> str:
        """生成适用于PDF的HTML"""
        # PDF版本的HTML需要更简洁的样式
        return self._generate_html_builtin(data).replace(
            'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',
            'background: #667eea;'
        )
    
    def _generate_text_content(self, data: Dict[str, Any]) -> str:
        """生成纯文本报告内容"""
        lines = []
        
        # 标题
        lines.append("=" * 60)
        lines.append("CTrapsDetector 代码检查报告")
        lines.append("=" * 60)
        lines.append(f"生成时间: {data['timestamp']}")
        lines.append("")
        
        # 项目信息
        if data.get('project_info'):
            project_info = data['project_info']
            lines.append("项目信息:")
            lines.append("-" * 20)
            lines.append(f"项目类型: {project_info.description}")
            lines.append(f"C标准: {project_info.c_standard}")
            lines.append(f"检测置信度: {project_info.confidence:.1%}")
            lines.append("")
        
        # 统计摘要
        lines.append("检查摘要:")
        lines.append("-" * 20)
        lines.append(f"总问题数: {data['total_issues']}")
        lines.append(f"严重问题: {data['critical_count']}")
        lines.append(f"警告问题: {data['warning_count']}")
        lines.append(f"建议问题: {data['suggestion_count']}")
        lines.append(f"涉及文件: {data['files_count']}")
        lines.append("")
        
        # 问题详情
        if data['issues']:
            lines.append("问题详情:")
            lines.append("-" * 20)
            
            for i, issue in enumerate(data['issues'], 1):
                lines.append(f"{i}. [{issue.severity.value}] {issue.rule_id}: {issue.rule_name}")
                lines.append(f"   文件: {issue.file_path}")
                lines.append(f"   位置: 第{issue.line_number}行, 第{issue.column}列")
                lines.append(f"   问题: {issue.message}")
                
                if issue.suggestion:
                    lines.append(f"   建议: {issue.suggestion}")
                    
                if issue.reference:
                    lines.append(f"   参考: {issue.reference}")
                    
                lines.append("")
        else:
            lines.append("🎉 恭喜！未发现任何问题。")
            lines.append("")
        
        # 规则统计
        if data['top_rules']:
            lines.append("规则统计 (前10名):")
            lines.append("-" * 20)
            for rule_id, count in data['top_rules']:
                lines.append(f"{rule_id}: {count}个问题")
            lines.append("")
        
        # 页脚
        lines.append("=" * 60)
        lines.append("报告由 CTrapsDetector v1.0 生成")
        lines.append("GitHub: https://github.com/SaberOnGo/CTrapsDetector")
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def generate_summary_only(self, issues: List, project_info=None) -> Dict[str, Any]:
        """只生成摘要数据，不生成文件"""
        return self._prepare_report_data(issues, project_info)


# 使用示例
if __name__ == "__main__":
    from ..rules.base_rule import Issue, Severity
    from pathlib import Path
    
    # 创建测试数据
    test_issues = [
        Issue(
            rule_id="C001",
            rule_name="数组越界检查",
            file_path=Path("test.c"),
            line_number=15,
            column=10,
            severity=Severity.CRITICAL,
            message="数组访问可能越界",
            description="检测到数组下标可能超出范围",
            code_snippet="int arr[10];\narr[10] = 5;  // 问题行\nreturn 0;",
            suggestion="将索引改为0-9之间的值",
            reference="《C陷阱与缺陷》第2章"
        )
    ]
    
    # 生成报告
    generator = ReportGenerator()
    
    try:
        html_path = generator.generate_html_report(test_issues)
        print(f"HTML报告已生成: {html_path}")
        
        text_path = generator.generate_text_report(test_issues)
        print(f"文本报告已生成: {text_path}")
        
        if HAS_WEASYPRINT:
            pdf_path = generator.generate_pdf_report(test_issues)
            print(f"PDF报告已生成: {pdf_path}")
        else:
            print("PDF生成需要安装 weasyprint 库")
            
    except Exception as e:
        print(f"报告生成失败: {e}")