---
name: test-fix
description: "Automatically fix failed test cases with guaranteed correctness"
category: testing
complexity: enhanced
mcp-servers: [playwright]
personas: [qa-specialist, root-cause-analyst]
---

# /test-fix

Automatic test failure analysis and fix with mandatory Playwright validation.

## Command Structure

```bash
/test-fix <result-file> [fix-id]
```

## Key Characteristics

| Aspect | Details |
|--------|---------|
| **Category** | Testing |
| **Complexity** | Enhanced |
| **Primary Personas** | QA Specialist, Root Cause Analyst |
| **MCP Server** | Playwright |

## Arguments

- `result-file` (required): Path to test result JSON file
- `fix-id` (optional): Unique fix session identifier (auto-generated from `caseName` if omitted)

## Usage Examples

```bash
/test-fix test/case_test_result/case.json
/test-fix ./test-results/case.json login-fix-001
```

---

## Operational Flow

The command follows a seven-stage process:

1. **Initialize** - Generate fix-id and create output directory
2. **Parse** - Load test results, screenshots, and source code
3. **Analyze** - Identify root cause with visual evidence
4. **Fix** - Implement targeted code changes
5. **Restart** - Restart service and verify health
6. **Validate** - Execute Playwright validation (MANDATORY)
7. **Verify** - Confirm all output artifacts exist

## Core Capabilities

- Auto-detect test framework and service restart method
- Analyze visual evidence from screenshots
- Generate targeted fixes for root causes
- Execute browser-based validation with Playwright
- Produce structured fix metadata and validation proof

## Tool Integration

- **Read**: Load JSON, screenshots, source files
- **Grep**: Search codebase for bug locations
- **Edit**: Apply targeted code fixes
- **Bash**: Execute service restart commands
- **Playwright MCP**: Execute validation (MANDATORY)
- **TodoWrite**: Track fix progress

## Scope Boundaries

**Included**: Analyzing test failures, implementing fixes, service restart, Playwright validation, artifact generation

**Excluded**: Creating new tests, modifying test framework configuration, skipping validation steps, partial implementations

---

## Input: Test Result JSON Structure

The test result file follows this schema:

```json
{
  "status": "error" | "completed",
  "caseName": "string",
  "testUrl": "http://127.0.0.1:3000/module/feature?id=123",
  "expectedResult": "1. 系统显示「编码已存在」提示\n2. 验证错误提示样式正确",
  "error": "string | null",
  "finalScreenshot": "path/to/image.png",
  "groups": [
    {
      "nodeId": "string",
      "status": "completed" | "error" | "init",
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
| `status` | Overall test result: `error` (failed), `completed` (passed), or `init` (pending - not executed due to prior step failure) |
| `caseName` | Test case name, used as default `fix-id` |
| `testUrl` | Complete test URL (no need for address replacement) |
| `expectedResult` | Expected validation results (multi-line assertions) |
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
├── fix_result.json      # Complete fix metadata (updated incrementally)
├── validation_pass.png  # Screenshot on success
└── validation_fail.png  # Screenshot on failure
```

### fix_result.json Incremental Write Specification

**Rule**: Update `fix_result.json` after EACH phase completion with new data from that phase.

**Phase-to-Data Mapping**:
- **Phase 1 (Parse)**: Write initial → `fixId`, `status: "in_progress"`, `caseName`
- **Phase 2 (Analyze)**: Add → `rootCause` (file, line, description)
- **Phase 3 (Fix)**: Add → `changes[]` (file, description)
- **Phase 4 (Restart)**: (No JSON update required)
- **Phase 5 (Validate)**: Add → `validation` (status, screenshot)
- **Phase 6 (Finalize)**: Update → `status: "success"` or `status: "failed"`

**Complete Schema** (final state):
```json
{
  "fixId": "string",
  "status": "success",
  "caseName": "string",
  "rootCause": {
    "file": "path/to/file.py",
    "line": 145,
    "description": "Clear explanation"
  },
  "changes": [
    {
      "file": "path/to/file.py",
      "description": "What was changed"
    }
  ],
  "validation": {
    "status": "passed",
    "screenshot": "validation_pass.png"
  }
}
```

---

## Workflow

### Phase 0: Initialize

1. Generate or use provided `fix-id`
2. Create output directory: `fix/{fix-id}/`
3. Collect start time for duration calculation

### Phase 1: Parse

**Required Actions:**
- Load test result JSON completely
- Read ALL referenced screenshots
- Read source files in failure path
- Read configuration files (CLAUDE.md, package.json)
- **Record original failure state** for comparison in Phase 5

**Checklist:**
- [ ] Test result JSON loaded (including `error`, `status`, `testUrl`, `expectedResult`)
- [ ] ALL screenshots from `groups[].steps[].screenshot` read
- [ ] `finalScreenshot` read (original failure state)
- [ ] Original error message saved for validation comparison
- [ ] Source code files identified and read
- [ ] Write fix_result.json (initial state)

### Phase 2: Analyze

1. Analyze visual evidence from screenshots
2. Trace failure through execution flow
3. Identify root cause with evidence
4. Document: file, line, type, description
5. Update fix_result.json

### Phase 3: Fix

1. Implement targeted fix for root cause
2. Apply defensive coding practices
3. Follow existing code patterns
4. Track changes
5. Update fix_result.json

**Quality Checklist:**
- [ ] Addresses root cause (not symptoms)
- [ ] No side effects
- [ ] Appropriate error handling
- [ ] No hardcoded workarounds

### Phase 4: Restart Service

**Detection Priority:**
1. Shell scripts: `restart.sh`, `start.sh`, `stop.sh`
2. CLAUDE.md instructions (fallback)

**Search Locations:**
```
./restart.sh, ./start.sh, ./stop.sh
./scripts/restart.sh, ./scripts/start.sh
```

**Steps:**
1. Find and execute restart script
2. Wait 5-10 seconds for service startup
3. Verify service is running
4. Retry up to 3 times on failure

### Phase 5: Validate with Playwright (MANDATORY)

> ⚠️ **CRITICAL**: This phase is NOT optional. Fix is INCOMPLETE without Playwright validation.

**Test URL**:
- Use `testUrl` field directly from test result JSON
- No URL transformation needed - the URL is already correct
- Example: `"testUrl": "http://127.0.0.1:3000/problem-closed-loop-management/problem-type-management"`

**Expected Results**:
- Use `expectedResult` field from test result JSON for validation criteria
- Parse multi-line assertions (e.g., "1. 系统显示「编码已存在」提示\n2. 验证错误提示样式正确")
- Each line represents a validation checkpoint to verify

**Validation Requirements:**
- **MUST follow the exact steps** defined in `groups[].steps[]` from the test result JSON
- Reproduce each step in order: read `stepDescription` and execute corresponding Playwright actions
- Verify each step's expected outcome (element presence, text content, state changes)
- **MUST verify expectedResult** after completing all steps
- If any step or expected result fails, document the failure and capture screenshot
- Capture final screenshot as validation proof

**Steps:**
1. **Read testUrl**: Extract `testUrl` from test result JSON
2. **Navigate using Playwright**: `browser_navigate` to the `testUrl` directly
3. **Execute test steps sequentially**: For each step in `groups[].steps[]`:
   - Read `stepDescription` to understand the action
   - Use appropriate Playwright tools to perform the action (click, fill, evaluate, etc.)
   - Verify the step completed successfully
   - **If step fails**: Capture failure screenshot → go to step 5 for analysis
   - If step has `screenshot`, optionally compare with original for reference
4. **Verify expectedResult**: After all steps complete:
   - Parse `expectedResult` into individual assertions
   - Verify each assertion using Playwright (check text, element state, etc.)
   - **If any assertion fails**: Document which assertion failed → go to step 5
5. **On validation failure** (any step or assertion fails):
   - **Capture failure screenshot** with timestamp
   - **Collect logs**:
     - Browser console: `playwright_console_logs` (errors, warnings, console.log)
     - Network logs: Failed API requests, status codes, response bodies
     - Backend logs: `./logs/`, `./backend/logs/`, service errors
   - **Test failed API directly** (if network error detected):
     - Extract failed API endpoint from network logs
     - Use `curl` to test API independently: `curl -X POST http://... -H "..." -d "..."`
     - Verify API response status, headers, body
     - Confirm if issue is API-level or frontend integration
   - **Compare with original failure**:
     - Read original error from test result JSON
     - Check if current failure is same as original
     - Verify fix actually addressed the root cause
   - **Check for new issues introduced**:
     - Compare current screenshot with original `finalScreenshot`
     - Look for regression: new errors not in original test
     - Verify no side effects from the fix
   - **Identify failure type**:
     - UI: Element not found, selector changed, timing issue
     - Backend API: API error, service crash, endpoint failure (confirmed via curl)
     - Data: Validation error, state mismatch
     - Network: Timeout, connection refused
   - **Analyze fix effectiveness**:
     - If same error → Fix incomplete, needs different approach
     - If new error → Fix caused regression, need rollback + new fix
     - If progress made → Partial fix, continue iteration
   - **Document in fix_result.json**: Failure type, error message, log excerpts, API test results, suspected cause, comparison with original
   - **Decision**:
     - Same error as original → Fix failed, try different approach in **Phase 3**
     - New error (regression) → Rollback fix, analyze side effects, return to **Phase 3**
     - Intermittent failure → Retry with same fix (increment `retryCount`)
     - `retryCount >= 3` → Phase 6 with failure status + detailed diagnosis
   - Return to **Phase 4: Restart** → **Phase 5: Validate** (retry)
6. **On validation success** (all steps and assertions pass):
   - Track validation results: Count total steps, passed steps, failed steps
   - Capture screenshot for fixed success cases: `browser_snapshot` → `fix/{fix-id}/validation_pass.png`
   - Update fix_result.json
   - Proceed to Phase 6

### Phase 6: Finalize

**Steps:**
1. Update fix_result.json with final status ("success" or "failed")

### Phase 7: Verify Output (MANDATORY)

**Required Files:**
- [ ] `fix/{fix-id}/fix_result.json` - exists and valid JSON
- [ ] `fix/{fix-id}/validation_*.png` - exists and non-empty

> Fix is INCOMPLETE if any file is missing.

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


------

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
9. Output verification passed

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
4. Verify all output files exist
5. Document failure reason

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

### Failure Analysis
- **Check logs**: Browser console, network, backend
- **Identify source**: UI, backend, data, or network issue
- **Collect evidence**: Error messages, stack traces, API responses, log excerpts

### Fix Quality
- Prefer specific fixes over broad changes
- Add defensive checks
- Follow existing code conventions

---

## Principles

1. **Read EVERYTHING** - All test files, screenshots, source code, original error
2. **Fix COMPLETELY** - No partial implementations
3. **Restart ALWAYS** - Service must restart before validation
4. **Validate with Playwright** - MANDATORY, no exceptions
5. **Compare with Original** - Always check if fix resolved original error
6. **Check for Regressions** - Ensure fix didn't introduce new issues
7. **Collect ALL Logs** - Browser, network, backend on failure
8. **Smart Retry Logic** - Different approach if same error persists
9. **Write Incrementally** - Update fix_result.json after each phase completion (Parse→Analyze→Fix→Restart→Validate→Finalize)
10. **Prove with Artifacts** - Save all output files
11. **Verify Output** - Check files exist before completing
12. **Pass ALL Steps** - Every step must succeed

---

## Quick Reference

### Command Invocation
```bash
# Basic usage (auto-generate fix-id)
/test-fix test/case_test_result/case.json

# With custom fix-id
/test-fix ./test-results/case.json my-fix-001
```

### Output Location
```
fix/{fix-id}/
├── fix_result.json      # Fix metadata
├── validation_pass.png  # Success screenshot
└── validation_fail.png  # Failure screenshot (if failed)
```

### Phase Checklist
- [ ] **Parse**: Load JSON, screenshots, source code → Write initial fix_result.json
- [ ] **Analyze**: Identify root cause → Update rootCause in JSON
- [ ] **Fix**: Implement changes → Update changes[] in JSON
- [ ] **Restart**: Service restart → Verify health
- [ ] **Validate**: Playwright execution → Update validation in JSON
- [ ] **Finalize**: Update final status → success/failed
- [ ] **Verify**: Confirm all artifacts exist

### Common Failure Patterns
| Pattern | Root Cause Type | Fix Approach |
|---------|----------------|--------------|
| Code Logic Error | Logic error | Source location fix |
| UI Interaction Failure | Selector error | Fix component selector |
| Missing Validation | Missing validation | Add validation logic |
| Race Condition | Race condition | Add synchronization |
