---
name: OpenSpec: Validate Spec Consistency
description: Validate internal consistency between proposal, specs, design, and tasks before implementation.
category: OpenSpec
tags: [openspec, validation, consistency]
---

# OpenSpec Spec Consistency Validation

You are validating the internal consistency of an OpenSpec change proposal before the implementation phase.

## Your Task

Perform a deep semantic analysis of the change documents to identify gaps, contradictions, and misalignments between:
- Proposal scope
- Spec requirements
- Design decisions
- Implementation tasks

## Arguments

The user will provide: `<change-id>`

## Process

### 1. Document Collection

Read ALL documents for the change:
```bash
openspec/changes/<change-id>/
├── proposal.md       # Scope and intent
├── design.md         # Technical approach (if exists)
├── tasks.md          # Implementation checklist
└── specs/*/spec.md   # Requirements deltas
```

### 2. Semantic Understanding

**Extract from proposal.md:**
- What is being built?
- What is explicitly OUT of scope? (Look for: 后续, later, future, phase 2, deferred, out of scope)
- What simplifications or compromises are mentioned?

**Extract from specs/*/spec.md:**
- List ALL "SHALL" and "MUST" requirements
- For each requirement, note which spec file and line number
- Identify key scenarios (GIVEN/WHEN/THEN)

**Extract from design.md (if exists):**
- What architectural decisions were made?
- What technical approach is described?
- Are there any simplifications mentioned?

**Extract from tasks.md:**
- What features are broken down into tasks?
- Which tasks are marked complete `[x]` vs incomplete `[ ]`?

### 3. Gap Analysis

Perform these consistency checks:

#### A. Proposal ↔ Specs Alignment
```
IF proposal mentions scope reductions (后续, later, etc.)
THEN check: Do spec deltas reflect the reduced scope?
  - If specs describe full feature but proposal says "build later"
    → FLAG: Scope mismatch
```

#### B. Specs ↔ Design Traceability
```
FOR EACH SHALL requirement in specs:
  Check: Is there a corresponding section in design.md?
  - If design doesn't address the requirement
    → FLAG: Missing design for requirement
  - If design contradicts the requirement
    → FLAG: Design-spec contradiction
```

#### C. Design ↔ Tasks Breakdown
```
FOR EACH major feature in design.md:
  Check: Are there tasks in tasks.md that implement it?
  - If design describes feature but no tasks exist
    → FLAG: Missing implementation tasks
```

#### D. Spec Scenarios ↔ Tasks Coverage
```
FOR EACH scenario in spec deltas:
  Check: Can you map it to specific task(s)?
  - If scenario has no corresponding task
    → FLAG: Scenario not covered by tasks
```

#### E. Entity/Concept Consistency
```
IF any document mentions entity X (e.g., "检验标准", "InspectionStandard"):
  Check: Do all documents use consistent understanding?
  - Check if one doc says "defer" vs another says "implement"
  - Check if one doc describes backend logic vs another says UI only
  → FLAG: Inconsistent entity understanding
```

### 4. Generate Report

Output a structured report in this format:

```markdown
# Spec Consistency Validation Report: <change-id>

## Summary
- Total specs analyzed: X
- Total SHALL requirements: X
- Total design sections: X
- Total tasks: X
- Gaps detected: X

---

## ✅ Consistent Areas

List what IS aligned properly (to give confidence).

---

## ⚠️ Gaps Detected

### Gap 1: [Category] - [Brief Title]

**Issue:**
[Clear description of the inconsistency]

**Evidence:**
- proposal.md:25: "检验标准管理界面后续再建"
- specs/inspections/spec.md:20: "WHEN system searches for valid 检验标准"
- design.md:45: "Accept选中类别/项目/抽样方案"

**Analysis:**
[Your semantic interpretation of what's contradictory]

**Interpretation Options:**
A) [First possible interpretation and its implications]
   → If this is correct: [what needs to change]

B) [Second possible interpretation and its implications]
   → If this is correct: [what needs to change]

**Recommendation:**
[Suggest which interpretation seems more likely based on context]

**Human Decision Required:**
[ ] Choose interpretation A and [add tasks / update specs / update design]
[ ] Choose interpretation B and [add tasks / update specs / update design]
[ ] Other: _______________

---

### Gap 2: ...

[Repeat format for each gap]

---

## 📋 Next Steps

1. Review each gap with stakeholders
2. For each gap, decide on interpretation
3. Update documents accordingly
4. Re-run validation to confirm consistency
5. Proceed to implementation phase
```

## Critical Principles

1. **DETECT ONLY, NEVER AUTO-FIX**
   - Identify gaps and contradictions
   - Provide interpretation options
   - Let human decide what to do

2. **Deep Semantic Analysis**
   - Don't rely on keyword matching
   - Understand intent and implications
   - Consider multiple interpretations

3. **Provide Evidence**
   - Always cite specific line numbers
   - Quote exact text
   - Show the contradiction clearly

4. **Be Helpful, Not Prescriptive**
   - Suggest likely interpretations
   - Explain implications of each choice
   - But final decision is human's

## Example Outputs

**Good (Specific, Cited, Options):**
```
⚠️ Gap: Spec requires backend standard lookup but design describes manual input

Evidence:
- specs/inspections/spec.md:20: "WHEN system searches for valid 检验标准"
- design.md:45: "Accept选中类别/项目/抽样方案"

Options:
A) Implement backend standard entity + search logic (defer only UI)
B) Update spec to describe simplified manual creation

Recommendation: Option A aligns better with proposal phrase "以标准快照的方式保留"
```

**Bad (Vague, No Evidence, Prescriptive):**
```
The specs don't match the design. Fix the specs.
```

## Begin

Read all documents for the specified change-id and produce the spec consistency validation report.
