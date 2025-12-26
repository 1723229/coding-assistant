---
name: test-fix
description: "Analyze test case results and apply intelligent fixes based on failure patterns"
category: testing
complexity: enhanced
mcp-servers: [playwright]
personas: [qa-specialist, root-cause-analyst]
---

# /test-fix - Test Result Analysis & Intelligent Fix

## Triggers
- Test case result files (JSON format with groups, steps, errors)
- Failed test scenarios requiring root cause analysis
- System behavior validation failures
- UI/UX workflow validation errors
- Integration test failures with screenshots

## Usage
```
/test-fix <result-file> [--analyze-only] [--auto-fix] [--verbose]
```

## Behavioral Flow
1. **Parse**: Load and parse test result JSON structure
2. **Analyze**: Deep analysis of failure patterns, error messages, and screenshots
3. **Diagnose**: Root cause identification using systematic reasoning
4. **Plan**: Generate fix strategy based on error type and context
5. **Apply**: Implement fixes with validation (if --auto-fix enabled)
6. **Report**: Comprehensive analysis report with recommendations

Key behaviors:
- Parse hierarchical test results (groups → objectives → steps)
- Analyze Chinese/English error messages and descriptions
- Visual analysis of screenshots to understand UI state
- Identify system constraints vs implementation bugs
- Distinguish between fixable bugs and design limitations
- Generate actionable fix recommendations
- Track fix success rate and patterns

## MCP Integration
- **Playwright MCP**: Re-execute test scenarios for validation (if applicable)
- **Root Cause Analyst Persona**: Systematic investigation of underlying issues
- **QA Specialist Persona**: Quality assessment and test strategy

## Tool Coordination
- **Read**: Load test result JSON and related files
- **Grep**: Search codebase for related implementations
- **Bash**: Execute validation commands and re-run tests
- **Write**: Generate analysis reports and fix documentation
- **Edit**: Apply code fixes based on analysis

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

## Analysis Categories

### 1. System Constraints (Not Fixable)
- Hardware/OS limitations (e.g., "缩放比例必须在100%到500%之间")
- API restrictions
- Third-party service limitations
- Business rule violations

### 2. Implementation Bugs (Fixable)
- Logic errors in code
- Incorrect UI selectors
- Missing validation
- Race conditions
- Incorrect error handling

### 3. Test Design Issues (Test Needs Fix)
- Unrealistic test scenarios
- Incorrect expectations
- Missing preconditions
- Flaky test patterns

### 4. Integration Issues
- Component communication failures
- Data synchronization problems
- Timing issues
- Dependency conflicts

## Key Patterns

### Pattern 1: System Constraint Detection
```
Error indicates system limitation →
  Analyze if constraint is documented →
  Verify if expected behavior →
  Recommend test case adjustment or requirement clarification
```

### Pattern 2: Implementation Bug Fix
```
Error indicates code issue →
  Locate relevant source code →
  Analyze root cause systematically →
  Generate fix with validation →
  Re-run affected tests
```

### Pattern 3: Visual State Analysis
```
Screenshot shows unexpected UI state →
  Compare with expected state →
  Identify UI rendering/interaction issues →
  Locate UI component code →
  Apply fix and validate visually
```

### Pattern 4: Multi-Step Workflow Failure
```
Workflow breaks at specific step →
  Analyze previous successful steps →
  Identify state transition failure →
  Fix state management or navigation logic →
  Validate entire workflow
```

## Examples

### Basic Analysis (Analyze Only)
```
/test-fix assets/case_test_result/case.json --analyze-only
# Generates comprehensive analysis report
# Identifies: System constraint (75% scale not supported, min 100%)
# Recommendation: Update test expectation or requirement specification
```

### Auto-Fix Mode
```
/test-fix results/failed_login_test.json --auto-fix
# Analyzes login failure
# Identifies: Incorrect password validation logic
# Applies fix to auth.js:145
# Re-runs test to validate
# Reports: ✅ Test now passing
```

### Verbose Diagnostic Mode
```
/test-fix results/ui_workflow.json --verbose
# Detailed step-by-step analysis
# Screenshot visual inspection with annotations
# Complete stack trace and context analysis
# Multi-hypothesis testing with Sequential MCP
```

### Batch Analysis
```
/test-fix results/*.json --analyze-only
# Analyzes all test results
# Generates summary report with patterns
# Groups failures by category
# Prioritizes fixes by impact
```

## Workflow Details

### Phase 1: Parse & Load (5-10 seconds)
- Load JSON test result file
- Validate structure and required fields
- Load associated screenshots
- Extract error messages and status codes

### Phase 2: Analysis (20-40 seconds)
- **Systematic Reasoning**: Multi-step reasoning about failure patterns
- Classify errors by category (system/implementation/test/integration)
- Analyze screenshot evidence for visual validation
- Compare expected vs actual behavior
- Identify root causes with evidence

### Phase 3: Diagnosis (10-20 seconds)
- Search codebase for related implementations
- Analyze code logic and identify potential bugs
- Evaluate system constraints and limitations
- Generate hypothesis list for failures

### Phase 4: Fix Planning (15-30 seconds)
- Determine if issue is fixable (code vs constraint)
- Generate fix strategy with steps
- Identify affected files and components
- Plan validation approach

### Phase 5: Fix Application (if --auto-fix, 30-60 seconds)
- Apply code changes systematically
- Run affected tests
- Validate fixes with Playwright (if UI-related)
- Generate before/after comparison

### Phase 6: Reporting (5-10 seconds)
- Generate comprehensive markdown report
- Include screenshots with annotations
- Provide fix recommendations
- Track metrics and success rates

## Report Structure

```markdown
# Test Result Analysis Report

## Executive Summary
- **Case Name**: [caseName]
- **Overall Status**: [status]
- **Total Groups**: [count]
- **Failed Groups**: [count]
- **Analysis Date**: [timestamp]

## Failure Analysis

### Group 1: [objective]
**Status**: ❌ Error
**Root Cause**: [System Constraint | Implementation Bug | Test Design | Integration Issue]

**Error Message**:
> [error message]

**Evidence**:
- Screenshot: [path] - [visual analysis]
- Code Location: [file:line]
- Related Components: [list]

**Diagnosis**:
[Detailed root cause analysis using systematic reasoning]

**Recommendation**:
- [ ] Action 1: [specific fix or adjustment]
- [ ] Action 2: [validation approach]
- [ ] Action 3: [follow-up work]

**Fix Status**:
- ✅ Applied and validated
- ⏳ Pending approval
- ❌ Not fixable (system constraint)
- 📋 Test needs adjustment

---

## Summary Statistics
- Total Steps: [count]
- Successful Steps: [count]
- Failed Steps: [count]
- System Constraints: [count]
- Fixable Bugs: [count]
- Test Adjustments Needed: [count]

## Recommendations Priority
1. 🔴 **Critical**: [high-priority fixes]
2. 🟡 **Important**: [medium-priority fixes]
3. 🟢 **Optional**: [low-priority improvements]

## Next Steps
1. [Immediate action required]
2. [Short-term improvements]
3. [Long-term considerations]
```

## Boundaries

**Will:**
- Parse and analyze test result JSON files with groups/steps structure
- Analyze Chinese and English error messages
- Perform visual analysis of screenshots to understand UI state
- Classify failures into fixable vs constraint categories
- Generate detailed root cause analysis with systematic reasoning
- Apply fixes for implementation bugs (with --auto-fix)
- Generate comprehensive reports with actionable recommendations
- Track patterns across multiple test results
- Re-validate fixes with appropriate testing tools

**Will Not:**
- Modify system constraints or OS limitations
- Change business rules or requirements without approval
- Execute destructive operations without explicit permission
- Auto-fix without thorough analysis (unless --auto-fix flag)
- Ignore error messages or skip root cause investigation
- Make assumptions about expected behavior without evidence
- Generate fixes for issues outside identified code scope

## Safety & Validation

**Pre-Fix Validation:**
- ✅ Analyze error message and context thoroughly
- ✅ Identify root cause with evidence
- ✅ Verify fix won't introduce regressions
- ✅ Check for similar issues in codebase
- ✅ Plan rollback strategy

**Post-Fix Validation:**
- ✅ Re-run failed test case
- ✅ Run related test suite
- ✅ Visual validation with Playwright (UI changes)
- ✅ Verify no new errors introduced
- ✅ Update test documentation

**Risk Assessment:**
- 🔴 **High Risk**: Multi-component changes, state management, auth/security
- 🟡 **Medium Risk**: UI logic, validation rules, data transformations
- 🟢 **Low Risk**: Display text, styling, localization, logging

## Integration with Test Workflow

```bash
# Standard test execution with fix analysis
npm test 2>&1 | tee test-output.log
/test-fix test-results.json --analyze-only

# Continuous fix mode during development
/test-fix results/*.json --auto-fix --watch

# Pre-commit validation
/test-fix latest-results.json --verbose
git add . && git commit -m "fix: address test failures"

# CI/CD integration
npm test || /test-fix test-results.json --analyze-only --export-report
```

## Advanced Features

### Pattern Learning
- Tracks common failure patterns across sessions
- Suggests preventive measures for recurring issues
- Builds knowledge base of fixes

### Multi-Language Support
- Handles Chinese, English, and mixed error messages
- Translates technical terms consistently
- Maintains context across languages

### Visual Regression Detection
- Compares screenshots across test runs
- Identifies UI changes causing failures
- Highlights visual differences

### Smart Retry Logic
- Identifies flaky tests
- Recommends retry strategies
- Distinguishes transient vs persistent failures

---

**Remember**: The goal is not just to fix tests, but to improve overall system quality through intelligent analysis and targeted improvements.
