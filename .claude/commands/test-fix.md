---
name: test-fix
description: "Automatically fix failed test cases with guaranteed correctness"
category: testing
complexity: enhanced
mcp-servers: [playwright]
personas: [root-cause-analyst]
---

# /test-fix - Automatic Test Failure Fix

## Purpose
**Core Mission**: Automatically analyze and fix failed test cases with guaranteed correctness through validation.

## Triggers
- Test case result files (JSON format with groups, steps, errors)
- Failed test scenarios requiring immediate correction
- UI/UX workflow failures with screenshots
- Integration test failures

## Usage
```
/test-fix <result-file>
```

## Auto-Fix Workflow

**CRITICAL REQUIREMENTS - NO SHORTCUTS ALLOWED:**
- ✅ Read ALL related files (test cases, screenshots, source code)
- ✅ Reproduce the complete failure workflow
- ✅ Mandatory Playwright validation with screenshot proof
- ✅ 100% completion required - NO skipping steps
- ❌ NEVER skip, ignore, or partially complete any step

**Step-by-Step Process:**

1. **Parse & Read ALL Related Files** (MANDATORY):
   - Load test result JSON completely
   - Read ALL screenshots referenced in test results
   - Read test case definition files
   - Read reproduction workflow documentation
   - Read all source files involved in the failure
   - Extract complete failure context (no shortcuts)

2. **Analyze**: Deep root cause analysis of failure patterns
   - Analyze visual evidence from screenshots
   - Trace failure through complete execution flow
   - Document root cause with evidence

3. **Diagnose**: Identify fixable bugs vs system constraints
   - Distinguish implementation bugs from system limits
   - Confirm bug is within fix scope

4. **Fix**: Apply code changes to resolve issues
   - Implement targeted fix for root cause
   - No partial fixes - complete resolution only

5. **Restart Service** (MANDATORY):
   - Read project CLAUDE.md for service restart instructions
   - Search for restart/stop/start scripts in project
   - Execute appropriate restart command before testing
   - Verify service is running before validation

6. **Validate with Playwright** (MANDATORY - NO EXCEPTIONS):
   - Use Playwright MCP to perform page-level testing
   - Execute FULL UI workflow validation (no shortcuts)
   - Reproduce EXACT test scenario from original failure
   - Capture screenshot and save as `validation_pass.png`
   - Verify ALL steps pass successfully
   - **FAILURE TO VALIDATE = FIX NOT COMPLETE**

7. **Report**: Summary of fixes applied and validation results
   - Document fix implementation
   - Provide screenshot proof (`validation_pass.png`)
   - Confirm 100% completion of all steps

## Key Behaviors

**Mandatory File Reading (NO EXCEPTIONS):**
- ✅ Read complete test result JSON with all nested data
- ✅ Read EVERY screenshot file referenced in test results
- ✅ Read ALL source code files involved in failure path
- ✅ Read test case definitions and workflow documentation
- ✅ Read project configuration files (CLAUDE.md, package.json, etc.)

**Analysis Requirements:**
- Parse hierarchical test results (groups → objectives → steps)
- Analyze Chinese/English error messages
- **Visual screenshot analysis for UI state understanding (MANDATORY)**
- Trace complete execution flow from screenshots
- Distinguish fixable bugs from system constraints

**Fix Implementation:**
- Apply fixes ONLY for implementation bugs
- **No partial fixes - complete resolution required**
- **Auto-detect service restart method**:
  - Check CLAUDE.md for restart instructions
  - Search for start.sh/stop.sh/restart.sh scripts
  - Use package.json scripts (npm start/restart)
  - Execute restart before validation

**Mandatory Validation (100% REQUIRED - NO SHORTCUTS):**
- ✅ **Playwright page-level testing after EVERY fix**
- ✅ **Full UI workflow execution (reproduce exact scenario)**
- ✅ **Screenshot capture saved as `validation_pass.png`**
- ✅ **Visual regression verification**
- ✅ **ALL test steps must pass - no partial success**
- ❌ **Fix is INCOMPLETE without Playwright validation proof**

**Guarantee correctness: Fix is ONLY complete when:**
1. Code changes applied ✅
2. Service restarted successfully ✅
3. Playwright validation passes ✅
4. Screenshot proof saved (`validation_pass.png`) ✅
5. NO steps skipped ✅

## MCP Integration
- **Playwright MCP**: Re-execute test scenarios for validation
- **Root Cause Analyst**: Systematic bug investigation

## Tool Coordination
- **Read**: Load test result JSON, screenshots, and source files
- **Grep**: Search codebase for bug locations
- **Edit**: Apply targeted code fixes
- **Bash**: Re-run tests for validation
- **TodoWrite**: Track fix progress

## Test Result Structure Expected

```json
{
  "status": "error" | "completed",
  "groups": [
    {
      "nodeId": "string",
      "status": "completed" | "error",
      "objective": "string (Chinese/English)",
      "error": "string | null",
      "steps": [
        {
          "stepId": "string",
          "status": "completed" | "error",
          "stepDescription": "string",
          "actionTime": "timestamp",
          "error": "string | null",
          "screenshot": "path/to/image.png"
        }
      ]
    }
  ],
  "error": "string | null",
  "finalScreenshot": "path/to/image.png",
  "caseName": "string"
}
```

## Fix Categories

### 1. Implementation Bugs (Auto-Fixable)
- Logic errors in code
- Incorrect UI selectors
- Missing validation
- Race conditions
- Incorrect error handling

### 2. System Constraints (Skip - Report Only)
- Hardware/OS limitations
- API restrictions
- Third-party service limitations
- Business rule violations

## Auto-Fix Patterns

### Pattern 1: Code Logic Error
```
Error indicates bug → Locate source → Analyze root cause → Apply fix → Restart service → Playwright validation
```

### Pattern 2: UI Interaction Failure
```
Screenshot shows issue → Identify selector/state problem → Fix component → Restart service → Playwright re-test
```

### Pattern 3: Validation Missing
```
Error shows validation gap → Add validation logic → Restart service → Playwright validation
```

## Service Restart Detection Strategy

**Priority Order:**
1. **CLAUDE.md**: Check for service management instructions
2. **Shell Scripts**: Search for restart.sh, start.sh, stop.sh
3. **Package.json**: Check for npm scripts (start, restart, dev)
4. **Docker**: Look for docker-compose.yml or Dockerfile
5. **Process Managers**: Check for PM2, systemd, supervisord configs

**Search Locations:**
- Project root: `./restart.sh`, `./start.sh`, `./stop.sh`
- Scripts directory: `./scripts/`, `./bin/`, `./tools/`
- Backend directory: `./backend/`, `./server/`
- Configuration: `package.json`, `docker-compose.yml`

## Fix Workflow Example

```
/test-fix assets/case_test_result/failed_test.json

Output:
📖 Reading ALL related files... (MANDATORY)
   ✅ Loaded: failed_test.json (complete structure)
   ✅ Read: screenshot_step1.png (visual analysis)
   ✅ Read: screenshot_error.png (failure state)
   ✅ Read: test_case_definition.json (workflow)
   ✅ Read: backend/app/auth.py (source code)
   ✅ Complete file reading - NO files skipped

📋 Analyzing test results...
❌ Found 1 fixable bug in login validation

🔍 Root Cause:
   File: backend/app/auth.py:145
   Issue: Password length check missing
   Evidence: Screenshot shows validation bypass

🔧 Applying fix...
   ✅ Added validation: len(password) >= 8
   ✅ Complete fix implementation - NO shortcuts

🔄 Restarting service... (MANDATORY)
   📖 Reading CLAUDE.md for restart instructions
   🔍 Searching for restart scripts: restart.sh, start.sh, stop.sh
   ✅ Found: ./scripts/restart.sh
   ⚡ Executing: bash ./scripts/restart.sh
   ✅ Service restarted successfully
   ✅ Verified service running on port xxxx

🎭 Validating with Playwright... (MANDATORY - NO EXCEPTIONS)
   🌐 Launching browser automation
   📸 Executing FULL UI test workflow (exact reproduction)
   ✅ Page loaded: http://localhost:xxxx/login
   ✅ Step 1: Enter username - PASS
   ✅ Step 2: Enter short password - PASS (validation triggered)
   ✅ Step 3: Validation error shown - PASS
   ✅ Step 4: Enter valid password - PASS
   ✅ Step 5: Login flow completed - PASS
   📸 Screenshot captured and saved: validation_pass.png
   ✅ Visual verification: ALL steps passed

📊 Summary:
   - Files read: 5/5 (100% - NO files skipped)
   - Bugs fixed: 1/1 (100% complete)
   - Service restarted: ✅ SUCCESS
   - Playwright validation: ✅ PASS (ALL steps)
   - Screenshot proof: ✅ validation_pass.png saved
   - Steps completed: 7/7 (100% - NO steps skipped)
   - Fix status: ✅ COMPLETE (fully validated)
   - Time: 18.7s
```

## Correctness Guarantees

**Pre-Fix Safety:**
- ✅ Read ALL files completely (test results, screenshots, source code, configs)
- ✅ Root cause identified with evidence from visual and code analysis
- ✅ Fix scope limited to bug location
- ✅ No regression risk assessed
- ✅ Rollback strategy prepared

**Post-Fix Validation (MANDATORY - NO EXCEPTIONS):**
- ✅ **Read ALL related files first** (REQUIRED)
  - Test result JSON (complete structure)
  - ALL screenshots referenced
  - Test case definitions
  - Source code files
  - Configuration files
- ✅ **Detect and execute service restart** (REQUIRED)
  - Read CLAUDE.md for instructions
  - Search for restart/start/stop scripts
  - Execute restart before testing
  - Verify service is running
- ✅ **Playwright page-level testing** (REQUIRED for ALL fixes - NO EXCEPTIONS)
  - Full UI workflow execution
  - Browser automation with real user interactions
  - **Reproduce EXACT test scenario from failure**
  - **Visual screenshot comparison**
  - **Save screenshot as `validation_pass.png`**
  - **ALL steps must pass - no partial success**
- ✅ Re-run failed test case with Playwright
- ✅ Run related test suite
- ✅ Verify no new errors introduced

**Success Criteria (ALL MUST BE MET - NO SHORTCUTS):**
1. ✅ All related files read completely
2. ✅ Root cause identified with evidence
3. ✅ Complete fix applied (no partial fixes)
4. ✅ Service restarted successfully
5. ✅ Playwright validation executed
6. ✅ ALL test steps passed
7. ✅ Screenshot proof saved (`validation_pass.png`)
8. ✅ No steps skipped or ignored

**Failure Conditions (Fix is INCOMPLETE if ANY occurs):**
- ❌ Skipped reading any related files
- ❌ Did not analyze all screenshots
- ❌ Partial fix implementation
- ❌ Service not restarted
- ❌ Playwright validation not executed
- ❌ Playwright validation failed
- ❌ Screenshot proof not saved
- ❌ Any step skipped or ignored

**Action on Failure:**
- Report failure clearly
- Preserve original code if uncertain
- **NEVER mark fix as complete without Playwright validation passing**
- **NEVER skip validation steps**


---

**Core Principle**:

**NO SHORTCUTS. NO SKIPPING. 100% COMPLETION REQUIRED.**

1. **Read EVERYTHING** - All test files, screenshots, source code, configs
2. **Fix COMPLETELY** - No partial implementations or workarounds
3. **Restart ALWAYS** - Service must be restarted before validation
4. **Validate with Playwright** - Mandatory page-level testing, exact scenario reproduction
5. **Prove with Screenshot** - Must save `validation_pass.png` as proof
6. **Pass ALL Steps** - Every step must succeed, no partial success accepted

**Fix with 100% confidence through complete validation, or don't fix at all.**
**Validation is NOT optional - it is the DEFINITION of completion.**