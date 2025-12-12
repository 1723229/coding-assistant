---
name: Analyze PRD
description: Convert a vague PRD into a structured clarification list for OpenSpec proposal generation
category: project
tags: [prd, analysis, openspec, clarification]
---

**Objective**
Convert a specific module/function from the PRD into `docs/PRD-Gen/clarification.md` - a structured questionnaire that PM can fill to enable OpenSpec proposal generation via `/openspec:proposal`.

**Guardrails**
- Follow the 4-pass analysis algorithm defined in `openspec/PRD_ANALYSIS_STANDARD.md`
- Every clarification question MUST serve the goal of writing testable OpenSpec Scenarios (`WHEN...THEN` format)
- Flag features that cannot be decomposed into concrete input/output as BLOCKERS
- Use the exact template structure from `PRD_ANALYSIS_STANDARD.md` Section 2
- **IMPORTANT**: Generate `docs/PRD-Gen/clarification.md` in the SAME LANGUAGE as the input PRD
  - If PRD is in Chinese, output in Chinese
  - If PRD is in English, output in English
  - Keep technical terms and OpenSpec keywords (WHEN, THEN, SHALL) in English regardless of language
- **SCOPE**: Only analyze the specified module's PRD content, not the entire PRD

**Prerequisites**
1. User must provide:
   - `--module`: Module/function name or ID (e.g., "D1组建团队" or "d1-team-formation")
   - `--feature-tree`: Path to FEATURE_TREE.md file (e.g., "docs/PRD-Gen/FEATURE_TREE.md")
   - `--prd`: Path to original PRD document (PDF/Markdown/Text)
2. Read `openspec/PRD_ANALYSIS_STANDARD.md` to understand the analysis standard
3. Read `openspec/COMMON_KNOWLEDGE.md` to collect common knowledges related

**Steps**

1. **Parse Parameters**
   - Extract module name/ID from `--module` parameter
   - Extract feature tree path from `--feature-tree` parameter
   - Extract PRD document path from `--prd` parameter

2. **Read Feature Tree and Locate Module**
   - Read the FEATURE_TREE.md file from provided path
   - Search for the module by matching:
     - Module ID (e.g., "d1-team-formation")
     - Chinese name (e.g., "D1组建团队")
     - English name (e.g., "D1 Team Formation")
   - Extract module information:
     - Module ID
     - Chinese and English names
     - PRD source line range (e.g., "行212-222")
     - Operations list (包含的操作)
     - Parent L1 feature for context

3. **Display Scope Summary**
   - Show what will be analyzed:
     ```
     📋 Analysis Scope:
     - Module: [Chinese Name] ([English Name])
     - Module ID: [module-id]
     - PRD Source: [section] (行[start]-[end])
     - Operations: [count] operations
       • [operation 1]
       • [operation 2]
       • ...
     ```
   - Ask user to confirm before proceeding (optional)

4. **Read the Standard**
   - Read `openspec/PRD_ANALYSIS_STANDARD.md` to internalize the 4-pass algorithm

5. **Extract Scoped PRD Content**
   - Read the PRD document from provided path
   - Extract ONLY the lines specified in the feature tree (e.g., lines 212-222)
   - Include parent L1 section context if needed for understanding
   - Detect the primary language of the PRD content (Chinese, English, etc.)

6. **Execute Four-Pass Analysis (Scoped)**
   Apply each pass to the SCOPED PRD content only:
   - **Pass 1**: Value & Root Need Check → Extract for Section A (Business Value)
   - **Pass 2**: Developer Onboarding Check → Extract for Section F (Tech Stack)
   - **Pass 3**: Technical Ambiguity Check → Extract for Sections C (Data Schema) & D (UI/UX)
   - **Pass 4**: Scenario Decomposition Check → Extract for Section B (Feature Breakdown)

7. **Generate `docs/PRD-Gen/clarification.md`**
   - **IMPORTANT**: Always use the fixed filename `docs/PRD-Gen/clarification.md`
   - Use the template structure from `openspec/PRD_ANALYSIS_STANDARD.md` Section 2
   - **Write all content in the PRD's language** (detected in Step 5)
   - Add module metadata header:
     ```markdown
     # Clarification for OpenSpec Proposal: [Module Name]

     > **Module ID:** [module-id]
     > **PRD Source:** [section] (行[start]-[end])
     ```
   - For Section B (Features): List each OPERATION from FEATURE_TREE and apply the "🚨 OpenSpec Testability Check"
   - For Section C (Data): Create schema mapping tables for each data source mentioned
   - For Section D (Interface): Create input/output specs for each operation
   - For Section E (Tests): Extract any test criteria mentioned in PRD
   - Fill in "Critical Blockers Summary" based on missing information
   - **Language Guidelines**:
     - Section headers: Use PRD language (e.g., "## 章节 A: 业务价值" for Chinese)
     - Questions/prompts: Use PRD language
     - Technical terms: Keep in English (WHEN, THEN, SHALL, API, JSON, etc.)
     - Code examples: Always in English

8. **Validate Completeness**
   - Ensure every operation has the 5 clarification sub-sections (Input/Output/Examples/Errors/Boundaries)
   - Ensure at least one concrete WHEN...THEN example is requested for each operation
   - Mark items that block OpenSpec generation in the Critical Blockers section

9. **Output Summary**
   After generating `docs/PRD-Gen/clarification.md`, provide a brief summary:
   - Module name and ID
   - Number of operations identified
   - Number of critical blockers found
   - Recommended next steps for PM

10. **Handle Review Messages (Iterative Refinement)**
    - If user provides review messages during the conversation, recognize these patterns:
      - `User Review on "Section X", msg: "review message"`
      - `Review for Section X: message`
      - `For Section X, message`
      - Natural language: "Section X should say..." or "Change X to..."
    - When review message detected:
      1. Parse the section reference (e.g., "Section A.1", "Section D.1")
      2. Extract the review message content
      3. Update the relevant section in `docs/PRD-Gen/clarification.md`
      4. Add entry to "Review History" section at the end of the file:
         ```markdown
         ## Review History

         ### Review [N]: [Timestamp]
         **Source:** [Section reference]
         **Message:** [review message]
         **Action Taken:** [what was updated]
         ```
      5. Update checklist items if they are now addressed
      6. Confirm the update to the user
    - Support multiple reviews in the same conversation
    - Ask if more reviews are needed after each update

**Reference**
- Standard: `openspec/PRD_ANALYSIS_STANDARD.md`
- OpenSpec conventions: `openspec/AGENTS.md`
- Project context: `openspec/project.md`

**Example Usage**

Example 1: Initial Analysis (Chinese PRD)
```
User: /analyze-prd --module "D1组建团队" --feature-tree "docs/PRD-Gen/FEATURE_TREE.md" --prd "docs/原始PRD.pdf"

Agent: [Reads FEATURE_TREE.md]
       [Locates module: d1-team-formation]

       📋 Analysis Scope:
       - Module: D1组建团队 (D1 Team Formation)
       - Module ID: d1-team-formation
       - PRD Source: 6.1.3 D1组建团队 (行212-222)
       - Operations: 9 operations
         • 进度条查看
         • 问题信息查看
         • 基础信息维护
         • 人员配置
         • 审批人员配置
         • 计划维护
         • 子任务创建
         • 子任务标记完成
         • 步骤完结

       [Detects language: Chinese]
       [Reads openspec/PRD_ANALYSIS_STANDARD.md]
       [Extracts PRD lines 212-222]
       [Executes 4-pass analysis on scoped content]
       [Generates docs/PRD-Gen/clarification.md in Chinese]

       ✅ 已生成 docs/PRD-Gen/clarification.md

       摘要:
       - 模块: D1组建团队 (d1-team-formation)
       - 识别到 9 个操作
       - 发现 6 个关键阻塞项:
         * 业务价值量化指标缺失
         * 人员配置的数据schema未定义
         * 甘特图组件的输入输出格式未定义
         * 子任务的状态流转规则不明确
         * UI/UX设计稿缺失
         * 测试数据准备说明缺失

       下一步: 请填写 docs/PRD-Gen/clarification.md，然后运行 /openspec:proposal
```

Example 2: Review and Update (Same Conversation)
```
User: User Review on "Section A.1", msg: "当前组建团队需要2小时，目标是10分钟内完成"

Agent: ✅ 已更新 Section A.1 in docs/PRD-Gen/clarification.md

       更新内容:
       - 当前状态: "组建团队需要2小时"
       - 目标状态: "10分钟内完成团队组建"

       已添加审阅记录到 Review History

       还有其他需要审阅的内容吗？

User: User Review on "Section D.1", msg: "人员配置需要支持从组织架构树选择，支持多选"

Agent: ✅ 已更新 Section D.1 in docs/PRD-Gen/clarification.md

       更新内容:
       - 输入方式: 添加"从组织架构树选择人员（支持多选）"
       - 输入字段: 添加 selected_user_ids (Array<string>)

       已添加审阅记录到 Review History

       还有其他需要审阅的内容吗？

User: 没有了

Agent: ✅ 所有审阅已应用到 docs/PRD-Gen/clarification.md

       当前状态:
       - 已完成审阅: 2 项
       - 剩余阻塞项: 4 项

       下一步: 继续填写剩余章节，然后运行 /openspec:proposal
```

Example 3: English PRD
```
User: /analyze-prd --module "problem-type-management" --feature-tree "docs/PRD-Gen/FEATURE_TREE.md" --prd "docs/original-prd.pdf"

Agent: [Reads FEATURE_TREE.md]
       [Locates module: problem-type-management]

       📋 Analysis Scope:
       - Module: 问题类型管理 (Problem Type Management)
       - Module ID: problem-type-management
       - PRD Source: 6.1.1 问题类型管理 (行188-199)
       - Operations: 10 operations
         • 列表查看
         • 查询
         • 新增
         • ...

       [Detects language: Chinese]
       [Reads openspec/PRD_ANALYSIS_STANDARD.md]
       [Extracts PRD lines 188-199]
       [Executes 4-pass analysis on scoped content]
       [Generates docs/PRD-Gen/clarification.md in Chinese]

       ✅ Generated docs/PRD-Gen/clarification.md

       Summary:
       - Module: 问题类型管理 (problem-type-management)
       - 10 operations identified
       - 5 critical blockers found:
         * Business value quantification missing
         * Workflow configuration data schema undefined
         * Drag-and-drop flow builder input/output format unclear
         * Approval role mapping not defined
         * UI/UX mockups missing

       Next: Please fill docs/PRD-Gen/clarification.md, then run /openspec:proposal
```

**Review Message Patterns**

The agent should recognize and handle these review message formats:

1. **Structured Format (Recommended):**
   ```
   User Review on "Section A.1", msg: "review message here"
   ```

2. **Alternative Structured Format:**
   ```
   Review for Section D.1: review message here
   ```

3. **Natural Language:**
   ```
   For Section B.2, the operation should include batch processing
   Section C.1 should use PostgreSQL instead of MySQL
   Change the business value in Section A to focus on time savings
   ```

4. **Multiple Reviews:**
   ```
   User Review on "Section A.1", msg: "first review"
   User Review on "Section D.1", msg: "second review"
   User Review on "Section E.1", msg: "third review"
   ```

**Notes**
- The output file is ALWAYS `docs/PRD-Gen/clarification.md` (fixed filename)
- This file prepares input for `/openspec:proposal` command (does NOT create proposal.md directly)
- Analysis is scoped to ONLY the specified module's PRD lines
- Support iterative refinement through review messages in the same conversation
- Maintain review history for traceability
