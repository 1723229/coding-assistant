---
name: test-fix
description: "Automatically fix failed test cases with guaranteed correctness"
category: testing
complexity: enhanced
mcp-servers: [playwright]
personas: [root-cause-analyst]
---

# /test-fix

Automatic test failure analysis and fix with mandatory Playwright validation.

## Usage

```bash
/test-fix <result-file> [fix-id]
```

**Arguments:**
- `result-file` (required): Path to test result JSON file
- `fix-id` (optional): Unique fix session identifier (auto-generated from `caseName` if omitted)

**Examples:**
```bash
/test-fix test/case_test_result/case.json
/test-fix ./test-results/case.json login-fix-001
```

---

## Input: Test Result JSON Structure

The test result file follows this schema:

```json
{
  "status": "error" | "completed",
  "caseName": "string",
  "error": "string | null",
  "finalScreenshot": "path/to/image.png",
  "groups": [
    {
      "nodeId": "string",
      "status": "completed" | "error",
      "objective": "string",
      "error": "string | null",
      "steps": [
        {
          "stepId": "string",
          "status": "completed" | "error",
          "stepDescription": "string",
          "actionTime": 1766738700722,
          "error": "string | null",
          "screenshot": "static/0.png"
        }
      ]
    }
  ]
}
```

**Field Descriptions:**
| Field | Description |
|-------|-------------|
| `status` | Overall test result: `error` (failed) or `completed` (passed) |
| `caseName` | Test case name, used as default `fix-id` |
| `error` | Top-level error message (null if passed) |
| `finalScreenshot` | Path to final state screenshot |
| `groups` | Ordered list of test groups (objectives) |
| `groups[].objective` | What this group aims to accomplish |
| `groups[].steps` | Individual actions within the group |
| `groups[].steps[].screenshot` | Screenshot after this step |

---

## Output: Fix Artifacts

All artifacts are written to `fix/{fix-id}/`:

```
fix/{fix-id}/
├── fix_result.json      # Complete fix metadata
├── validation_pass.png  # Screenshot on success
├── validation_fail.png  # Screenshot on failure
└── fix_note.md          # Human-readable report
```

---

## Workflow

### Phase 0: Initialize

1. Generate or use provided `fix-id`
2. Create output directory: `fix/{fix-id}/`
3. Initialize `fix_result.json`: status `"in_progress"`, all phases `"pending"`

**Phase Update Rules**:
- Each phase start → `"phase_name": "in_progress"`
- Each phase complete → `"phase_name": "completed"` + add phase data
- On failure → `"phase_name": "failed"` + error details

### Phase 1: Parse

**Required Actions:**
- Load test result JSON completely
- Read ALL referenced screenshots
- Read source files in failure path
- Read configuration files (CLAUDE.md, package.json)

**Checklist:**
- [ ] Test result JSON loaded
- [ ] ALL screenshots from `groups[].steps[].screenshot` read
- [ ] `finalScreenshot` read
- [ ] Source code files identified and read

### Phase 2: Analyze

1. Analyze visual evidence from screenshots
2. Trace failure through execution flow
3. Identify root cause with evidence
4. Document: file, line, type, description
5. Add `rootCause` to fix_result.json

**Analysis Output:**
```json
{
  "rootCause": {
    "file": "path/to/file.py",
    "line": 145,
    "type": "missing_validation | logic_error | selector_error | race_condition",
    "description": "Clear explanation of the bug"
  }
}
```

### Phase 3: Classify

**Auto-Fixable (Implementation Bugs):**
- Logic errors
- Incorrect UI selectors
- Missing validation
- Race conditions
- Data transformation errors
- State management issues

**Not Fixable (Report Only):**
- Hardware/OS limitations
- API restrictions
- Third-party service limitations
- Business rule violations

### Phase 4: Fix

1. Implement targeted fix for root cause
2. Apply defensive coding practices
3. Follow existing code patterns
4. Add `changes` array to fix_result.json

**Quality Checklist:**
- [ ] Addresses root cause (not symptoms)
- [ ] No side effects
- [ ] Appropriate error handling
- [ ] No hardcoded workarounds

### Phase 5: Restart Service

**Detection Priority:**
1. CLAUDE.md instructions
2. Shell scripts: `restart.sh`, `start.sh`, `stop.sh`
3. npm scripts in `package.json`

**Search Locations:**
```
./restart.sh, ./start.sh, ./stop.sh, ./scripts/, ./bin/, ./frontend/, ./backend/, package.json
```

**Steps:**
1. Detect restart method
2. Execute restart command
3. Wait for service health check
4. Retry up to 3 times on failure

### Phase 6: Validate with Playwright (MANDATORY)

> ⚠️ **CRITICAL**: This phase is NOT optional. Fix is INCOMPLETE without Playwright validation.

**Base URL Configuration**:
- Always use `127.0.0.1:{port}` (default port: `3000`)
- **IMPORTANT**: Preserve full path from original test URL
- Example: `http://172.27.1.44:20001/page1` → `http://127.0.0.1:3000/page1`

**Required MCP Tools:**
- `browser_navigate` - Navigate to URL
- `browser_snapshot` - Get page accessibility tree
- `browser_click` - Click elements
- `browser_type` - Type into inputs
- `browser_take_screenshot` - Capture proof

**Steps:**
1. Navigate to `http://127.0.0.1:3000{path}` (extract path from original test URL)
2. Reproduce EXACT test scenario from `groups[].steps`
3. Verify each step passes
4. Capture screenshot: `fix/{fix-id}/validation_pass.png` or `validation_fail.png`
5. Add `validation` results to fix_result.json

### Phase 7: Generate Reports

**Final fix_result.json requirements:**
- All phases have final status (completed/failed)
- `rootCause`, `changes`, `validation` sections complete
- Add `endTime`, `duration`, final `status`
- Add `outputVerification` section

**fix_result.json:**
```json
{
  "fixId": "string",
  "status": "success" | "failed",
  "startTime": "ISO timestamp",
  "endTime": "ISO timestamp",
  "duration": "2m 15s",
  "sourceFile": "path/to/case.json",
  "caseName": "string",
  "phases": {
    "parse": "completed",
    "analyze": "completed",
    "fix": "completed",
    "restart": "completed",
    "validate": "completed",
    "verify_output": "completed"
  },
  "rootCause": {
    "file": "path/to/file.py",
    "line": 145,
    "type": "missing_validation",
    "description": "Description"
  },
  "changes": [
    {
      "file": "path/to/file.py",
      "type": "modification",
      "linesChanged": 5,
      "description": "What was changed"
    }
  ],
  "validation": {
    "status": "passed" | "failed",
    "stepsTotal": 5,
    "stepsPassed": 5,
    "screenshot": "fix/{fix-id}/validation_pass.png",
    "playwrightUsed": true
  },
  "outputVerification": {
    "fix_result.json": true,
    "validation_screenshot": true,
    "fix_note.md": true,
    "allFilesPresent": true
  },
  "retryCount": 0
}
```

**fix_note.md:**
```markdown
# Fix Report: {fix-id}

## Summary
- **Status**: SUCCESS | FAILED
- **Duration**: 2m 15s
- **Case**: {caseName}

## Root Cause
- **File**: path/to/file.py:145
- **Issue**: Description
- **Impact**: Impact description

## Changes Made
1. **file.py** - What was changed

## Validation
- **Method**: Playwright MCP
- **Result**: PASSED (5/5 steps)
- **Screenshot**: validation_pass.png
```

### Phase 8: Verify Output (MANDATORY)

**Required Files:**
- [ ] `fix/{fix-id}/fix_result.json` - exists and valid JSON
- [ ] `fix/{fix-id}/validation_*.png` - exists and non-empty
- [ ] `fix/{fix-id}/fix_note.md` - exists and non-empty

> Fix is INCOMPLETE if any file is missing.

---

## fix_result.json Update Workflow

**CRITICAL**: Update at EVERY phase transition for real-time progress tracking.

### Update Pattern:

**Phase Lifecycle:**
- Start: `"phase_name": "in_progress"`
- Complete: `"phase_name": "completed"` + phase data
- Failed: `"phase_name": "failed"` + error

**Phase Data to Add:**
- Analyze → `rootCause`
- Fix → `changes[]`
- Validate → `validation`
- Verify → `outputVerification`, final `status`, `endTime`, `duration`

---

## Error Recovery

### Retry Configuration

```json
{
  "maxRetries": 3,
  "retryDelayMs": 5000,
  "backoffMultiplier": 2
}
```

### Error Classification

**Transient (Auto-Retry):**
- Network timeouts
- Service not ready
- Browser automation glitches
- Port conflicts

**Permanent (Abort):**
- Syntax errors
- Missing dependencies
- Permission denied
- Test logic failure

### Recovery by Phase

| Phase | On Failure | Action |
|-------|------------|--------|
| Parse | Retry 3x | Report & abort |
| Analyze | Retry 3x | Report & abort |
| Fix | Report | Abort with diagnosis |
| Restart | Retry 3x | Report & abort |
| Validate | Retry 3x | Capture failure screenshot |
| Verify | Generate | Create missing files |

---

## Fix Patterns


### Pattern 1: Code Logic Error
```
Error Analysis → Source Location → Fix → Restart → Playwright Validate
```

### Pattern 2: UI Interaction Failure
```
Screenshot Analysis → Selector Issue → Fix Component → Restart → Playwright Validate
```

### Pattern 3: Missing Validation
```
Validation Gap → Add Logic → Restart → Playwright Validate
```

### Pattern 4: Race Condition
```
Timing Issue → Add Synchronization → Restart → Playwright Validate
```


---

## Tool Coordination

| Tool | Purpose |
|------|---------|
| Read | Load JSON, screenshots, source files |
| Grep | Search codebase for bug locations |
| Edit | Apply targeted code fixes |
| Bash | Execute service restart commands |
| Playwright MCP | Execute validation (MANDATORY) |
| TodoWrite | Track fix progress |

---

## Success Criteria

**Fix is COMPLETE when ALL are true:**
1. All related files read
2. Root cause identified with evidence
3. Complete fix applied
4. Service restarted
5. Playwright validation executed
6. All test steps passed (or failure documented)
7. `fix_result.json` exists and valid
8. `validation_*.png` exists
9. `fix_note.md` exists
10. Output verification passed

**Fix is INCOMPLETE if ANY occurs:**
- Skipped reading files
- Partial fix implementation
- Service not restarted
- Playwright validation NOT executed
- Output files missing
- Any step skipped

---

## Validation Failure Handling

1. Retry up to 3 times with exponential backoff
2. Capture failure screenshot: `validation_fail.png`
3. Update `fix_result.json` with failure details
4. Generate `fix_note.md` with diagnosis
5. Verify all output files exist
6. Document failure reason

---

## Best Practices

### Screenshot Analysis
- Compare before/after states
- Look for UI state inconsistencies
- Verify error messages match expectations

### Service Restart
- Verify health after restart
- Check logs for errors
- Wait for full initialization

### Playwright Validation
- Wait for elements before interacting
- Verify intermediate states
- Capture proof screenshots

### Fix Quality
- Prefer specific fixes over broad changes
- Add defensive checks
- Follow existing code conventions

---

## Principles

1. **Read EVERYTHING** - All test files, screenshots, source code
2. **Fix COMPLETELY** - No partial implementations
3. **Restart ALWAYS** - Service must restart before validation
4. **Validate with Playwright** - MANDATORY, no exceptions
5. **Update fix_result.json** - EVERY phase transition must update the file
6. **Recover on Failure** - Auto-retry transient errors
7. **Prove with Artifacts** - Save all 3 output files
8. **Verify Output** - Check files exist before completing
9. **Pass ALL Steps** - Every step must succeed
