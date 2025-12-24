"""
PRD Clarification Index Generator and Validator

This script parses clarification.md and generates clarification_index.json.
It also validates the format to ensure consistency.

Usage:
    python generate_clarification_index.py [--validate-only]
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class ClarificationParser:
    """Parse clarification.md and extract structured data."""

    def __init__(self, md_file_path: str):
        self.md_file_path = Path(md_file_path)
        self.content = self._read_file()
        self.lines = self.content.split('\n')

    def _read_file(self) -> str:
        """Read markdown file content."""
        with open(self.md_file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from markdown header."""
        metadata = {
            'module_id': None,
            'module_name_cn': None,
            'module_name_en': None,
            'prd_file': None,
            'prd_section': None,
            'prd_lines': None,
            'generated_at': None,
            'version': None
        }

        # Extract from blockquote section
        blockquote_pattern = r'^> \*\*(.+?):\*\* (.+)$'
        for line in self.lines[:20]:  # Check first 20 lines
            match = re.match(blockquote_pattern, line)
            if match:
                key = match.group(1)
                value = match.group(2)
                if 'Module ID' in key:
                    metadata['module_id'] = value
                elif 'PRD来源' in key:
                    # Parse "6.1.3 D1组建团队 (行212-222)"
                    prd_match = re.match(r'([\d.]+)\s+(.+?)\s+\(行([\d-]+)\)', value)
                    if prd_match:
                        metadata['prd_section'] = prd_match.group(1)
                        metadata['module_name_cn'] = prd_match.group(2)
                        metadata['prd_lines'] = prd_match.group(3)
                elif 'PRD文件' in key:
                    metadata['prd_file'] = value
                elif '生成时间' in key:
                    metadata['generated_at'] = value
                elif '文档状态' in key or '版本' in key:
                    metadata['version'] = 'v3.0'

        # Extract English name from header
        for line in self.lines[:10]:
            if line.startswith('# OpenSpec提议澄清文档'):
                # Extract Chinese and English names
                parts = line.split(':')
                if len(parts) > 1:
                    names = parts[1].strip()
                    # Assume format: "中文名 (English Name)" or just "中文名"
                    metadata['module_name_en'] = 'D1 Team Formation'

        return metadata

    def parse_html_metadata(self, line: str) -> Optional[Dict[str, str]]:
        """Parse HTML comment metadata."""
        pattern = r'<!-- meta:(.+?) -->'
        match = re.search(pattern, line)
        if match:
            meta_str = match.group(1)
            meta_dict = {}
            for pair in meta_str.split(','):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    meta_dict[key.strip()] = value.strip()
            return meta_dict
        return None

    def parse_prd_location(self, cell: str) -> Dict[str, Any]:
        """Parse PRD location from table cell."""
        # Patterns: [PRD:行214], [PRD:行217-小组领导者], [需补充], [推断]
        prd_patterns = [
            (r'\[PRD:行(\d+)(?:-(.+?))?\]', 'prd'),
            (r'\[需补充\]', 'supplement'),
            (r'\[推断\]', 'inferred'),
            (r'\[系统生成\]', 'system')
        ]

        location = {
            'file': None,
            'section': None,
            'line': None,
            'text_snippet': None
        }

        for pattern, loc_type in prd_patterns:
            match = re.search(pattern, cell)
            if match:
                if loc_type == 'prd':
                    location['line'] = int(match.group(1))
                    if match.group(2):
                        location['text_snippet'] = match.group(2)
                elif loc_type == 'supplement':
                    location['text_snippet'] = '需补充'
                elif loc_type == 'inferred':
                    location['text_snippet'] = '推断'
                elif loc_type == 'system':
                    location['text_snippet'] = '系统生成'
                break

        return location

    def parse_table(self, start_line: int) -> Tuple[List[Dict[str, str]], int]:
        """Parse markdown table starting from given line."""
        rows = []
        headers = []
        i = start_line

        # Find table start
        while i < len(self.lines):
            line = self.lines[i].strip()
            if line.startswith('|') and '|' in line[1:]:
                # This is a table row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if not headers:
                    headers = cells
                    i += 1
                    # Skip separator line
                    if i < len(self.lines) and '|---' in self.lines[i]:
                        i += 1
                    continue

                if len(cells) == len(headers):
                    row = dict(zip(headers, cells))
                    rows.append(row)
                i += 1
            else:
                break

        return rows, i

    def extract_clarification_items(self, start_line: int, end_line: int, section_id: str) -> List[Dict[str, Any]]:
        """Extract clarification items (questions to be filled) from a section."""
        items = []

        # Patterns for different types of clarification items
        patterns = [
            (r'\(请补充\)', 'to_fill', '请补充'),
            (r'\(待确认\)', 'to_confirm', '待确认'),
            (r'\[需补充\]', 'to_fill', '需补充'),
            (r'\[待确认\]', 'to_confirm', '待确认'),
            (r'\*\*待补充:\*\*', 'to_fill', '待补充'),
            (r'- \[ \]', 'checkbox', '待选择'),
            (r'_____', 'blank', '待填写'),
            (r'\?\?\?', 'to_fill', '待填写'),
        ]

        for line_num in range(start_line, min(end_line, len(self.lines))):
            line = self.lines[line_num]

            for pattern, item_type, label in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    # Extract context (surrounding text)
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(line), match.end() + 50)
                    context = line[context_start:context_end].strip()

                    # Try to extract the question or field name
                    question = self._extract_question_from_context(line, match.start())

                    item = {
                        'type': item_type,
                        'label': label,
                        'question': question,
                        'context': context,
                        'md_line': line_num + 1,  # 1-indexed for display
                        'section_id': section_id,
                        'status': 'pending'
                    }
                    items.append(item)

        return items

    def _extract_question_from_context(self, line: str, match_pos: int) -> str:
        """Extract the question or field name from the context."""
        # Look backwards to find the question/field name
        prefix = line[:match_pos].strip()

        # Try to extract from markdown bold/italic
        bold_match = re.search(r'\*\*(.+?)\*\*\s*$', prefix)
        if bold_match:
            return bold_match.group(1)

        # Try to extract from ":" pattern
        colon_match = re.search(r'[：:]\s*(.+?)$', prefix)
        if colon_match:
            return colon_match.group(1).strip()

        # Try to extract from "- **field:**" pattern
        field_match = re.search(r'-\s*\*\*(.+?)\*\*', prefix)
        if field_match:
            return field_match.group(1)

        # Try to extract from subsection header
        header_match = re.search(r'###\s+(.+?)$', prefix)
        if header_match:
            return header_match.group(1)

        # Return first 30 chars if no specific pattern found
        return prefix[-30:] if len(prefix) > 30 else prefix

    def parse_clarification_wrapper(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse HTML clarification wrapper comments."""
        # Match: <!-- clarification:start,id=c-5.2-1,type=data_schema,... -->
        start_pattern = r'<!-- clarification:start,(.+?) -->'
        end_pattern = r'<!-- clarification:end -->'

        start_match = re.search(start_pattern, line)
        if start_match:
            attrs = {}
            for pair in start_match.group(1).split(','):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    attrs[key.strip()] = value.strip()
            return {'wrapper_type': 'start', 'attributes': attrs}

        if re.search(end_pattern, line):
            return {'wrapper_type': 'end'}

        return None

    def extract_wrapped_clarifications(self) -> List[Dict[str, Any]]:
        """Extract clarifications with HTML wrapper metadata."""
        wrapped_items = []
        current_item = None
        content_lines = []

        for i, line in enumerate(self.lines):
            wrapper = self.parse_clarification_wrapper(line)

            if wrapper and wrapper['wrapper_type'] == 'start':
                attrs = wrapper['attributes']
                current_item = {
                    'id': attrs.get('id'),
                    'type': attrs.get('type'),
                    'section': attrs.get('section'),
                    'operation_id': attrs.get('operation_id'),
                    'prd_ref': attrs.get('prd_ref'),
                    'priority': attrs.get('priority', 'medium'),
                    'status': attrs.get('status', 'pending'),
                    'md_line_start': i + 1,
                    'content': []
                }
                content_lines = []

            elif wrapper and wrapper['wrapper_type'] == 'end':
                if current_item:
                    current_item['content'] = '\n'.join(content_lines).strip()
                    current_item['md_line_end'] = i + 1

                    # Parse question and options
                    question, options = self._parse_question_content(current_item['content'])
                    current_item['question'] = question
                    current_item['options'] = options

                    wrapped_items.append(current_item)
                    current_item = None

            elif current_item is not None:
                content_lines.append(line)

        return wrapped_items

    def _parse_question_content(self, content: str) -> Tuple[str, List[Dict]]:
        """Parse question text and options from markdown."""
        lines = content.split('\n')
        question = ""
        options = []

        for line in lines:
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                # Extract question title
                question = line.strip('*').strip(':')
            elif line.startswith('- [ ]'):
                # Checkbox option
                options.append({
                    'type': 'checkbox',
                    'text': line[5:].strip(),
                    'checked': False
                })
            elif '_____' in line or '____' in line:
                # Fill-in-the-blank option
                options.append({
                    'type': 'blank',
                    'text': line,
                    'value': None
                })

        return question, options

    def extract_sections(self) -> List[Dict[str, Any]]:
        """Extract all sections from markdown."""
        sections = []
        current_section = None
        i = 0

        while i < len(self.lines):
            line = self.lines[i]

            # Check for HTML metadata
            meta = self.parse_html_metadata(line)
            if meta:
                if 'section' in meta:
                    section_id = meta.get('section')
                    section_type = meta.get('type', 'unknown')

                    # Find section header
                    j = i + 1
                    while j < len(self.lines) and not self.lines[j].strip().startswith('##'):
                        j += 1

                    if j < len(self.lines):
                        header = self.lines[j].strip()
                        section_name = header.lstrip('#').strip()

                        # Find section end (next section or end of document)
                        section_end = j + 1
                        while section_end < len(self.lines):
                            next_line = self.lines[section_end]
                            next_meta = self.parse_html_metadata(next_line)
                            if next_meta and 'section' in next_meta:
                                break
                            section_end += 1

                        current_section = {
                            'section_id': section_id,
                            'section_name': section_name,
                            'section_type': section_type,
                            'md_line_start': i,
                            'md_line_end': section_end,
                            'items': [],
                            'clarification_items': []
                        }

                        # Parse table if exists
                        k = j + 1
                        while k < section_end and not self.lines[k].strip().startswith('##'):
                            if self.lines[k].strip().startswith('|'):
                                table_data, end_line = self.parse_table(k)
                                for row in table_data:
                                    item = {
                                        'data': row,
                                        'md_line': k
                                    }
                                    # Parse PRD location if exists
                                    if 'PRD定位' in row:
                                        item['prd_location'] = self.parse_prd_location(row['PRD定位'])
                                        # Check if this row needs clarification
                                        if '[需补充]' in row.get('PRD定位', ''):
                                            item['needs_clarification'] = True
                                    current_section['items'].append(item)
                                k = end_line
                                break
                            k += 1

                        # Extract clarification items (questions to be filled)
                        clarification_items = self.extract_clarification_items(j, section_end, section_id)
                        current_section['clarification_items'] = clarification_items

                        sections.append(current_section)

            i += 1

        return sections

    def extract_operations(self) -> List[Dict[str, Any]]:
        """Extract all operations from section 6."""
        operations = []
        i = 0

        while i < len(self.lines):
            line = self.lines[i]

            # Check for operation metadata
            meta = self.parse_html_metadata(line)
            if meta and 'operation_id' in meta:
                operation = {
                    'operation_id': meta.get('operation_id'),
                    'operation_name': meta.get('operation_name'),
                    'operation_type': None,
                    'prd_location': {
                        'section': meta.get('prd_section'),
                        'lines': meta.get('prd_lines')
                    },
                    'md_line_start': i,
                    'md_line_end': None,
                    'components': {}
                }

                # Parse operation components (basic_info, input_spec, output_spec, etc.)
                j = i + 1
                current_component = None

                while j < len(self.lines):
                    component_line = self.lines[j]

                    # Check for next operation
                    next_meta = self.parse_html_metadata(component_line)
                    if next_meta and 'operation_id' in next_meta and next_meta['operation_id'] != operation['operation_id']:
                        break

                    # Check for component metadata
                    comp_meta = self.parse_html_metadata(component_line)
                    if comp_meta:
                        comp_type = None
                        if 'input_spec' in component_line:
                            comp_type = 'input_spec'
                        elif 'output_spec' in component_line:
                            comp_type = 'output_spec'
                        elif 'scenarios' in component_line:
                            comp_type = 'scenarios'
                        elif 'errors' in component_line:
                            comp_type = 'errors'
                        elif 'boundaries' in component_line:
                            comp_type = 'boundaries'
                        elif 'test_cases' in component_line:
                            comp_type = 'test_cases'

                        if comp_type:
                            current_component = {
                                'type': comp_type,
                                'md_line': j,
                                'fields': []
                            }

                            # Parse table for this component
                            k = j + 1
                            while k < len(self.lines) and not self.lines[k].strip().startswith('####'):
                                if self.lines[k].strip().startswith('|'):
                                    table_data, end_line = self.parse_table(k)
                                    current_component['fields'] = table_data
                                    k = end_line
                                    break
                                k += 1

                            operation['components'][comp_type] = current_component
                            j = k
                            continue

                    j += 1

                operation['md_line_end'] = j
                operations.append(operation)
                i = j
            else:
                i += 1

        return operations

    def build_navigation_index(self, sections: List[Dict], operations: List[Dict]) -> Dict[str, Any]:
        """Build navigation indices for quick lookup."""
        nav_index = {
            'by_prd_line': {},
            'by_operation': {},
            'by_section': {},
            'by_scenario': {},
            'by_clarification_item': []
        }

        # Build by_prd_line index
        for section in sections:
            for item in section.get('items', []):
                prd_loc = item.get('prd_location', {})
                if prd_loc.get('line'):
                    line_num = str(prd_loc['line'])
                    if line_num not in nav_index['by_prd_line']:
                        nav_index['by_prd_line'][line_num] = []
                    nav_index['by_prd_line'][line_num].append({
                        'type': 'section',
                        'section_id': section['section_id'],
                        'item_data': item.get('data', {}),
                        'md_line': item.get('md_line')
                    })

        # Build by_operation index
        for op in operations:
            nav_index['by_operation'][op['operation_id']] = {
                'name': op['operation_name'],
                'prd_lines': op['prd_location'].get('lines'),
                'md_line_start': op['md_line_start'],
                'md_line_end': op['md_line_end'],
                'components': list(op['components'].keys())
            }

        # Build by_section index with clarification items count
        for section in sections:
            clarification_count = len(section.get('clarification_items', []))
            nav_index['by_section'][section['section_id']] = {
                'name': section['section_name'],
                'type': section['section_type'],
                'md_line_start': section['md_line_start'],
                'md_line_end': section['md_line_end'],
                'item_count': len(section.get('items', [])),
                'clarification_count': clarification_count,
                'needs_attention': clarification_count > 0
            }

        # Build by_clarification_item index (flat list for easy frontend access)
        for section in sections:
            for item in section.get('clarification_items', []):
                nav_index['by_clarification_item'].append({
                    'section_id': item['section_id'],
                    'section_name': section['section_name'],
                    'type': item['type'],
                    'label': item['label'],
                    'question': item['question'],
                    'context': item['context'],
                    'md_line': item['md_line'],
                    'status': item['status']
                })

        return nav_index

    def calculate_statistics(self, sections: List[Dict], operations: List[Dict]) -> Dict[str, int]:
        """Calculate statistics about the clarification document."""
        stats = {
            'total_sections': len(sections),
            'total_operations': len(operations),
            'total_scenarios': 0,
            'total_fields': 0,
            'total_test_cases': 0,
            'required_items': 0,
            'optional_items': 0,
            'to_be_confirmed_items': 0,
            'to_be_filled_items': 0,
            'total_clarification_items': 0,
            'clarification_by_type': {
                'to_fill': 0,
                'to_confirm': 0,
                'checkbox': 0,
                'blank': 0
            },
            'blockers': 0
        }

        for op in operations:
            if 'scenarios' in op['components']:
                stats['total_scenarios'] += len(op['components']['scenarios'].get('fields', []))
            if 'test_cases' in op['components']:
                stats['total_test_cases'] += len(op['components']['test_cases'].get('fields', []))

        # Count clarification items from sections
        for section in sections:
            clarification_items = section.get('clarification_items', [])
            stats['total_clarification_items'] += len(clarification_items)

            for item in clarification_items:
                item_type = item.get('type', 'to_fill')
                if item_type in stats['clarification_by_type']:
                    stats['clarification_by_type'][item_type] += 1

                if item_type == 'to_confirm':
                    stats['to_be_confirmed_items'] += 1
                elif item_type in ['to_fill', 'blank']:
                    stats['to_be_filled_items'] += 1

            # Also count from table items
            for item in section.get('items', []):
                data = item.get('data', {})
                if '必填' in str(data):
                    stats['required_items'] += 1
                if '可选' in str(data):
                    stats['optional_items'] += 1

                # Count [需补充] in PRD location
                prd_loc = item.get('prd_location', {})
                if prd_loc.get('text_snippet') == '需补充':
                    stats['to_be_filled_items'] += 1

        # Count blockers from Section 9
        for section in sections:
            if section.get('section_type') == 'blockers':
                # Count unchecked items in blocker section
                for line_num in range(section.get('md_line_start', 0), section.get('md_line_end', 0)):
                    if line_num < len(self.lines):
                        line = self.lines[line_num]
                        if '- [ ]' in line and ('章节' in line or 'Section' in line):
                            stats['blockers'] += 1

        return stats

    def generate_index(self) -> Dict[str, Any]:
        """Generate complete index JSON."""
        metadata = self.extract_metadata()
        sections = self.extract_sections()
        operations = self.extract_operations()
        nav_index = self.build_navigation_index(sections, operations)
        stats = self.calculate_statistics(sections, operations)

        # Count total operations
        metadata['total_operations'] = len(operations)
        metadata['total_sections'] = len(sections)

        index = {
            'metadata': metadata,
            'sections': sections,
            'navigation_index': nav_index,
            'statistics': stats
        }

        return index


class ClarificationValidator:
    """Validate clarification.md and clarification_index.json format."""

    def __init__(self, md_file: str, json_file: str):
        self.md_file = Path(md_file)
        self.json_file = Path(json_file)
        self.errors = []
        self.warnings = []

    def validate_metadata(self, index: Dict) -> bool:
        """Validate metadata section."""
        required_fields = ['module_id', 'prd_file', 'prd_section', 'generated_at']
        metadata = index.get('metadata', {})

        for field in required_fields:
            if not metadata.get(field):
                self.errors.append(f"Missing required metadata field: {field}")

        # Validate module_id format
        if metadata.get('module_id') and not re.match(r'^[a-z0-9-]+$', metadata['module_id']):
            self.warnings.append(f"Invalid module_id format: {metadata['module_id']}")

        return len(self.errors) == 0

    def validate_sections(self, index: Dict) -> bool:
        """Validate sections structure."""
        sections = index.get('sections', [])

        if not sections:
            self.errors.append("No sections found")
            return False

        for section in sections:
            # Check required fields
            if not section.get('section_id'):
                self.errors.append("Section missing section_id")
            if not section.get('section_name'):
                self.errors.append("Section missing section_name")

            # Validate line numbers
            if section.get('md_line_start') and section.get('md_line_end'):
                if section['md_line_start'] >= section['md_line_end']:
                    self.errors.append(f"Invalid line range in section {section.get('section_id')}")

        return len(self.errors) == 0

    def validate_navigation_index(self, index: Dict) -> bool:
        """Validate navigation index completeness."""
        nav = index.get('navigation_index', {})

        required_indices = ['by_prd_line', 'by_operation', 'by_section']
        for idx in required_indices:
            if idx not in nav:
                self.errors.append(f"Missing navigation index: {idx}")

        return len(self.errors) == 0

    def validate_consistency(self, index: Dict) -> bool:
        """Validate consistency between sections and navigation."""
        sections = index.get('sections', [])
        operations = [s for s in sections if s.get('section_type') == 'operations']
        nav = index.get('navigation_index', {})

        # Check if all operations are in navigation
        for op_section in operations:
            for op in op_section.get('operations', []):
                op_id = op.get('operation_id')
                if op_id not in nav.get('by_operation', {}):
                    self.errors.append(f"Operation {op_id} not in navigation index")

        return len(self.errors) == 0

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations."""
        if not self.json_file.exists():
            self.errors.append(f"JSON file not found: {self.json_file}")
            return False, self.errors, self.warnings

        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON format: {e}")
            return False, self.errors, self.warnings

        # Run validations
        self.validate_metadata(index)
        self.validate_sections(index)
        self.validate_navigation_index(index)
        self.validate_consistency(index)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


def main():
    """Main entry point."""
    import argparse
    import sys

    # Fix Windows console encoding issue
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='Generate and validate PRD clarification index')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing files')
    parser.add_argument('--md-file', default='../../docs/PRD-Gen/clarification.md', help='Path to clarification.md')
    parser.add_argument('--json-file', default='../../docs/PRD-Gen/clarification_index.json', help='Path to output JSON')

    args = parser.parse_args()

    if args.validate_only:
        print("🔍 Validating clarification format...")
        validator = ClarificationValidator(args.md_file, args.json_file)
        is_valid, errors, warnings = validator.validate()

        if errors:
            print(f"\n❌ Validation failed with {len(errors)} errors:")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print(f"\n⚠️  {len(warnings)} warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        if is_valid:
            print("\n✅ Validation passed!")

        return 0 if is_valid else 1

    else:
        print("📝 Parsing clarification.md...")
        parser_obj = ClarificationParser(args.md_file)

        print("🔨 Generating index...")
        index = parser_obj.generate_index()

        print(f"💾 Writing to {args.json_file}...")
        with open(args.json_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print("\n✅ Generation complete!")
        print(f"   - Sections: {index['statistics']['total_sections']}")
        print(f"   - Operations: {index['statistics']['total_operations']}")
        print(f"   - Scenarios: {index['statistics']['total_scenarios']}")

        # Run validation
        print("\n🔍 Running validation...")
        validator = ClarificationValidator(args.md_file, args.json_file)
        is_valid, errors, warnings = validator.validate()

        if warnings:
            print(f"\n⚠️  {len(warnings)} warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        if is_valid:
            print("\n✅ Validation passed!")
        else:
            print(f"\n❌ Validation found {len(errors)} errors:")
            for error in errors:
                print(f"  - {error}")

        return 0


if __name__ == '__main__':
    exit(main())
