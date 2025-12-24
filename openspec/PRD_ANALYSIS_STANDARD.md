# Capability: PRD Analysis & Clarification (`/analyze-prd`)

> **Purpose:** A self-contained workflow to convert a vague Product Requirement Document (PRD) into a structured clarification list **compatible with OpenSpec proposal format**.
> **Key Constraint:** Every clarification question must serve the goal of writing **testable Scenarios** in `WHEN...THEN` format.
> **Output Format:** Machine-readable structure with HTML metadata comments and standardized tables for automated processing.

## 0. Format Requirements (Machine-Readable Structure)

### 0.1 Why Machine-Readable Format?

The clarification document must be both human-readable (for PM to fill) and machine-parsable (for automated OpenSpec generation). This dual requirement enables:

1. **Automated Validation** - Verify format compliance before OpenSpec generation
2. **Navigation Indices** - Quick lookup from PRD line → clarification items and vice versa
3. **Frontend Integration** - Display clarification content linked to PRD source
4. **Traceability** - Track every requirement back to its PRD source
5. **Statistics** - Calculate coverage, blockers, and completeness metrics

### 0.2 Mandatory Format Elements

Every clarification.md file MUST include:

#### 1. HTML Metadata Comments

Add before each major structure element:

```markdown
<!-- meta:section=1,type=business_value -->
## 1. 业务价值

<!-- meta:section=6.1,operation_id=op1,prd_section=6.1.3,prd_lines=212-214,operation_name=进度条查看 -->
### 6.1 操作1: 进度条查看

<!-- meta:input_spec,operation_id=op1 -->
#### 输入规范
```

**Valid section_type values:**
- `business_value` - Section 1 (业务价值/Business Value)
- `tech_stack` - Section 2 (技术栈/Tech Stack)
- `ui_ux` - Section 3 (UI/UX资源/UI/UX Resources)
- `scope` - Section 4 (范围确认/Scope Confirmation)
- `data_schema` - Section 5 (数据Schema映射/Data Schema Mapping)
- `operations` - Section 6 (操作详细规范/Operation Specifications)
- `blockers` - Section 9 (阻塞项清单/Blocker List)

#### 2. Table Format with PRD Location

ALL tables MUST include a "PRD定位" (PRD Location) column:

```markdown
| 字段名 | 类型 | 必填 | 说明 | PRD定位 |
|--------|------|------|------|---------|
| problem_id | String | 是 | 问题ID | [PRD:行217] |
| team_leaders | JSON | 是 | 小组领导者 | [PRD:行217-小组领导者] |
| extension_data | JSON | 否 | 扩展字段 | [需补充] |
```

**Valid PRD Location Formats:**
- `[PRD:行214]` - Exact PRD line number
- `[PRD:行217-小组领导者]` - Line number + specific content reference
- `[需补充]` - Needs PM to supplement (not in PRD)
- `[推断]` - Inferred from context
- `[系统生成]` - System auto-generated

#### 3. Operation Components (Section 6)

Each operation MUST have these 7 components with HTML metadata:

```markdown
<!-- meta:section=6.1,operation_id=op1,operation_name=进度条查看 -->
### 6.1 操作1: 进度条查看

<!-- meta:basic_info,operation_id=op1 -->
#### 基本信息

<!-- meta:input_spec,operation_id=op1 -->
#### 输入规范

<!-- meta:output_spec,operation_id=op1 -->
#### 输出规范

<!-- meta:scenarios,operation_id=op1 -->
#### 场景列表

<!-- meta:errors,operation_id=op1 -->
#### 错误处理

<!-- meta:boundaries,operation_id=op1 -->
#### 边界条件

<!-- meta:test_cases,operation_id=op1 -->
#### 测试用例
```

#### 4. Module Metadata Header

Every clarification file starts with:

```markdown
# OpenSpec提议澄清文档: [Module Name]

> **Module ID:** [module-id]
> **PRD来源:** [section] [Module Name] (行[start]-[end])
> **PRD文件:** [prd-file-path]
> **生成时间:** [YYYY-MM-DD]
> **文档状态:** 待产品经理审阅
```

### 0.3 Validation and Index Generation

After generating `clarification.md`, the `/analyze-prd` command MUST:

1. **Run validation tool:**
   ```bash
   cd .claude/script && python generate_clarification_index.py
   ```

2. **Generate two files:**
   - `clarification.md` - Human-readable questionnaire
   - `clarification_index.json` - Machine-readable index with:
     * Navigation indices (`by_prd_line`, `by_operation`, `by_section`, `by_scenario`)
     * Statistics (total sections, operations, scenarios, blockers)
     * PRD coverage analysis
     * Metadata and traceability info

3. **Validation checks:**
   - All sections have HTML metadata comments
   - All tables have "PRD定位" column
   - All operations have 7 required components
   - Operation IDs follow pattern `op\d+` (op1, op2, etc.)
   - Section IDs are valid (numbers or dotted numbers)
   - Line number ranges are logical (start < end)
   - All PRD references are valid

4. **If validation fails:**
   - Display specific errors to user
   - Fix issues in clarification.md
   - Re-run validation until it passes

5. **If validation passes:**
   - Confirm both files ready for use
   - Display statistics summary
   - Guide user to next steps

### 0.4 Benefits of This Format

✅ **Traceability** - Every clarification item links back to PRD source line
✅ **Automation** - Index enables automated OpenSpec proposal generation
✅ **Frontend Integration** - JSON index powers interactive UI displays
✅ **Validation** - Format errors caught before OpenSpec generation
✅ **Coverage Analysis** - Identify uncovered PRD sections
✅ **Navigation** - Bidirectional lookup between PRD and clarifications

---

## 1. The "OpenSpec-Ready" Analysis Algorithm

The Agent MUST apply the following **four-pass analysis** (derived from team guidelines + OpenSpec requirements) when analyzing the PRD. Do not ask for the Wiki; use these hardcoded heuristics:

### Pass 1: Value & Root Need Check (The "Project Initiation" + OpenSpec "Why" Section)
*Team Rule: Projects must define quantifiable business value and address "hidden needs" (not just features).*
*OpenSpec Rule: `proposal.md` requires a clear "Why" section with measurable business impact.*

*   **Heuristic:** Does the PRD explicitly state the **ROI** (e.g., "save 50% time") or **Root Pain Point**?
    *   *If NO:* The generated `context.md` MUST ask for:
        *   **Quantifiable Pain Point:** (e.g., "Current process takes 3 days")
        *   **Expected Outcome:** (e.g., "Target < 10 seconds")
        *   **Hidden Needs:** (e.g., "Do users want just data, or actionable advice?")
        *   **Success Scenario (OpenSpec):** Can this value be expressed as a measurable scenario?
            *   Example: `#### Scenario: Reduce analysis time` → `WHEN quality issue occurs THEN root cause identified within 10 minutes (vs 3 days before)`

### Pass 2: Developer Onboarding Check (The "Newcomer" + OpenSpec `design.md` Foundation)
*Team Rule: Specs must serve as training docs for new developers.*
*OpenSpec Rule: `design.md` (if needed) and `tasks.md` must be clear enough for a junior developer to implement.*

*   **Step 1: Check Common Knowledge Base**
    *   Does `openspec/COMMON_KNOWLEDGE.md` exist?
    *   If YES: Read and extract tech stack information:
        *   Backend framework and version
        *   Frontend framework and version
        *   Database type and version
        *   Deployment environment
        *   Third-party dependencies
        *   Architecture patterns (microservices, monolith, etc.)

*   **Step 2: Evaluate PRD Tech Stack Completeness**
    *   **Heuristic:** Does the PRD define the **Tech Stack**, **Environment**, and **Code Standards**?
    *   **If COMMON_KNOWLEDGE.md exists and has complete tech stack info:**
        *   Pre-fill Section F (Technology Stack) in `clarification.md` with info from COMMON_KNOWLEDGE.md
        *   Mark each pre-filled item with `[来源: COMMON_KNOWLEDGE.md]` or `[Source: COMMON_KNOWLEDGE.md]`
        *   Only ask for clarification on items NOT covered in COMMON_KNOWLEDGE.md
        *   Add note: "✅ 技术栈已从项目公共知识库自动填充" / "✅ Tech stack auto-filled from project common knowledge base"
    *   **If COMMON_KNOWLEDGE.md missing or incomplete:**
        *   The generated `clarification.md` MUST ask for:
            *   **Backend/Frontend Stack Preference:** (e.g., Python vs Node, React vs Vue)
            *   **Database Selection:** (e.g., Postgres vs MySQL)
            *   **Deployment Target:** (e.g., Private Cloud vs SaaS)
            *   **Existing Codebase Reference:** (e.g., "Follow pattern in `auth/` module")
    *   **If PRD has tech stack info that conflicts with COMMON_KNOWLEDGE.md:**
        *   Flag as a warning for user to review
        *   Ask: "PRD specifies [X] but COMMON_KNOWLEDGE.md says [Y], which should be used?"

### Pass 3: Technical Ambiguity Check (The "SRS" + OpenSpec Scenario Foundation)
*Team Rule: Requirements must be "Professional & Unambiguous" (No guessing).*
*OpenSpec Rule: Every feature must have at least one testable `#### Scenario:` with clear input/output.*

*   **Heuristic:** For every "Noun" (Data) and "Verb" (Action) in the PRD:
    *   *Data Source:* Is the **Interface** (API/DB/File) and **Auth** defined?
        *   → *Ask for Swagger/DDL.*
        *   → *OpenSpec Impact:* Without this, cannot write `WHEN system fetches data from MES...`
    *   *Schema:* Are **English Field Names** and **Types** defined?
        *   → *Ask for Schema Mapping.*
        *   → *OpenSpec Impact:* Without this, cannot write `THEN return defect_type='dimensional_deviation'`
    *   *UI/UX:* Is the "Report" or "Dashboard" visual defined?
        *   → *Ask for Figma/Mockups.*
        *   → *OpenSpec Impact:* Without this, cannot write `THEN display report with columns [A, B, C]`
    *   *Testing:* Is the "Accuracy" metric backed by data?
        *   → *Ask for Ground Truth/Test Set.*
        *   → *OpenSpec Impact:* This IS the Scenario! `WHEN user asks "Q" THEN system returns "A"`

### Pass 4: Scenario Decomposition Check (The "OpenSpec Testability" Standard)
*OpenSpec Rule: Every requirement MUST have at least one `#### Scenario:` with WHEN...THEN structure.*
*Purpose: Ensure PRD features can be translated into executable test cases.*

*   **Heuristic:** For every feature mentioned in the PRD, ask:
    *   **"Can I write a concrete WHEN...THEN for this?"**
        *   ✅ **YES Example:** "用户可查询质量数据" →
            ```markdown
            #### Scenario: Query by process type
            - **WHEN** user selects process="加工" and date_range="2025-01"
            - **THEN** return list of quality issues with fields [id, type, process, date]
            ```
        *   ❌ **NO Example:** "整理分析数据" → Too vague!
            *   → *Ask:* "What does '整理' mean? Sort? Aggregate? Clean?"
            *   → *Ask:* "What is the input (raw data schema) and output (analysis result schema)?"

    *   **Edge Cases & Error Handling:**
        *   For each WHEN, ask: "What if it fails?"
        *   → *Example:* `WHEN user queries non-existent process THEN return error "Process not found"`

    *   **Boundary Conditions:**
        *   → *Example:* `WHEN date range is empty THEN return all historical data` or `THEN return error "Date required"`?

*   **Output Requirement:** If a PRD feature CANNOT be decomposed into WHEN...THEN:
    *   The generated `context.md` MUST flag it as a **blocker** and ask for:
        *   **Specific Input:** What data/parameters does the user provide?
        *   **Specific Output:** What does the system return? (Format, fields, structure)
        *   **3 Concrete Examples:** Show me 3 real-world examples of input → output

---

## 2. The Standard Output Template

The Agent MUST generate a file using the specific structure below. Use "Fill-in-the-blanks" format (Code blocks or Quotes) for PDM convenience.

**Key Principle:** Every section must map to either `proposal.md`, `tasks.md`, `design.md`, or `specs/*.md` in OpenSpec format.

**Note:** This file is temporary and should be deleted after the OpenSpec proposal is created. If analyzing multiple PRDs, use unique names like `prd-context-quality-system.md`.

```markdown
# Project Context Clarification (For OpenSpec Proposal Generation)

> **Instructions:** Please fill in the missing details below. This file will be used by `/openspec:proposal` to auto-generate:
> - `openspec/changes/[change-id]/proposal.md` (Why, What, Impact)
> - `openspec/changes/[change-id]/tasks.md` (Implementation checklist)
> - `openspec/changes/[change-id]/design.md` (if needed)
> - `openspec/changes/[change-id]/specs/[capability]/spec.md` (Requirements + Scenarios)

---

## Section A: Business Value (→ `proposal.md` - "Why")
*Maps to OpenSpec `## Why` section.*

### A.1 Quantified Pain Point
> **Current State:** (e.g., "Root cause analysis takes 3 days per issue")
>

### A.2 Expected Outcome (Success Metric)
> **Target State:** (e.g., "Reduce to < 10 minutes with 90% accuracy")
>

### A.3 Success Scenario (OpenSpec Format)
> Write as a testable scenario to prove value delivery:
> ```markdown
> #### Scenario: Faster root cause identification
> - **WHEN** quality issue is reported
> - **THEN** system provides root cause analysis within 10 minutes
> - **AND** accuracy rate >= 90% (vs baseline)
> ```

---

## Section B: Functional Requirements (→ `specs/[capability]/spec.md`)
*Maps to OpenSpec `## ADDED Requirements` - high-level "what" the system does.*

### B.1 Feature List (from PRD)
For each feature in the PRD, describe what it does:

#### Feature 1: [Name from PRD, e.g., "问数配置"]
**PRD Description:** (Copy exact text from PRD)

**Functional Requirement:**
> What does this feature do? (High-level description)
> Example: "System SHALL allow users to query quality data using natural language"

**User Stories:**
> Provide 2-3 user stories:
> - As a quality manager, I want to query defect counts by process, so that I can identify problem areas
> - As a production supervisor, I want to see trend analysis, so that I can predict quality issues
> - As a...

#### Feature 2: [Next feature...]
(Repeat structure above)

---

## Section C: Data Schema (→ `specs/[capability]/spec.md` + `design.md`)
*Required to write concrete THEN clauses in Scenarios.*

### C.1 Data Sources
#### MES System
- **接入方式:** (Check one)
  - [ ] REST API (Paste Swagger URL or JSON example)
  - [ ] Database Direct (Paste DDL or table schema)
  - [ ] File Export (Paste file format + sample data)

- **关键字段映射 (English Field Names):**
  > Map PRD's Chinese terms to actual system fields:
  > | PRD Term (中文) | System Field Name | Data Type | Example Value |
  > |----------------|-------------------|-----------|---------------|
  > | 问题类型 | defect_type | ENUM | 'dimensional_deviation' |
  > | 发生工序 | process_name | VARCHAR | '加工' |
  > | 发现时间 | detected_at | TIMESTAMP | '2025-01-15 14:30:00' |
  > | ... | ... | ... | ... |

#### ERP System
(Same structure as MES)

#### 飞书云文档
- **Document Type:**
  - [ ] 多维表格 (Bitable) → App Token: _____, Table ID: _____
  - [ ] Excel/Word → Upload method? Auto-sync?

---

## Section D: Interface Specifications (→ `specs/[capability]/spec.md`)
*Required to write concrete WHEN...THEN scenarios with specific inputs/outputs.*

### D.1 Input/Output Specifications
For each feature from Section B, specify the interface contract:

#### Feature 1: [Name from Section B]

**Input Specification:**
> What does the user provide?
> - **Format:** (Natural language text? Form fields? API parameters?)
> - **Required fields:** (List all required inputs)
> - **Optional fields:** (List all optional inputs)
> - **Validation rules:** (What makes input valid/invalid?)
>
> **Examples:**
> 1. Input: `{"query": "上周加工工序有多少问题?", "user_id": "user123"}`
> 2. Input: `{"process": "加工", "start_date": "2024-12-01", "end_date": "2024-12-07"}`
> 3. Input: ...

**Output Specification:**
> What does the system return?
> - **Format:** (JSON? HTML? PDF? Text?)
> - **Schema:** (Define the structure)
> - **Fields:** (List all output fields with types)
>
> **Examples:**
> 1. Output: `{"count": 23, "issues": [...]}`
> 2. Output: `"23个问题"`
> 3. Output: ...

**Concrete Scenarios (3-5 minimum):**
> Provide testable input → output pairs:
> ```markdown
> #### Scenario: Query by process and date range
> - **WHEN** user inputs query="上周加工工序有多少问题?"
> - **THEN** system returns count=23 and list of 23 issues
>
> #### Scenario: Invalid date range
> - **WHEN** user inputs start_date > end_date
> - **THEN** system returns error "Invalid date range"
>
> #### Scenario: No results found
> - **WHEN** user queries non-existent process
> - **THEN** system returns count=0 and empty list
> ```

**Error Handling:**
> List all error cases and responses:
> - Invalid input → Error code 400, message "..."
> - System unavailable → Error code 503, message "..."
> - Permission denied → Error code 403, message "..."

**Boundary Conditions:**
> - Date range limits: Max 1 year
> - Result set size: Max 1000 records, paginated
> - Query complexity: Max 3 filters combined
> - Rate limiting: 100 requests per minute

#### Feature 2: [Next feature...]
(Repeat structure above)

---

### D.2 UI/UX Design Specifications
*Visual and interaction design details.*

#### UI Mockups
> **Required:**
> - Figma link or screenshot for each major screen
> - Layout specifications (grid, spacing, responsive breakpoints)
> - Component library reference (if using existing design system)

#### Interaction Flows
> **For each feature, describe the user flow:**
>
> **Feature 1: Query Interface**
> 1. User lands on query page
> 2. User types query in search box
> 3. System shows loading indicator
> 4. System displays results in table format
> 5. User can export results to Excel
>
> **Feature 2: Report Generation**
> 1. User clicks "Generate Report" button
> 2. User selects date range and filters
> 3. User clicks "Generate"
> 4. System shows progress bar
> 5. System downloads PDF report

#### Visual Design Assets
> **Provide:**
> - Color palette (primary, secondary, error, success colors)
> - Typography (font families, sizes, weights)
> - Icon set (if custom icons are used)
> - Report template (if generating reports)

---

## Section E: Acceptance Criteria (→ Test Cases in `tasks.md`)
*Test data and validation criteria - references scenarios from Section D.*

### E.1 Test Data Preparation
**Purpose:** Provide real data to validate scenarios from Section D.

**Required:**
> For each scenario in Section D, provide:
> - **Test data setup:** What data must exist in MES/ERP/database?
> - **Expected results:** What should the system return given this test data?
> - **Data source reference:** Link to actual MES records or test database

**Example:**
```text
Scenario: Query by process and date range (from Section D.1)
- Test Data Setup:
  * MES database contains 23 quality issues for process="加工" in date range 2024-12-01 to 2024-12-07
  * Record IDs: ISS-001 through ISS-023
  * Sample record: {"id": "ISS-001", "process": "加工", "defect_type": "dimensional_deviation", ...}
- Expected Result:
  * count: 23
  * issues: [array of 23 issue objects]
- Data Source: MES test database, table `quality_issues`, records ISS-001 to ISS-023
```

### E.2 Standard Test Set (100% Accuracy Target)
**PRD States:** "标准测试准确率达100%"

**Required:** Provide 10+ standard test cases with ground truth:
```text
Test Case 1:
- Scenario Reference: Section D.1, Feature 1, Scenario "Query by process and date range"
- Input: "2024年12月加工工序的尺寸偏差问题有多少个?"
- Expected Output: "15个"
- Test Data: MES records ISS-001 to ISS-015 (defect_type='dimensional_deviation', process='加工', date in Dec 2024)
- Pass Criteria: Exact match on count

Test Case 2:
- Scenario Reference: ...
- Input: ...
- Expected Output: ...
- Test Data: ...
- Pass Criteria: ...

(Provide 10+ cases covering all scenarios in Section D)
```

### E.3 Free-Form Test Criteria (90% Accuracy Target)
**PRD States:** "自由发挥测试准确率达90%"

**Required Clarifications:**
> **Define "自由发挥":**
> - [ ] Paraphrased versions of standard queries?
> - [ ] Queries with typos or grammatical errors?
> - [ ] Queries combining multiple filters in unexpected ways?
> - [ ] Queries using synonyms or alternative phrasings?
>
> **Define accuracy measurement:**
> - [ ] Exact match (output must be identical)?
> - [ ] Semantic match (output conveys same information)?
> - [ ] Partial match (output contains correct information)?
>
> **Define error tolerance:**
> - Acceptable errors: (e.g., "formatting differences OK")
> - Unacceptable errors: (e.g., "wrong count NOT OK")
>
> **Provide 20+ free-form test cases:**
> (Similar format to E.2, but with more varied/creative queries)

---

## Section F: Technical Stack (→ `design.md` + `tasks.md`)
*Required for newcomer onboarding and implementation planning.*

### F.1 Technology Choices
- **Backend:** [ ] Python (FastAPI) [ ] Node.js [ ] Java
- **Frontend:** [ ] React [ ] Vue [ ] 飞书小程序
- **Database:** [ ] PostgreSQL [ ] MySQL [ ] ClickHouse
- **AI/LLM:** [ ] OpenAI GPT-4 [ ] Claude [ ] 通义千问 [ ] 本地模型

### F.2 Deployment Environment
- [ ] Alibaba Cloud
- [ ] AWS
- [ ] 飞书内部容器
- [ ] On-premise servers

### F.3 Existing Codebase Patterns
> Link to similar modules in codebase (if any):
> - Auth pattern: `src/auth/`
> - Data sync pattern: `src/integrations/`
> - Report generation: `src/reports/`

---

## Section G: Out-of-Scope Clarifications
*Helps prevent scope creep.*

> List what the PRD does NOT require:
> - Real-time alerting? (YES / NO / UNCLEAR)
> - Mobile app? (YES / NO / UNCLEAR)
> - Multi-language support? (YES / NO / UNCLEAR)
> - Historical data migration before 2024? (YES / NO / UNCLEAR)

---

## 🚨 Critical Blockers Summary
*Auto-generated list of items that MUST be filled before proposal generation.*

The following items are BLOCKING proposal creation:
- [ ] **Section A.3:** Success Scenario (cannot write `proposal.md` without it)
- [ ] **Section B:** Functional requirements and user stories (cannot write high-level `specs/` without it)
- [ ] **Section C.1:** MES/ERP schema mapping (cannot write data access scenarios)
- [ ] **Section D.1:** Input/Output specifications with concrete scenarios (cannot write testable `specs/` without it)
- [ ] **Section D.2:** UI/UX mockups and interaction flows (cannot write user experience scenarios)
- [ ] **Section E.2:** Standard test set with ground truth (cannot validate scenarios)
- [ ] **Section F.1:** Technology stack choices (cannot write `design.md` and `tasks.md`)
```
