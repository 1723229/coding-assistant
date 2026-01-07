# -*- coding: utf-8 -*-
"""
Test Service - Batch process test case archives and trigger fix workflows.

This standalone script provides two-phase execution:

PHASE 1 (Prepare):
1. Extracts all ZIP files in a directory (skips already extracted)
2. Finds all case.json files with status="error"
3. Replaces testUrl in case.json files

PHASE 2 (Execute):
1. Triggers fix workflow via external API for each error case
2. Processes SSE stream responses
3. Reports success/failure statistics

Usage:
    # Run both phases (default)
    python backend/app/core/test_service.py /path/to/test/cases

    # Run Phase 1 only (prepare)
    python backend/app/core/test_service.py /path/to/test/cases prepare

    # Run Phase 2 only (execute)
    python backend/app/core/test_service.py /path/to/test/cases execute
"""

import json
import logging
import sys
import uuid
import zipfile
from pathlib import Path
from typing import List

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://172.27.1.44:10099/api/tasks/stream"
WORKSPACE_PATH = "/workspace"
OLD_TEST_URL = "http://47.97.84.212:3000"
NEW_TEST_URL = "http://127.0.0.1:3000"


def unzip_all(base_dir: Path) -> int:
    """
    Extract all ZIP files in directory tree.
    Skips extraction if folder with same name already exists.
    
    Args:
        base_dir: Root directory to scan for ZIP files
        
    Returns:
        Number of archives extracted
    """
    extracted_count = 0
    
    for zip_path in base_dir.rglob("*.zip"):
        # Target folder: same name without .zip extension
        target_dir = zip_path.with_suffix("")
        
        if target_dir.exists():
            logger.info(f"Skip (already extracted): {zip_path.name}")
            continue
        
        try:
            logger.info(f"Extracting: {zip_path.name}")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(target_dir)
            extracted_count += 1
            logger.info(f"  -> Extracted to: {target_dir}")
        except zipfile.BadZipFile:
            logger.error(f"  -> Failed (bad zip): {zip_path}")
        except Exception as e:
            logger.error(f"  -> Failed: {zip_path} - {e}")
    
    return extracted_count


def find_error_cases(base_dir: Path) -> List[Path]:
    """
    Find all case.json files with status="error".
    
    Args:
        base_dir: Root directory to scan
        
    Returns:
        List of paths to error case.json files
    """
    error_cases = []
    
    for case_path in base_dir.rglob("case.json"):
        try:
            with open(case_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("status") == "error":
                error_cases.append(case_path)
                logger.info(f"Found error case: {case_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {case_path}")
        except Exception as e:
            logger.error(f"Failed to read: {case_path} - {e}")
    
    return error_cases


def replace_test_url(case_path: Path) -> bool:
    """
    Replace testUrl value in case.json.
    Replaces http://47.97.84.212:3000 with http://127.0.0.1:3000
    
    Args:
        case_path: Path to case.json file
        
    Returns:
        True if replacement was made, False otherwise
    """
    try:
        with open(case_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if OLD_TEST_URL not in content:
            return False
        
        new_content = content.replace(OLD_TEST_URL, NEW_TEST_URL)
        
        with open(case_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"  Replaced testUrl in: {case_path.name}")
        return True
    except Exception as e:
        logger.error(f"  Failed to replace testUrl: {case_path} - {e}")
        return False


def trigger_fix(base_dir: Path, case_path: Path) -> bool:
    """
    Call external API to trigger fix workflow.
    
    Args:
        base_dir: Base directory for calculating relative path
        case_path: Path to case.json file
        
    Returns:
        True if API call succeeded, False otherwise
    """
    session_id = str(uuid.uuid4())
    
    # Calculate relative path from base directory
    try:
        relative_path = case_path.relative_to(base_dir)
    except ValueError:
        # Fallback if case_path is not under base_dir
        relative_path = case_path
    print(f"ffff---{relative_path}")
    prompt = f"/test-fix D1组建团队/{relative_path} {session_id}"

    payload = {
        "session_id": session_id,
        "workspace_path": WORKSPACE_PATH,
        "prompt": prompt
    }
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    logger.info(f"  Triggering fix: {relative_path}")
    logger.info(f"    session_id: {session_id}")
    logger.info(f"    fix_id: {session_id}")
    
    try:
        # 使用 stream=True 启用流式响应
        response = requests.post(API_URL, headers=headers, json=payload, timeout=1800, stream=True)

        if response.status_code == 200:
            logger.info(f"  -> API call succeeded, processing stream...")

            # 处理 SSE 流式响应
            success = False
            error_occurred = False

            for line in response.iter_lines():
                if not line:
                    continue

                # 解码并解析 SSE 格式: "data: {...}"
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # 去掉 "data: " 前缀
                    try:
                        event = json.loads(data_str)

                        event_type = event.get('type', '')

                        # 记录关键事件
                        if event_type == 'connected':
                            logger.info("    -> Connected to stream")
                        elif event_type == 'text' or event_type == 'text_delta':
                            content = event.get('content', '')
                            if content:
                                logger.info(f"    -> Response: {content[:100]}...")
                        elif event_type == 'response_complete':
                            logger.info("    -> Response complete")
                            success = True
                        elif event_type == 'error':
                            error_msg = event.get('content', 'Unknown error')
                            logger.error(f"    -> Error in stream: {error_msg}")
                            error_occurred = True

                    except json.JSONDecodeError:
                        logger.warning(f"    -> Failed to parse SSE data: {data_str[:100]}")

            if error_occurred:
                logger.error("  -> Stream completed with errors")
                return False
            elif success:
                logger.info("  -> Stream completed successfully")
                return True
            else:
                logger.warning("  -> Stream ended without completion signal")
                return True  # 假设成功，因为没有明确的错误
        else:
            logger.error(f"  -> API call failed: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.Timeout:
        logger.error("  -> API call timeout")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"  -> API call error: {e}")
        return False


def prepare_cases(base_dir: str) -> List[Path]:
    """
    Phase 1: Prepare test cases (extract + replace URLs).

    This function:
    1. Extracts all ZIP files
    2. Finds error cases
    3. Replaces testUrl in case.json files

    Args:
        base_dir: Path to directory containing test cases

    Returns:
        List of prepared case.json paths
    """
    base_path = Path(base_dir).resolve()

    if not base_path.exists():
        logger.error(f"Directory does not exist: {base_path}")
        sys.exit(1)

    if not base_path.is_dir():
        logger.error(f"Path is not a directory: {base_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("PHASE 1: PREPARE TEST CASES")
    logger.info(f"Processing: {base_path}")
    logger.info("=" * 60)

    # Step 1: Extract all ZIP files
    logger.info("\n[Step 1] Extracting ZIP files...")
    extracted = unzip_all(base_path)
    logger.info(f"Extracted {extracted} archive(s)")

    # Step 2: Find error cases
    logger.info("\n[Step 2] Finding error cases...")
    error_cases = find_error_cases(base_path)
    logger.info(f"Found {len(error_cases)} error case(s)")

    if not error_cases:
        logger.info("No error cases to process.")
        return []

    # Print all error cases
    logger.info("\n[Error Cases]")
    for i, case_path in enumerate(error_cases, 1):
        logger.info(f"  {i}. {case_path}")

    # Step 3: Replace testUrl in all cases
    logger.info("\n[Step 3] Replacing testUrl in case.json files...")
    replaced_count = 0
    for case_path in error_cases:
        if replace_test_url(case_path):
            replaced_count += 1

    logger.info(f"Replaced testUrl in {replaced_count} file(s)")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 1 COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Total error cases: {len(error_cases)}")
    logger.info(f"  URLs replaced: {replaced_count}")
    logger.info("=" * 60)

    return error_cases


def execute_fixes(base_dir: str, case_paths: List[Path]) -> None:
    """
    Phase 2: Execute fix workflows via API.

    This function triggers the fix workflow for each prepared case.

    Args:
        base_dir: Base directory for calculating relative paths
        case_paths: List of case.json paths to process
    """
    base_path = Path(base_dir).resolve()

    if not case_paths:
        logger.info("No cases to execute.")
        return

    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: EXECUTE FIX WORKFLOWS")
    logger.info(f"Processing {len(case_paths)} case(s)")
    logger.info("=" * 60)

    success_count = 0

    for i, case_path in enumerate(case_paths, 1):
        logger.info(f"\n--- Executing [{i}/{len(case_paths)}]: {case_path.parent.name} ---")

        if trigger_fix(base_path, case_path):
            success_count += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2 COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Total cases: {len(case_paths)}")
    logger.info(f"  API calls succeeded: {success_count}")
    logger.info(f"  API calls failed: {len(case_paths) - success_count}")
    logger.info("=" * 60)


def main(base_dir: str, mode: str = "all") -> None:
    """
    Main orchestration function.

    Args:
        base_dir: Path to directory containing test cases
        mode: Execution mode - "prepare", "execute", or "all" (default)
    """
    if mode == "prepare":
        # Phase 1 only: Extract and replace
        prepare_cases(base_dir)

    elif mode == "execute":
        # Phase 2 only: Execute fixes (assumes preparation is done)
        base_path = Path(base_dir).resolve()
        error_cases = find_error_cases(base_path)
        execute_fixes(base_dir, error_cases)

    else:
        # Both phases: Complete workflow
        error_cases = prepare_cases(base_dir)
        if error_cases:
            execute_fixes(base_dir, error_cases)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_service.py <base_directory> [mode]")
        print("")
        print("Modes:")
        print("  all      - Run both phases (default)")
        print("  prepare  - Phase 1 only: Extract ZIPs and replace URLs")
        print("  execute  - Phase 2 only: Execute fix workflows via API")
        print("")
        print("Examples:")
        print("  python test_service.py /path/to/cases")
        print("  python test_service.py /path/to/cases prepare")
        print("  python test_service.py /path/to/cases execute")
        sys.exit(1)

    base_directory = sys.argv[1]
    execution_mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    if execution_mode not in ["all", "prepare", "execute"]:
        print(f"Invalid mode: {execution_mode}")
        print("Valid modes: all, prepare, execute")
        sys.exit(1)

    main(base_directory, execution_mode)

