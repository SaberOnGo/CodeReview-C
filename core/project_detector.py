#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# project_detector.py
"""
项目类型检测器 - 自动检测项目类型和C标准
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass

@dataclass 
class ProjectInfo:
    """项目信息"""
    project_type: str
    c_standard: str
    description: str
    confidence: float  # 置信度 0-1
    detected_features: List[str]

class ProjectDetector:
    """项目类型检测器"""
    
    def __init__(self):
        # 项目类型检测模式
        self.project_patterns = {
            "ESP32": {
                "files": ["sdkconfig", "CMakeLists.txt", "Kconfig", "partitions.csv"],
                "includes": [
                    "esp_*.h", "freertos/", "driver/", "nvs_flash.h",
                    "esp_wifi.h", "esp_event.h", "esp_log.h"
                ],
                "defines": ["ESP32", "CONFIG_", "portTICK_PERIOD_MS"],
                "c_standard": "C99",
                "description": "ESP32 IoT开发项目"
            },
            
            "STM32_HAL": {
                "files": ["*.ioc", "startup_stm32*.s", "*.ld"],
                "includes": [
                    "stm32*hal*.h", "stm32*it.h", "main.h", 
                    "cmsis_os.h", "FreeRTOS.h"
                ],
                "defines": ["STM32", "HAL_", "USE_HAL_DRIVER"],
                "c_standard": "C99",
                "description": "STM32 HAL库项目"
            },
            
            "STM32_LL": {
                "files": ["startup_stm32*.s", "*.ld"],
                "includes": ["stm32*ll*.h", "stm32*xx.h"],
                "defines": ["STM32", "USE_FULL_LL_DRIVER"],
                "c_standard": "C99", 
                "description": "STM32 LL库项目"
            },
            
            "Arduino": {
                "files": ["*.ino", "platformio.ini", "arduino.json"],
                "includes": ["Arduino.h", "Wire.h", "SPI.h"],
                "defines": ["ARDUINO", "F_CPU"],
                "c_standard": "C99",
                "description": "Arduino开发项目"
            },
            
            "Keil_MDK": {
                "files": ["*.uvprojx", "*.uvoptx", "*.sct"],
                "includes": ["ARMCM*.h", "core_cm*.h"],
                "defines": ["__CC_ARM", "__ARMCC_VERSION"],
                "c_standard": "C90",
                "description": "Keil MDK项目"
            },
            
            "Linux_GNU": {
                "files": ["Makefile", "configure", "*.mk", "CMakeLists.txt"],
                "includes": [
                    "unistd.h", "sys/", "pthread.h", "signal.h",
                    "netinet/", "arpa/"
                ],
                "defines": ["__GNUC__", "_GNU_SOURCE", "LINUX"],
                "c_standard": "GNU99",
                "description": "Linux GNU C项目"
            },
            
            "Windows_MSVC": {
                "files": ["*.vcxproj", "*.sln", "*.vcproj"],
                "includes": ["windows.h", "tchar.h", "stdafx.h"],
                "defines": ["_WIN32", "_MSC_VER", "WIN32"],
                "c_standard": "C90",
                "description": "Windows MSVC项目"
            },
            
            "Generic_C": {
                "files": ["*.c", "*.h"],
                "includes": ["stdio.h", "stdlib.h", "string.h"],
                "defines": [],
                "c_standard": "C99",
                "description": "通用C语言项目"
            }
        }
        
        # C标准特性检测
        self.c_standard_features = {
            "C90": {
                "forbidden": [
                    r"//.*",  # 单行注释
                    r"int\s+\w+\s*\[.*\].*=.*{.*}",  # 变长数组初始化
                    r"for\s*\(\s*int\s+",  # for循环中声明变量
                ],
                "description": "ANSI C (C90/C89)"
            },
            
            "C99": {
                "features": [
                    r"//.*",  # 单行注释
                    r"for\s*\(\s*int\s+",  # for循环中声明变量
                    r"int\s+\w+\s*\[.*\w+.*\]",  # 变长数组
                    r"\.\w+\s*=",  # designated initializers
                    r"inline\s+",  # inline关键字
                ],
                "includes": ["stdbool.h", "stdint.h", "inttypes.h"],
                "description": "ISO C99标准"
            },
            
            "C11": {
                "features": [
                    r"_Static_assert\s*\(",
                    r"_Generic\s*\(",
                    r"_Alignof\s*\(",
                    r"_Thread_local\s+",
                ],
                "includes": ["stdalign.h", "stdatomic.h", "stdnoreturn.h"],
                "description": "ISO C11标准"
            },
            
            "GNU_Extensions": {
                "features": [
                    r"typeof\s*\(",
                    r"__attribute__\s*\(",
                    r"__builtin_\w+",
                    r"struct\s+\w+\s*{\s*[^}]*;\s*\[\s*0\s*\]",  # 零长度数组
                    r"#pragma\s+GCC",
                ],
                "description": "GNU C扩展"
            }
        }
    
    def detect_project_type(self, project_path: Path) -> ProjectInfo:
        """检测项目类型"""
        print(f"检测项目类型: {project_path}")
        
        scores = {}
        detected_features = []
        
        # 检测各种项目类型
        for proj_type, patterns in self.project_patterns.items():
            score = 0
            features = []
            
            # 检查特征文件
            file_score = self._check_files(project_path, patterns["files"])
            score += file_score * 0.4
            if file_score > 0:
                features.append(f"特征文件匹配({file_score:.1f})")
            
            # 检查包含文件
            include_score = self._check_includes(project_path, patterns["includes"])
            score += include_score * 0.4
            if include_score > 0:
                features.append(f"头文件匹配({include_score:.1f})")
            
            # 检查宏定义
            define_score = self._check_defines(project_path, patterns["defines"])
            score += define_score * 0.2
            if define_score > 0:
                features.append(f"宏定义匹配({define_score:.1f})")
            
            scores[proj_type] = score
            if score > 0:
                detected_features.extend([f"{proj_type}: {f}" for f in features])
        
        # 选择得分最高的项目类型
        best_type = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_type]
        
        # 如果得分太低，使用通用C项目
        if best_score < 0.3:
            best_type = "Generic_C"
            best_score = 0.5
            detected_features.append("使用默认通用C项目类型")
        
        # 检测C标准
        c_standard = self._detect_c_standard(project_path)
        if not c_standard:
            c_standard = self.project_patterns[best_type]["c_standard"]
        
        return ProjectInfo(
            project_type=best_type,
            c_standard=c_standard,
            description=self.project_patterns[best_type]["description"],
            confidence=best_score,
            detected_features=detected_features
        )
    
    def _check_files(self, project_path: Path, file_patterns: List[str]) -> float:
        """检查特征文件"""
        if not file_patterns:
            return 0
        
        found_count = 0
        total_patterns = len(file_patterns)
        
        for pattern in file_patterns:
            # 使用glob匹配文件
            if list(project_path.rglob(pattern)):
                found_count += 1
        
        return found_count / total_patterns if total_patterns > 0 else 0
    
    def _check_includes(self, project_path: Path, include_patterns: List[str]) -> float:
        """检查包含的头文件"""
        if not include_patterns:
            return 0
        
        c_files = list(project_path.rglob("*.c")) + list(project_path.rglob("*.h"))
        if not c_files:
            return 0
        
        found_patterns = set()
        
        for file_path in c_files[:20]:  # 限制检查文件数量
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for pattern in include_patterns:
                    # 简单的包含检查
                    if pattern.endswith('/'):
                        # 目录匹配
                        if f'#include <{pattern}' in content or f'#include "{pattern}' in content:
                            found_patterns.add(pattern)
                    else:
                        # 文件匹配
                        if f'#include <{pattern}>' in content or f'#include "{pattern}"' in content:
                            found_patterns.add(pattern)
                        # 通配符匹配
                        if '*' in pattern:
                            import fnmatch
                            include_regex = pattern.replace('*', r'[^<>"]*')
                            if re.search(f'#include\\s*[<"]{include_regex}[>"]', content):
                                found_patterns.add(pattern)
                                
            except Exception:
                continue
        
        return len(found_patterns) / len(include_patterns)
    
    def _check_defines(self, project_path: Path, define_patterns: List[str]) -> float:
        """检查宏定义"""
        if not define_patterns:
            return 0
        
        c_files = list(project_path.rglob("*.c")) + list(project_path.rglob("*.h"))
        if not c_files:
            return 0
        
        found_patterns = set()
        
        for file_path in c_files[:10]:  # 限制检查文件数量
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for pattern in define_patterns:
                    # 检查宏定义或使用
                    if f'#define {pattern}' in content or f'{pattern}' in content:
                        found_patterns.add(pattern)
                        
            except Exception:
                continue
        
        return len(found_patterns) / len(define_patterns)
    
    def _detect_c_standard(self, project_path: Path) -> Optional[str]:
        """检测C标准"""
        c_files = list(project_path.rglob("*.c")) + list(project_path.rglob("*.h"))
        if not c_files:
            return None
        
        feature_scores = {
            "C90": 0,
            "C99": 0, 
            "C11": 0,
            "GNU_Extensions": 0
        }
        
        # 检查最多20个文件
        for file_path in c_files[:20]:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 检查各种C标准特性
                for standard, patterns in self.c_standard_features.items():
                    if standard == "C90":
                        # C90通过检查是否缺少新特性来判断
                        continue
                    
                    # 检查语法特性
                    features = patterns.get("features", [])
                    for feature_regex in features:
                        if re.search(feature_regex, content):
                            feature_scores[standard] += 1
                    
                    # 检查包含的头文件
                    includes = patterns.get("includes", [])
                    for include in includes:
                        if f'#include <{include}>' in content:
                            feature_scores[standard] += 1
                            
            except Exception:
                continue
        
        # 确定最可能的C标准
        if feature_scores["GNU_Extensions"] > 0:
            return "GNU99"
        elif feature_scores["C11"] > 0:
            return "C11"
        elif feature_scores["C99"] > 2:
            return "C99"
        else:
            return "C90"
    
    def get_recommended_rules(self, project_info: ProjectInfo) -> List[str]:
        """根据项目类型推荐规则"""
        base_rules = ["C001", "C002", "L001"]  # 基础规则
        
        project_specific_rules = {
            "ESP32": ["E001", "E002", "E003"],  # ESP32特定规则
            "STM32_HAL": ["S001", "S002"],      # STM32特定规则
            "Arduino": ["A001", "A002"],        # Arduino特定规则
            "Keil_MDK": ["K001"],              # Keil特定规则
            "Linux_GNU": ["G001", "G002"],      # GNU特定规则
        }
        
        recommended = base_rules.copy()
        if project_info.project_type in project_specific_rules:
            recommended.extend(project_specific_rules[project_info.project_type])
        
        return recommended
    
    def generate_detection_report(self, project_info: ProjectInfo) -> str:
        """生成检测报告"""
        report = f"""
项目检测报告
============

项目类型: {project_info.project_type}
项目描述: {project_info.description}
C语言标准: {project_info.c_standard}
检测置信度: {project_info.confidence:.1%}

检测到的特征:
"""
        for feature in project_info.detected_features:
            report += f"  • {feature}\n"
        
        recommended_rules = self.get_recommended_rules(project_info)
        report += f"\n推荐规则: {', '.join(recommended_rules)}\n"
        
        return report


# 使用示例
if __name__ == "__main__":
    detector = ProjectDetector()
    
    # 检测项目
    project_path = Path("test_project")
    if project_path.exists():
        project_info = detector.detect_project_type(project_path)
        
        print(detector.generate_detection_report(project_info))
    else:
        print("测试项目目录不存在")