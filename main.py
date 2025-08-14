#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件: main.py
CTrapsDetector - C语言静态代码分析工具
主程序入口

作者: SaberOnGo
版本: v1.0
GitHub: https://github.com/SaberOnGo/CTrapsDetector

这是一个专为中国开发者设计的C语言静态代码分析工具，
基于《C陷阱与缺陷》等经典书籍，提供智能的代码质量检查。
"""

import sys
import os
from pathlib import Path
import argparse
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 版本信息
VERSION = "1.0.0"
BUILD_DATE = "2024-12"
AUTHOR = "SaberOnGo"
GITHUB_URL = "https://github.com/SaberOnGo/CTrapsDetector"

def print_banner():
    """打印程序横幅"""
    banner = f"""
{'='*60}
🛡️  CTrapsDetector v{VERSION} - C语言代码静态分析工具
{'='*60}
专为中国开发者设计的现代化C语言代码检查工具
基于《C陷阱与缺陷》等经典书籍，提供智能的代码质量检查

作者: {AUTHOR}
构建: {BUILD_DATE}  
GitHub: {GITHUB_URL}
{'='*60}
"""
    print(banner)

def check_dependencies():
    """检查依赖包"""
    print("🔍 检查依赖包...")
    
    required_packages = [
        ('tree_sitter', 'tree-sitter'),
        ('tree_sitter_c', 'tree-sitter-c'), 
        ('customtkinter', 'customtkinter'),
        ('chardet', 'chardet'),
    ]
    
    optional_packages = [
        ('jinja2', 'jinja2'),
        ('weasyprint', 'weasyprint'),
    ]
    
    missing_required = []
    missing_optional = []
    
    # 检查必需包
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            missing_required.append(package_name)
            print(f"  ❌ {package_name} (必需)")
    
    # 检查可选包
    for module_name, package_name in optional_packages:
        try:
            __import__(module_name)
            print(f"  ✅ {package_name} (可选)")
        except ImportError:
            missing_optional.append(package_name)
            print(f"  ⚠️  {package_name} (可选，用于报告生成)")
    
    if missing_required:
        print(f"\n❌ 缺少必需依赖包: {', '.join(missing_required)}")
        print("📥 请运行以下命令安装:")
        print(f"   pip install {' '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"\n💡 可选功能需要安装: {', '.join(missing_optional)}")
        print("   这些包用于高级报告生成功能")
    
    print("✅ 依赖检查完成\n")
    return True

def setup_logging():
    """设置日志"""
    import logging
    from datetime import datetime
    
    # 创建日志目录
    log_dir = project_root / "output" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志
    log_file = log_dir / f"ctraps_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='CTrapsDetector - C语言静态代码分析工具',
        epilog=f'更多信息请访问: {GITHUB_URL}'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'CTrapsDetector {VERSION}'
    )
    
    parser.add_argument(
        '--gui', '-g',
        action='store_true',
        help='启动图形界面（默认）'
    )
    
    parser.add_argument(
        '--cli', '-c',
        action='store_true', 
        help='使用命令行模式'
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='输入目录路径（CLI模式）'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='输出报告路径（CLI模式）'
    )
    
    parser.add_argument(
        '--template', '-t',
        type=str,
        default='beginner',
        choices=['beginner', 'c_traps', 'embedded', 'misra_c', 'enterprise'],
        help='规则模板选择'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        default='html',
        choices=['html', 'pdf', 'txt', 'json'],
        help='报告格式'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='自定义配置文件路径'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，不生成报告'
    )
    
    return parser.parse_args()

def run_gui_mode():
    """运行图形界面模式"""
    try:
        print("🎨 启动图形界面...")
        from ui.main_window import MainWindow
        
        app = MainWindow()
        app.run()
        
    except ImportError as e:
        print(f"❌ GUI模块导入失败: {e}")
        print("请确保所有依赖包已正确安装")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ GUI启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run_cli_mode(args, logger):
    """运行命令行模式"""
    try:
        print("⚙️ 启动命令行模式...")
        
        # 检查必需参数
        if not args.input:
            print("❌ 命令行模式需要指定输入目录: --input <directory>")
            sys.exit(1)
        
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ 输入目录不存在: {input_path}")
            sys.exit(1)
        
        # 导入核心模块
        from core.parser import CodeParser
        from core.rule_engine import RuleEngine
        from core.project_detector import ProjectDetector
        from core.report_generator import ReportGenerator
        
        logger.info(f"开始分析项目: {input_path}")
        
        # 初始化组件
        parser = CodeParser()
        rule_engine = RuleEngine()
        detector = ProjectDetector()
        report_generator = ReportGenerator()
        
        # 加载配置
        if args.config:
            config_path = Path(args.config)
            if config_path.exists():
                rule_engine.import_config(config_path)
                logger.info(f"已加载配置文件: {config_path}")
            else:
                print(f"⚠️ 配置文件不存在: {config_path}")
        
        # 应用模板
        rule_engine.apply_template(args.template)
        logger.info(f"已应用规则模板: {args.template}")
        
        # 检测项目类型
        project_info = detector.detect_project_type(input_path)
        print(f"📋 项目类型: {project_info.description}")
        print(f"📋 C标准: {project_info.c_standard}")
        print(f"📋 置信度: {project_info.confidence:.1%}")
        
        # 解析文件
        print("🔍 解析项目文件...")
        parsed_files = parser.parse_project(input_path)
        print(f"📄 发现 {len(parsed_files)} 个C文件")
        
        if not parsed_files:
            print("⚠️ 未找到C文件")
            return
        
        # 执行检查
        print("🔎 执行代码检查...")
        issues = rule_engine.check_files(parsed_files, parser)
        
        # 显示结果摘要
        print_cli_summary(issues, project_info)
        
        # 生成报告
        if not args.dry_run:
            output_path = args.output or f"report_{project_info.project_type}.{args.format}"
            
            print(f"📝 生成{args.format.upper()}报告...")
            
            if args.format == 'html':
                report_path = report_generator.generate_html_report(issues, project_info, output_path)
            elif args.format == 'pdf':
                report_path = report_generator.generate_pdf_report(issues, project_info, output_path)
            elif args.format == 'txt':
                report_path = report_generator.generate_text_report(issues, project_info, output_path)
            elif args.format == 'json':
                report_path = generate_json_report(issues, project_info, output_path)
            
            print(f"✅ 报告已生成: {report_path}")
            logger.info(f"报告生成完成: {report_path}")
        
        logger.info("分析完成")
        
    except Exception as e:
        print(f"❌ 命令行模式执行失败: {e}")
        logger.error(f"CLI模式错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def print_cli_summary(issues, project_info):
    """打印CLI模式结果摘要"""
    print("\n" + "="*50)
    print("📊 检查结果摘要")
    print("="*50)
    
    if not issues:
        print("🎉 恭喜！未发现任何问题。")
        return
    
    # 按严重程度统计
    critical_count = sum(1 for issue in issues if issue.severity.value == "严重")
    warning_count = sum(1 for issue in issues if issue.severity.value == "警告")
    suggestion_count = sum(1 for issue in issues if issue.severity.value == "建议")
    
    print(f"总问题数: {len(issues)}")
    print(f"🔴 严重: {critical_count}")
    print(f"🟡 警告: {warning_count}")
    print(f"💡 建议: {suggestion_count}")
    
    # 按文件统计
    files_with_issues = {}
    for issue in issues:
        file_path = str(issue.file_path)
        if file_path not in files_with_issues:
            files_with_issues[file_path] = []
        files_with_issues[file_path].append(issue)
    
    print(f"\n涉及文件: {len(files_with_issues)}")
    
    # 显示最严重的问题
    critical_issues = [issue for issue in issues if issue.severity.value == "严重"]
    if critical_issues:
        print(f"\n🔴 严重问题预览 (前5个):")
        for i, issue in enumerate(critical_issues[:5]):
            rel_path = Path(issue.file_path).name
            print(f"  {i+1}. {rel_path}:{issue.line_number} - {issue.message}")
    
    # 按规则统计
    from collections import Counter
    rule_stats = Counter(issue.rule_id for issue in issues)
    print(f"\n📋 最常见问题 (前5个):")
    for rule_id, count in rule_stats.most_common(5):
        print(f"  {rule_id}: {count}个问题")

def generate_json_report(issues, project_info, output_path):
    """生成JSON格式报告"""
    from datetime import datetime
    
    # 准备JSON数据
    report_data = {
        'metadata': {
            'tool': 'CTrapsDetector',
            'version': VERSION,
            'generated_at': datetime.now().isoformat(),
            'project_info': {
                'type': project_info.project_type if project_info else 'unknown',
                'c_standard': project_info.c_standard if project_info else 'unknown',
                'confidence': project_info.confidence if project_info else 0.0
            }
        },
        'summary': {
            'total_issues': len(issues),
            'critical_count': sum(1 for issue in issues if issue.severity.value == "严重"),
            'warning_count': sum(1 for issue in issues if issue.severity.value == "警告"),
            'suggestion_count': sum(1 for issue in issues if issue.severity.value == "建议")
        },
        'issues': []
    }
    
    # 转换问题数据
    for issue in issues:
        issue_data = {
            'rule_id': issue.rule_id,
            'rule_name': issue.rule_name,
            'file_path': str(issue.file_path),
            'line_number': issue.line_number,
            'column': issue.column,
            'severity': issue.severity.value,
            'message': issue.message,
            'description': issue.description,
            'suggestion': issue.suggestion,
            'reference': issue.reference
        }
        report_data['issues'].append(issue_data)
    
    # 写入文件
    output_path = Path(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    return str(output_path)

def run_interactive_setup():
    """运行交互式设置"""
    print("🔧 欢迎使用CTrapsDetector交互式设置")
    print("请按照提示配置您的检查选项\n")
    
    # 选择输入目录
    while True:
        input_dir = input("📁 请输入要检查的项目目录路径: ").strip()
        if not input_dir:
            print("❌ 路径不能为空")
            continue
        
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"❌ 目录不存在: {input_path}")
            continue
        
        break
    
    # 选择规则模板
    templates = {
        '1': 'beginner',
        '2': 'c_traps', 
        '3': 'embedded',
        '4': 'misra_c',
        '5': 'enterprise'
    }
    
    print("\n📋 请选择规则模板:")
    print("1. 新手友好版 (推荐初学者)")
    print("2. C陷阱与缺陷版 (基于经典书籍)")
    print("3. 嵌入式专用版 (ESP32/STM32优化)")
    print("4. MISRA-C精选版 (工业标准)")
    print("5. 企业级严格版 (完整检查)")
    
    while True:
        choice = input("请选择 (1-5): ").strip()
        if choice in templates:
            template = templates[choice]
            break
        print("❌ 无效选择，请输入1-5")
    
    # 选择报告格式
    formats = {
        '1': 'html',
        '2': 'pdf',
        '3': 'txt',
        '4': 'json'
    }
    
    print("\n📄 请选择报告格式:")
    print("1. HTML (推荐，可在浏览器中查看)")
    print("2. PDF (便于打印和分享)")
    print("3. 文本 (轻量级)")
    print("4. JSON (用于工具集成)")
    
    while True:
        choice = input("请选择 (1-4): ").strip()
        if choice in formats:
            report_format = formats[choice]
            break
        print("❌ 无效选择，请输入1-4")
    
    # 构建参数
    class InteractiveArgs:
        def __init__(self):
            self.cli = True
            self.input = str(input_path)
            self.output = None
            self.template = template
            self.format = report_format
            self.config = None
            self.verbose = False
            self.dry_run = False
    
    return InteractiveArgs()

def show_help():
    """显示帮助信息"""
    help_text = f"""
CTrapsDetector v{VERSION} - C语言静态代码分析工具

🚀 快速开始:
  python main.py                    # 启动图形界面
  python main.py --cli -i ./project # 命令行模式

📋 命令行选项:
  --gui, -g          启动图形界面（默认）
  --cli, -c          使用命令行模式
  --input, -i DIR    输入项目目录
  --output, -o FILE  输出报告文件
  --template, -t T   规则模板 (beginner/c_traps/embedded/misra_c/enterprise)
  --format, -f F     报告格式 (html/pdf/txt/json)
  --config FILE      自定义配置文件
  --verbose          详细输出模式
  --dry-run          预览模式，不生成报告

🎯 使用示例:
  # GUI模式（推荐新手）
  python main.py

  # 检查ESP32项目，生成HTML报告
  python main.py --cli -i ./esp32_project -t embedded -f html

  # 使用C陷阱规则，生成PDF报告
  python main.py --cli -i ./src -t c_traps -f pdf -o report.pdf

  # 预览检查结果，不生成报告
  python main.py --cli -i ./code --dry-run --verbose

📚 规则模板说明:
  beginner   - 新手友好版 (基础规则，适合学习)
  c_traps    - C陷阱与缺陷版 (基于经典书籍)
  embedded   - 嵌入式专用版 (ESP32/STM32优化)
  misra_c    - MISRA-C精选版 (工业级标准)
  enterprise - 企业级严格版 (完整规则集)

💡 更多信息:
  GitHub: {GITHUB_URL}
  文档: README.md
  问题反馈: {GITHUB_URL}/issues
"""
    print(help_text)

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 特殊命令处理
    if len(sys.argv) == 1:
        # 无参数，显示横幅并启动GUI
        print_banner()
        if not check_dependencies():
            sys.exit(1)
        run_gui_mode()
        return
    
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return
    
    # 显示横幅
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 设置日志
    logger = setup_logging()
    logger.info(f"CTrapsDetector v{VERSION} 启动")
    
    try:
        # 选择运行模式
        if args.cli:
            # 命令行模式
            run_cli_mode(args, logger)
        elif args.input:
            # 如果指定了输入目录但没有--cli，运行交互式设置
            interactive_args = run_interactive_setup()
            run_cli_mode(interactive_args, logger)
        else:
            # GUI模式
            run_gui_mode()
            
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        logger.info("用户中断程序")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        logger.error(f"未捕获的异常: {e}")
        if args.verbose if hasattr(args, 'verbose') else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("程序结束")

if __name__ == "__main__":
    main()