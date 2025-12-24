#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能树验证和JSON提取工具

功能：
1. 验证FEATURE_TREE.md的结构和格式
2. 验证总览部分声明的数量与实际解析的数量是否一致
3. 从FEATURE_TREE.md中提取数据并生成METADATA.json
4. 提供详细的错误信息帮助修复问题

用法：
    # 使用默认路径（../../docs/PRD-Gen/FEATURE_TREE.md）
    python validate_feature_tree.py

    # 指定输入文件
    python validate_feature_tree.py -i path/to/FEATURE_TREE.md

    # 指定输入和输出文件
    python validate_feature_tree.py -i input.md -o output.json

默认路径：
    - 输入: ../../docs/PRD-Gen/FEATURE_TREE.md (相对于脚本所在目录)
    - 输出: METADATA.json (与输入文件同级目录)
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class ValidationError:
    """验证错误类"""
    def __init__(self, line_num: int, error_type: str, message: str, suggestion: str = ""):
        self.line_num = line_num
        self.error_type = error_type
        self.message = message
        self.suggestion = suggestion

    def __str__(self):
        result = f"[X] Line {self.line_num}: [{self.error_type}] {self.message}"
        if self.suggestion:
            result += f"\n    Suggestion: {self.suggestion}"
        return result


class FeatureTreeValidator:
    """功能树验证器"""

    def __init__(self, md_file_path: str):
        self.md_file_path = Path(md_file_path)
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.features: List[Dict] = []
        self.metadata: Dict = {}

    def validate(self) -> bool:
        """执行完整验证"""
        print("Starting validation of FEATURE_TREE.md...")

        if not self.md_file_path.exists():
            print(f"[ERROR] File not found: {self.md_file_path}")
            return False

        # 读取文件
        with open(self.md_file_path, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()

        # 执行各项验证
        self._validate_structure()
        self._validate_system_info()  # 验证系统信息
        self._validate_overview()
        self._validate_features()
        self._validate_counts()  # 验证数量一致性

        # 输出验证结果
        self._print_results()

        return len(self.errors) == 0

    def _validate_structure(self):
        """验证文档基本结构"""
        if not self.lines:
            self.errors.append(ValidationError(0, "结构错误", "文件为空"))
            return

        # 检查必需的标题
        required_headers = ["# 功能树", "## 系统信息", "## 总览", "## 详细结构"]
        found_headers = set()

        for i, line in enumerate(self.lines, 1):
            line = line.strip()
            for header in required_headers:
                if line.startswith(header):
                    found_headers.add(header)

        for header in required_headers:
            if header not in found_headers:
                self.errors.append(ValidationError(
                    0, "结构错误",
                    f"缺少必需的标题: {header}",
                    f"请在文件中添加 '{header}' 标题"
                ))

    def _validate_system_info(self):
        """验证系统信息部分"""
        system_info_section = False
        system_info_fields = {
            "系统名称": False,
            "系统英文名称": False,
            "系统版本": False
        }

        for i, line in enumerate(self.lines, 1):
            line = line.strip()

            if line == "## 系统信息":
                system_info_section = True
                continue

            if system_info_section:
                if line.startswith("##"):
                    break

                for field in system_info_fields:
                    if line.startswith(f"- {field}:"):
                        system_info_fields[field] = True
                        # 提取值
                        value = line.split(":", 1)[1].strip()
                        self.metadata[field] = value

        # 检查缺失的字段
        for field, found in system_info_fields.items():
            if not found:
                self.errors.append(ValidationError(
                    0, "系统信息错误",
                    f"系统信息部分缺少字段: {field}",
                    f"请在系统信息部分添加 '- {field}: ...'"
                ))

    def _validate_overview(self):
        """验证总览部分"""
        overview_section = False
        overview_fields = {
            "总功能数": False,
            "L1功能数": False,
            "L2功能数": False,
            "叶子功能数": False,
            "最大层级深度": False
        }

        for i, line in enumerate(self.lines, 1):
            line = line.strip()

            if line == "## 总览":
                overview_section = True
                continue

            if overview_section:
                if line.startswith("##"):
                    break

                for field in overview_fields:
                    if line.startswith(f"- {field}:"):
                        overview_fields[field] = True
                        # 提取数值
                        match = re.search(r': (\d+)', line)
                        if match:
                            self.metadata[field] = int(match.group(1))

        # 检查缺失的字段
        for field, found in overview_fields.items():
            if not found:
                self.errors.append(ValidationError(
                    0, "总览错误",
                    f"总览部分缺少字段: {field}",
                    f"请在总览部分添加 '- {field}: X'"
                ))

    def _validate_features(self):
        """验证功能节点"""
        current_feature = None
        current_level = None
        line_num = 0

        for i, line in enumerate(self.lines, 1):
            line_content = line.rstrip()

            # 检测功能节点标题
            if line_content.startswith("###"):
                # 先保存上一个功能节点
                if current_feature:
                    self._finalize_feature(current_feature)
                    current_feature = None

                level_match = re.match(r'^(#{3,4})\s+(L\d+):\s+(.+?)\s+\((.+?)\)\s+\[ID:\s*([a-z0-9-]+)\](\s+\[叶子\])?', line_content)

                if level_match:
                    level_markers = level_match.group(1)
                    level = level_match.group(2)
                    name_zh = level_match.group(3)
                    name_en = level_match.group(4)
                    feature_id = level_match.group(5)
                    is_leaf = level_match.group(6) is not None

                    # 验证层级标记与实际层级是否匹配
                    expected_markers = "###" if level == "L1" else "####"
                    if level_markers != expected_markers:
                        self.errors.append(ValidationError(
                            i, "格式错误",
                            f"层级标记不匹配: {level} 应该使用 {expected_markers}，实际使用了 {level_markers}",
                            f"将 '{level_markers}' 改为 '{expected_markers}'"
                        ))

                    # 验证ID格式（kebab-case）
                    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', feature_id):
                        self.errors.append(ValidationError(
                            i, "格式错误",
                            f"功能ID格式错误: {feature_id}，应该使用kebab-case（小写+连字符）",
                            "例如: problem-type-management"
                        ))

                    # 创建新的功能节点
                    current_feature = {
                        "line_num": i,
                        "level": level,
                        "name_zh": name_zh,
                        "name_en": name_en,
                        "id": feature_id,
                        "is_leaf": is_leaf,
                        "url": "",
                        "complexity_score": 0,
                        "coupling_score": 0,
                        "operations": [],
                        "prd_source": {},
                        "children": []
                    }
                    current_level = level

                else:
                    self.errors.append(ValidationError(
                        i, "格式错误",
                        f"功能节点标题格式错误",
                        "正确格式: #### L2: 中文名 (English Name) [ID: kebab-case-id] [叶子]"
                    ))

            # 解析功能节点的属性
            elif current_feature and line_content.startswith("- "):
                self._parse_feature_attribute(i, line_content, current_feature)

            # 解析操作列表
            elif current_feature and line_content.startswith("  - "):
                self._parse_operation(i, line_content, current_feature)

        # 保存最后一个功能节点
        if current_feature:
            self._finalize_feature(current_feature)

    def _parse_feature_attribute(self, line_num: int, line: str, feature: Dict):
        """解析功能节点属性"""
        # 中文名称
        if line.startswith("- 中文名称:"):
            feature["name_zh_field"] = line.split(":", 1)[1].strip()

        # 英文名称
        elif line.startswith("- 英文名称:"):
            feature["name_en_field"] = line.split(":", 1)[1].strip()

        # URL
        elif line.startswith("- URL:"):
            feature["url"] = line.split(":", 1)[1].strip()

        # 复杂度
        elif line.startswith("- 复杂度:"):
            match = re.search(r'(\d+)分', line)
            if match:
                feature["complexity_score"] = int(match.group(1))
            else:
                self.errors.append(ValidationError(
                    line_num, "格式错误",
                    "复杂度格式错误，应该包含分数",
                    "正确格式: - 复杂度: 48分 (高)"
                ))

        # 耦合度
        elif line.startswith("- 耦合度:"):
            match = re.search(r'(\d+)分', line)
            if match:
                feature["coupling_score"] = int(match.group(1))
            else:
                self.errors.append(ValidationError(
                    line_num, "格式错误",
                    "耦合度格式错误，应该包含分数",
                    "正确格式: - 耦合度: 9分 (低)"
                ))

        # 决策
        elif line.startswith("- 决策:"):
            feature["decision"] = line.split(":", 1)[1].strip()

        # 叶子节点
        elif line.startswith("- 叶子节点:"):
            is_leaf_text = line.split(":", 1)[1].strip()
            feature["is_leaf_field"] = (is_leaf_text == "是")

        # PRD来源
        elif line.startswith("- **PRD来源**:"):
            prd_match = re.search(r'\*\*PRD来源\*\*:\s*(.+?)\s+\(行(\d+)-(\d+)\)', line)
            if prd_match:
                feature["prd_source"] = {
                    "chapter": prd_match.group(1),
                    "line_start": int(prd_match.group(2)),
                    "line_end": int(prd_match.group(3))
                }
            else:
                self.errors.append(ValidationError(
                    line_num, "格式错误",
                    "PRD来源格式错误",
                    "正确格式: - **PRD来源**: 章节标题 (行X-Y)"
                ))

        # 包含的操作（标题行）
        elif line.startswith("- **包含的操作**:"):
            feature["operations_section"] = True

    def _parse_operation(self, line_num: int, line: str, feature: Dict):
        """解析操作"""
        operation_match = re.match(r'\s+- ([^:]+):\s*(.+)', line)
        if operation_match:
            op_name = operation_match.group(1).strip()
            op_desc = operation_match.group(2).strip()

            # 简单的英文名称转换（可以根据需要优化）
            op_name_en = self._translate_operation_name(op_name)

            feature["operations"].append({
                "name_zh": op_name,
                "name_en": op_name_en,
                "description": op_desc
            })
        else:
            self.warnings.append(ValidationError(
                line_num, "格式警告",
                "操作格式可能不正确",
                "正确格式:   - 操作名: 操作描述"
            ))

    def _translate_operation_name(self, name_zh: str) -> str:
        """简单的操作名称中英文映射"""
        translation_map = {
            "列表查看": "List View",
            "查询": "Search",
            "新增": "Create",
            "编辑": "Edit",
            "删除": "Delete",
            "复制": "Copy",
            "详情查看": "Detail View",
            "导出": "Export",
            "导入": "Import",
            "导出模板": "Export Template",
            "保存": "Save",
            "提交": "Submit",
            "审批": "Approval",
            "启用禁用": "Enable/Disable",
            "处理": "Process",
            "关闭": "Close",
            "进度图": "Progress Chart",
            "结项": "Closure",
            "步骤完结": "Step Completion"
        }
        return translation_map.get(name_zh, name_zh)

    def _finalize_feature(self, feature: Dict):
        """完成功能节点验证"""
        line_num = feature["line_num"]

        # 验证必填字段
        required_fields = ["name_zh", "name_en", "url"]
        for field in required_fields:
            if not feature.get(field):
                self.errors.append(ValidationError(
                    line_num, "缺失字段",
                    f"功能节点缺少必填字段: {field}",
                    f"请添加 '- {field}: ...'"
                ))

        # 验证叶子节点的特殊要求
        if feature.get("is_leaf"):
            # 叶子节点必须有复杂度和耦合度
            if feature["complexity_score"] == 0:
                self.errors.append(ValidationError(
                    line_num, "缺失字段",
                    "叶子节点缺少复杂度评分",
                    "请添加 '- 复杂度: X分 (等级)'"
                ))

            if feature["coupling_score"] == 0:
                self.errors.append(ValidationError(
                    line_num, "缺失字段",
                    "叶子节点缺少耦合度评分",
                    "请添加 '- 耦合度: X分 (等级)'"
                ))

            # 叶子节点必须有操作列表
            if len(feature["operations"]) == 0:
                self.errors.append(ValidationError(
                    line_num, "缺失字段",
                    "叶子节点缺少操作列表",
                    "请添加 '- **包含的操作**: ...' 并列出至少3个操作"
                ))
            elif len(feature["operations"]) < 3:
                self.warnings.append(ValidationError(
                    line_num, "操作数量警告",
                    f"叶子节点操作数量较少 ({len(feature['operations'])}个)，建议至少3个",
                    "检查是否有遗漏的操作"
                ))

            # 验证标题中的[叶子]标记
            if not feature.get("is_leaf"):
                self.errors.append(ValidationError(
                    line_num, "格式错误",
                    "叶子节点标题缺少 [叶子] 标记",
                    "在标题末尾添加 [叶子]"
                ))

        # 验证PRD来源
        if not feature.get("prd_source"):
            self.errors.append(ValidationError(
                line_num, "缺失字段",
                "功能节点缺少PRD来源",
                "请添加 '- **PRD来源**: 章节标题 (行X-Y)'"
            ))

        # 添加到功能列表
        self.features.append(feature)

    def _validate_counts(self):
        """验证总览部分的数量与实际解析的数量是否一致"""
        actual_total = len(self.features)
        actual_l1 = len([f for f in self.features if f['level'] == 'L1'])
        actual_l2 = len([f for f in self.features if f['level'] == 'L2'])
        actual_l3 = len([f for f in self.features if f['level'] == 'L3'])
        actual_l4 = len([f for f in self.features if f['level'] == 'L4'])
        actual_leaf = len([f for f in self.features if f['is_leaf']])

        # 计算最大层级深度
        max_level = 0
        for f in self.features:
            level_num = int(f['level'][1:])  # 提取L1中的1
            if level_num > max_level:
                max_level = level_num

        # 对比总览中声明的数量
        declared_total = self.metadata.get("总功能数", 0)
        declared_l1 = self.metadata.get("L1功能数", 0)
        declared_l2 = self.metadata.get("L2功能数", 0)
        declared_l3 = self.metadata.get("L3功能数", 0)
        declared_leaf = self.metadata.get("叶子功能数", 0)
        declared_depth = self.metadata.get("最大层级深度", 0)

        # 验证总功能数
        if declared_total != actual_total:
            self.errors.append(ValidationError(
                0, "数量不一致",
                f"总览中声明的总功能数({declared_total})与实际解析的数量({actual_total})不一致",
                f"请将总览中的'总功能数'修改为: {actual_total}"
            ))

        # 验证L1功能数
        if declared_l1 != actual_l1:
            self.errors.append(ValidationError(
                0, "数量不一致",
                f"总览中声明的L1功能数({declared_l1})与实际解析的数量({actual_l1})不一致",
                f"请将总览中的'L1功能数'修改为: {actual_l1}"
            ))

        # 验证L2功能数
        if declared_l2 != actual_l2:
            self.errors.append(ValidationError(
                0, "数量不一致",
                f"总览中声明的L2功能数({declared_l2})与实际解析的数量({actual_l2})不一致",
                f"请将总览中的'L2功能数'修改为: {actual_l2}"
            ))

        # 验证L3功能数（如果总览中有声明）
        if declared_l3 != actual_l3 and declared_l3 > 0:
            self.errors.append(ValidationError(
                0, "数量不一致",
                f"总览中声明的L3功能数({declared_l3})与实际解析的数量({actual_l3})不一致",
                f"请将总览中的'L3功能数'修改为: {actual_l3}"
            ))

        # 验证叶子功能数
        if declared_leaf != actual_leaf:
            self.errors.append(ValidationError(
                0, "数量不一致",
                f"总览中声明的叶子功能数({declared_leaf})与实际解析的数量({actual_leaf})不一致",
                f"请将总览中的'叶子功能数'修改为: {actual_leaf}"
            ))

        # 验证最大层级深度
        if declared_depth != max_level:
            self.errors.append(ValidationError(
                0, "数量不一致",
                f"总览中声明的最大层级深度({declared_depth})与实际解析的深度({max_level})不一致",
                f"请将总览中的'最大层级深度'修改为: {max_level}"
            ))

    def _print_results(self):
        """打印验证结果"""
        print("\n" + "="*80)
        print("VALIDATION RESULTS")
        print("="*80)

        if self.errors:
            print(f"\n[ERROR] Found {len(self.errors)} errors:\n")
            for error in self.errors:
                print(error)
        else:
            print("\n[OK] No errors found!")

        if self.warnings:
            print(f"\n[WARNING] Found {len(self.warnings)} warnings:\n")
            for warning in self.warnings:
                print(warning)

        # 显示实际统计和声明的对比
        actual_total = len(self.features)
        actual_l1 = len([f for f in self.features if f['level'] == 'L1'])
        actual_l2 = len([f for f in self.features if f['level'] == 'L2'])
        actual_leaf = len([f for f in self.features if f['is_leaf']])
        actual_ops = sum(len(f['operations']) for f in self.features)

        declared_total = self.metadata.get("总功能数", 0)
        declared_l1 = self.metadata.get("L1功能数", 0)
        declared_l2 = self.metadata.get("L2功能数", 0)
        declared_leaf = self.metadata.get("叶子功能数", 0)

        print(f"\nSTATISTICS:")
        print(f"   - Total features: {actual_total} (declared: {declared_total}) {'[OK]' if actual_total == declared_total else '[MISMATCH]'}")
        print(f"   - L1 nodes: {actual_l1} (declared: {declared_l1}) {'[OK]' if actual_l1 == declared_l1 else '[MISMATCH]'}")
        print(f"   - L2 nodes: {actual_l2} (declared: {declared_l2}) {'[OK]' if actual_l2 == declared_l2 else '[MISMATCH]'}")
        print(f"   - Leaf nodes: {actual_leaf} (declared: {declared_leaf}) {'[OK]' if actual_leaf == declared_leaf else '[MISMATCH]'}")
        print(f"   - Total operations: {actual_ops}")
        print("="*80 + "\n")

    def extract_to_json(self, output_path: str) -> bool:
        """提取数据到JSON文件"""
        if self.errors:
            print("[ERROR] Cannot generate JSON due to validation errors")
            return False

        print(f"Generating {output_path}...")

        # 构建JSON结构
        json_data = {
            "version": "1.0",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_document": "System-Design_text_only.md",
            "system_info": {
                "name_zh": self.metadata.get("系统名称", ""),
                "name_en": self.metadata.get("系统英文名称", ""),
                "version": self.metadata.get("系统版本", "")
            },
            "total_features": self.metadata.get("总功能数", len(self.features)),
            "l1_count": self.metadata.get("L1功能数", 0),
            "l2_count": self.metadata.get("L2功能数", 0),
            "l3_count": self.metadata.get("L3功能数", 0),
            "l4_count": self.metadata.get("L4功能数", 0),
            "leaf_count": self.metadata.get("叶子功能数", 0),
            "max_depth": self.metadata.get("最大层级深度", 2),
            "features": []
        }

        # 构建功能树结构
        l1_features = [f for f in self.features if f["level"] == "L1"]
        l2_features = [f for f in self.features if f["level"] == "L2"]

        for l1 in l1_features:
            l1_node = {
                "id": l1["id"],
                "level": l1["level"],
                "name_zh": l1["name_zh"],
                "name_en": l1["name_en"],
                "url": l1["url"],
                "complexity_score": l1["complexity_score"],
                "coupling_score": l1["coupling_score"],
                "is_leaf": l1["is_leaf"],
                "operations": l1["operations"],
                "prd_source": l1["prd_source"],
                "children": []
            }

            # 添加L2子节点
            for l2 in l2_features:
                l2_node = {
                    "id": l2["id"],
                    "level": l2["level"],
                    "name_zh": l2["name_zh"],
                    "name_en": l2["name_en"],
                    "url": l2["url"],
                    "complexity_score": l2["complexity_score"],
                    "coupling_score": l2["coupling_score"],
                    "is_leaf": l2["is_leaf"],
                    "operations": l2["operations"],
                    "prd_source": l2["prd_source"],
                    "children": []
                }
                l1_node["children"].append(l2_node)

            json_data["features"].append(l1_node)

        # 写入JSON文件
        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        print(f"[OK] JSON file generated: {output_path}")
        print(f"     File size: {output_file.stat().st_size / 1024:.2f} KB")
        return True


def main():
    """主函数"""
    import sys
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Feature Tree Validation and JSON Extraction Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default paths
  python validate_feature_tree.py

  # Specify input file only
  python validate_feature_tree.py -i path/to/FEATURE_TREE.md

  # Specify both input and output files
  python validate_feature_tree.py -i input.md -o output.json
        '''
    )

    # 默认路径：相对于脚本所在目录（.claude/agents）
    script_dir = Path(__file__).parent
    default_input = script_dir / ".." / ".." / "docs" / "PRD-Gen" / "FEATURE_TREE.md"

    parser.add_argument(
        '-i', '--input',
        type=str,
        default=str(default_input),
        help=f'Input FEATURE_TREE.md file path (default: {default_input})'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output METADATA.json file path (default: same directory as input file)'
    )

    args = parser.parse_args()

    # 处理输入文件路径
    md_file = Path(args.input).resolve()

    # 处理输出文件路径
    if args.output:
        json_file = Path(args.output).resolve()
    else:
        # 默认输出到输入文件同级目录
        json_file = md_file.parent / "METADATA.json"

    # 检查输入文件是否存在
    if not md_file.exists():
        print(f"[ERROR] Input file not found: {md_file}")
        return 1

    print("="*80)
    print("Feature Tree Validation and JSON Extraction Tool")
    print("="*80)
    print(f"Input file:  {md_file}")
    print(f"Output file: {json_file}")
    print()

    # 创建验证器
    validator = FeatureTreeValidator(str(md_file))

    # 执行验证
    if validator.validate():
        # 提取JSON
        validator.extract_to_json(str(json_file))
        print("\n[OK] All done!")
        return 0
    else:
        print("\n[ERROR] Validation failed. Please fix the errors above and try again.")
        return 1


if __name__ == "__main__":
    exit(main())
