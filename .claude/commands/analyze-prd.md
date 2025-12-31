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
2. User may provide(optonal):
   - `--ddd`: Path to DDD domain design file (Markdown)
2. Read `openspec/PRD_ANALYSIS_STANDARD.md` to understand the analysis standard
3. Read `openspec/COMMON_KNOWLEDGE.md` to collect common knowledges related

**Steps**

1. **Parse Parameters**
   - Extract module name/ID from `--module` parameter
   - Extract feature tree path from `--feature-tree` parameter
   - Extract PRD document path from `--prd` parameter
   - Extract DDD document path from `--ddd` parameter (if present)

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

4. **Read Common Knowledge Base**
   - Check if `openspec/COMMON_KNOWLEDGE.md` exists
   - If exists, extract tech stack information:
     * Backend framework and version
     * Frontend framework and version
     * Database type and version
     * Deployment environment
     * Third-party dependencies
     * Architecture patterns (microservices, monolith, etc.)
   - Store for use in Section 2 (Technology Stack)
   - Display summary:
     ```
     📚 Common Knowledge Loaded:
     - Backend: [framework and version]
     - Frontend: [framework and version]
     - Database: [database type and version]
     - Deployment: [environment]
     ```

   **4.5 Create Tech Stack Filter Index**
   From loaded COMMON_KNOWLEDGE.md, create mental index of known tech stack:
   - **Backend**: Java 8, Spring Boot 2.3.2, Spring Cloud Hoxton.SR9, Nacos
   - **Frontend**: React 16.9.0 (JavaScript, NOT TypeScript), Ant Design 3.26.20, Redux, React Router 4
   - **Database**: MySQL (actual deployment), supports PostgreSQL/Oracle/SQL Server
   - **ORM**: JPA, MyBatis, MyBatis-Plus
   - **Middleware**: Redis (cache), RabbitMQ (message queue), MinIO (object storage)
   - **Architecture**: Spring Cloud Microservices with Nacos service registration
   - **API Docs**: Swagger 2.9.2
   - **Build Tools**: Webpack (frontend), Yarn (package manager)

5. **Read the Standard**
   - Read `openspec/PRD_ANALYSIS_STANDARD.md` to internalize the 4-pass algorithm

6. **Extract Scoped PRD Content**
   - Read the PRD document from provided path
   - Extract ONLY the lines specified in the feature tree (e.g., lines 212-222)
   - Include parent L1 section context if needed for understanding
   - Detect the primary language of the PRD content (Chinese, English, etc.)

6. **Execute Four-Pass Analysis (Scoped)**
   Apply each pass to the SCOPED PRD content only:
   - **Pass 1**: Developer Onboarding Check → Pre-fill Section F (Tech Stack) from COMMON_KNOWLEDGE.md if available
   - **Pass 2**: Technical Ambiguity Check → Extract for Sections C (Data Schema) & D (UI/UX)
   - **Pass 3**: Scenario Decomposition Check → Extract for Section B (Feature Breakdown)

   **IMPORTANT: Skip the following sections:**
   - ❌ DO NOT generate "业务价值" (Business Value) section
   - ❌ DO NOT generate deployment environment clarification questions
   - ❌ DO NOT ask about business metrics or pain points
   - ✅ ONLY focus on technical specifications and implementation details

   **6.4 CRITICAL: Section 2 (技术栈) EXCLUSION Policy** 🔴

   **Section 2 (技术栈) Generation Rules:**
   - ❌ **DO NOT generate Section 2 (技术栈) at all**
   - ✅ Tech stack information is already defined in `openspec/COMMON_KNOWLEDGE.md` and does NOT need clarification
   - ✅ Start document with Section 2 (UI/UX资源) instead of tech stack
   - ❌ **DO NOT** ask generic tech stack questions anywhere in ANY section

   **Section Renumbering After Removing Tech Stack:**
   - Original Section 2 (技术栈) → **REMOVED entirely**
   - Original Section 3 (UI/UX资源) → **New Section 2**
   - Original Section 4 (范围确认) → **New Section 3**
   - Original Section 5 (数据Schema映射) → **New Section 4**
   - Original Section 6 (操作详细规范) → **New Section 5**
   - Original Section 9 (阻塞项清单) → **New Section 6**

   **Feature-Specific Tech Choices Handling:**
   - Feature-specific technology choices are developer implementation details → **Skip entirely**
   - Examples of questions to NEVER ask:
     * ❌ Excel library choice → Developer decision
     * ❌ Flowchart/visualization component → Developer decision
     * ❌ API integration method → Developer decision

   **6.5 CRITICAL: Tech Stack Filtering Rule** 🔴

   **Rule 1: Section 2 Pre-fill Only**
   Section 2 (技术栈) MUST:
   - ✅ Pre-fill known tech stack from COMMON_KNOWLEDGE.md (2.1-2.4 subsections only)
   - ❌ NOT include any "待明确的技术选型" subsection (no Section 2.5)
   - ❌ NOT include any clarification questions (`<!-- clarification:start -->`)
   - ✅ End immediately after Section 2.4 (架构模式)

   **Rule 2: Complete Tech Stack Filter**
   Before generating ANY clarification question in ALL sections, classify each question:
   - **Any tech choice question** (generic tech stack OR feature-specific tech selection) → Skip entirely, never ask
   - **Business requirement/configuration question** → Keep in appropriate section

   Tech choice questions include ANY question asking about:
   - Which library/component/tool to use
   - How to implement using specific technology
   - Which API/SDK/framework to choose
   - Technology configuration details (vs. business configuration)

   **❌ SKIP entirely (Generic - already known in COMMON_KNOWLEDGE.md):**
   - Database selection (Known: MySQL for actual deployment, supports PostgreSQL/Oracle/SQL Server)
   - Frontend framework (Known: React 16.9.0 JavaScript, NOT TypeScript)
   - UI component library (Known: Ant Design 3.26.20)
   - Backend framework (Known: Java 8, Spring Boot 2.3.2, Spring Cloud Hoxton.SR9)
   - Microservices architecture (Known: Yes, Spring Cloud with Nacos)
   - Message queue (Known: RabbitMQ)
   - Cache solution (Known: Redis)
   - File storage (Known: MinIO)
   - API documentation (Known: Swagger 2.9.2)
   - ORM framework (Known: JPA, MyBatis, MyBatis-Plus)
   - State management (Known: Redux)
   - Frontend routing (Known: React Router 4)
   - Build tools (Known: Webpack + Yarn)
   - TypeScript usage (Known: No, uses JavaScript)
   - Service registration (Known: Nacos)
   - Configuration management (Known: Nacos Config)

   **❌ ALSO SKIP (Feature-specific tech choices - developer decisions, not PM requirements):**
   - "导出功能使用哪个Excel处理库?" → Developer decision, not business requirement
   - "进度图使用哪个可视化组件?" → Developer decision, not business requirement
   - "此功能需要调用哪些外部API?" → Only ask if PRD explicitly mentions external system integration
   - "数据如何在Redis中缓存?" → Developer decision on cache implementation
   - "使用哪个RabbitMQ交换机?" → Developer decision on messaging implementation
   - "文件上传使用什么组件?" → Developer decision, not business requirement

   **✅ KEEP (Business requirements and configurations):**
   - "导出数据量限制是多少?" → Business boundary condition
   - "缓存过期时间设置为多久?" → Business configuration requirement
   - "外部系统接口协议是什么?" → Business integration requirement (only if PRD mentions external system)
   - "审批通知的内容包含哪些字段?" → Business requirement
   - "进度图展示哪些维度的数据?" → Business requirement
   - "文件上传支持哪些格式?" → Business requirement

   **Rule 2.1: Tech Choice Question Detection Patterns**

   A question is considered a "tech choice question" if it matches ANY of these patterns:

   **Pattern A: Direct Tech Selection**
   - "使用什么[技术/库/组件/框架]"
   - "选择哪个[库/工具/技术]"
   - "采用什么技术实现"
   - "[功能]用什么库"
   - Question contains specific technology library/tool option lists

   **Pattern B: Tech Implementation Method**
   - "如何实现[技术细节]" (when question focuses on technical means, not business requirements)
   - "使用哪个API/SDK/组件"
   - "通过什么技术/组件实现"

   **Complete Examples of Tech Choice Questions to SKIP:**
   ```markdown
   ❌ "导出功能使用哪个Excel处理库?" → Technology selection
   ❌ "进度图使用哪个可视化组件?" → Technology selection
   ❌ "数据如何在Redis中缓存?" → Technical implementation detail
   ❌ "使用哪个RabbitMQ交换机?" → Technology configuration
   ❌ "审批通知通过哪个消息队列发送?" → Technology selection
   ❌ "文件上传使用什么组件?" → Technology selection
   ❌ "采用什么加密算法?" → Technology selection
   ❌ "使用哪个日期处理库?" → Technology selection
   ```

   **Complete Examples of Business Questions to KEEP:**
   ```markdown
   ✅ "导出数据量限制是多少?" → Business boundary condition
   ✅ "缓存过期时间设置为多久?" → Business configuration requirement
   ✅ "审批通知的内容包含哪些字段?" → Business requirement
   ✅ "文件上传支持哪些格式?" → Business requirement
   ✅ "进度图展示哪些维度的数据?" → Business requirement
   ✅ "用户权限如何划分?" → Business requirement
   ✅ "审批流程包含哪些步骤?" → Business requirement
   ```

   **Application Scope:**
   - **Section 2 (技术栈)**: MOST CRITICAL - Skip ALL questions, only pre-fill from COMMON_KNOWLEDGE.md
   - **Section 5 (数据Schema映射)**: Skip database type questions, ask only schema structure details
   - **Section 6 (操作详细规范)**: Skip generic framework/tool questions, place feature-specific tech choices here
   - **All sections**: Filter out any generic tech stack questions everywhere

   **Example - What to SKIP (Never generate these questions anywhere):**
   ```markdown
   ❌ "使用什么数据库?" → Already known (MySQL)
   ❌ "前端使用React还是Vue?" → Already known (React 16.9.0)
   ❌ "是否需要TypeScript?" → Already known (No, JavaScript only)
   ❌ "API文档工具选择?" → Already known (Swagger 2.9.2)
   ❌ "是否采用微服务架构?" → Already known (Yes, Spring Cloud)
   ❌ "消息队列选型?" → Already known (RabbitMQ)
   ❌ "缓存使用什么?" → Already known (Redis)
   ❌ "文件存储方案?" → Already known (MinIO)
   ```

   **Example - Updated Approach (Skip ALL tech choices):**

   **Scenario: PRD mentions "导出质量数据为Excel报表"**

   **❌ OLD approach (Feature-specific tech questions in Section 6 - NO LONGER VALID):**
   ```markdown
   <!-- clarification:start,id=c-6.6-1,type=tech_choice,... -->
   **Excel处理库选择:**
   - [ ] Apache POI
   - [ ] EasyExcel
   - [ ] 其他: ___________
   <!-- clarification:end -->
   ```
   **Reasoning:** "Excel处理库选择" is a technology implementation detail → Developer decides based on project standards

   **✅ NEW approach (Skip tech choice, keep business requirements):**
   ```markdown
   ### 6.6 导出操作

   **操作ID:** export-quality-data
   **触发条件:** 用户点击"导出"按钮
   **输入参数:**
   - 导出范围: 当前筛选条件、全部数据、选中数据
   - 导出格式: Excel (.xlsx)

   **业务逻辑:**
   1. 根据导出范围查询数据
   2. 生成 Excel 文件
   3. 返回下载链接

   <!-- clarification:start,id=c-6.6-1,type=boundary,section=6.6,prd_ref=需补充,priority=medium,status=pending -->
   **导出数据量限制:**
   - 单次导出最多支持 _______ 条记录
   - 超过限制时如何处理: [ ] 分批导出 [ ] 报错提示 [ ] 后台任务
   <!-- clarification:end -->

   <!-- clarification:start,id=c-6.6-2,type=business_logic,section=6.6,prd_ref=需补充,priority=high,status=pending -->
   **导出内容范围:**
   - [ ] 当前筛选结果
   - [ ] 全部数据
   - [ ] 用户选中的记录
   <!-- clarification:end -->

   **输出结果:** Excel文件下载链接
   **异常处理:** 数据量超限、生成失败
   **PRD定位:** 行xxx-xxx
   ```

   **Key differences:**
   - ❌ "Excel处理库选择" is a tech implementation detail → Skip entirely
   - ✅ "导出数据量限制" is a business requirement → PM must specify based on business needs
   - ✅ "导出内容范围" is a business requirement → PM must clarify expected user behavior

7. **Generate and Validate `docs/PRD-Gen/clarification.md`** 🔴 CRITICAL: DO NOT SKIP VALIDATION

   **Part A: Generate Clarification Document**
   - **IMPORTANT**: Always use the fixed filename `docs/PRD-Gen/clarification.md`
   - Use the template structure from `openspec/PRD_ANALYSIS_STANDARD.md` Section 2
   - **Write all content in the PRD's language** (detected in Step 5)
   - Add module metadata header:
     ```markdown
     # OpenSpec提议澄清文档: [Module Name]

     > **Module ID:** [module-id]
     > **PRD来源:** [section] [Module Name] (行[start]-[end])
     > **PRD文件:** [prd-file-path]
     > **生成时间:** [YYYY-MM-DD]
     > **文档状态:** 待产品经理审阅
     ```
   - **FORMAT REQUIREMENTS** (Machine-Readable Structure):
     1. **HTML Metadata Comments** - Add before each section/operation/component:
        ```markdown
        <!-- meta:section=1,type=business_value -->
        ## 1. 业务价值

        <!-- meta:section=6.1,operation_id=op1,prd_section=6.1.3,prd_lines=212-214,operation_name=进度条查看 -->
        ### 6.1 操作1: 进度条查看

        <!-- meta:input_spec,operation_id=op1 -->
        #### 输入规范
        ```
     2. **Table Format** - ALL tables MUST include "PRD定位" column:
        ```markdown
        | 字段名 | 类型 | 必填 | 说明 | PRD定位 |
        |--------|------|------|------|---------|
        | problem_id | String | 是 | 问题ID | [PRD:行217] |
        | team_leaders | JSON | 是 | 小组领导者 | [PRD:行217-小组领导者] |
        | extension_data | JSON | 否 | 扩展字段 | [需补充] |
        ```
        Valid PRD location formats:
        - `[PRD:行214]` - Exact line number
        - `[PRD:行217-小组领导者]` - Line number + specific content
        - `[需补充]` - Needs PM to supplement
        - `[推断]` - Inferred from context
        - `[系统生成]` - System generated
     3. **Section Types** - Use standardized section_type values:
        - `business_value` - Section 1 (业务价值)
        - `tech_stack` - Section 2 (技术栈)
        - `ui_ux` - Section 3 (UI/UX资源)
        - `scope` - Section 4 (范围确认)
        - `data_schema` - Section 5 (数据Schema映射)
        - `operations` - Section 6 (操作详细规范)
        - `blockers` - Section 9 (阻塞项清单)
     4. **Operation Components** - Each operation MUST have:
        - `basic_info` - 基本信息 (operation name, PRD reference, permissions)
        - `input_spec` - 输入规范 (input fields with types and validation)
        - `output_spec` - 输出规范 (output fields with types and examples)
        - `scenarios` - 场景列表 (WHEN...THEN scenarios with priorities)
        - `errors` - 错误处理 (error codes and messages)
        - `boundaries` - 边界条件 (constraints and limits)
        - `test_cases` - 测试用例 (concrete test scenarios)
   - For Section B (Features): List each OPERATION from FEATURE_TREE and apply the "🚨 OpenSpec Testability Check"
   - For Section C (Data): Create schema mapping tables for each data source mentioned
   - For Section D (Interface): Create input/output specs for each operation
   - For Section E (Tests): Extract any test criteria mentioned in PRD
   - Fill in "Critical Blockers Summary" based on missing information
   - **Language Guidelines**:
     - Section headers: Use PRD language (e.g., "## 1. 业务价值" for Chinese)
     - Questions/prompts: Use PRD language
     - Technical terms: Keep in English (WHEN, THEN, SHALL, API, JSON, etc.)
     - Code examples: Always in English

   **7.5 Clarification Question Formatting Rules**

   When generating clarification questions (especially in "待明确" sections), ALWAYS use structured formats:

   **Rule 1: Convert Yes/No Questions → Checkboxes**
   - If question has 2-3 possible answers → Use checkbox list
   - Apply this to: Logic rules, workflow modes, processing methods, scope decisions
   - Always include "其他: ___________" option for flexibility
   - Example:
     ```markdown
     **审批流转模式:**
     - [ ] 串行审批(逐层依次审批)
     - [ ] 并行审批(所有层级同时进行)
     - [ ] 其他: ___________
     ```

   **Rule 2: Convert Logic/Rule Questions → Checkbox with Description**
   - If question explains a rule or logic → Convert to checkbox with explanation
   - Apply this to: Business rules, validation logic, calculation methods
   - Example:
     ```markdown
     **或签逻辑确认:**
     - [ ] 或签为true时任意一人通过即可，为false时所有人都需通过
     - [ ] 采用其他规则: ___________
     ```

   **Rule 3: Convert Numeric/Limit Questions → Fill-in-the-blank**
   - If question asks for numbers, limits, ranges → Use blank line format
   - Apply this to: Quantity limits, time ranges, size constraints
   - Example:
     ```markdown
     **审批层级限制:**
     - 最多支持 _______ 个审批层级
     - 每层最多 _______ 个审批人
     ```

   **Rule 4: NEVER Use Unstructured Blockquote Lists**
   - ❌ WRONG:
     ```markdown
     > **待明确:**
     > - Question 1?
     > - Question 2?
     ```
   - ✅ RIGHT:
     ```markdown
     **Topic Title:**
     - [ ] Option 1 (explanation)
     - [ ] Option 2 (explanation)
     - [ ] 其他: ___________
     ```

   **Rule 5: Group Related Questions Under Same Topic**
   - Combine related questions into one structured block
   - Example: Group all approval logic questions together, not separately
   - Each group should have a clear topic title

   **Rule 6: Deduplication - NO Duplicate Questions**
   - Before adding a clarificationon, check if the same question already exists
   - If a similar question is found in any section, skip adding the duplicate
   - Maintain a running list of all questions to prevent duplication across sections
   - Use semantic similarity matching (e.g., "审批流转模式" and "审批模式" are the same)
   - Example of deduplication:
     ```markdown
     ❌ WRONG (duplicate):
     Section 5: **审批流转模式:** [checkboxes]
     Section 6: **审批模式:** [checkboxes]  # This is a duplicate!

     ✅ RIGHT (deduplicated):
     Section 5: **审批流转模式:** [checkboxes]
     Section 6: (No duplicate question, reuse reference to Section 5)
     ```

   **Rule 7: Consolidate Clarification Questions in Dedicated Section**
   - Create a new "待澄清问题汇总" (Clarification Questions Summary) section
   - Place ALL clarification questions in this dedicated section
   - Organize by category: Data Schema, UI/UX, Business Logic, Technical Decisions
   - Link back to relevant sections in the document
   - Format:
     ```markdown
     ## 待澄清问题汇总

     ### 数据Schema相关
     **[Section 5.1] 用户权限字段:**
     - [ ] 使用角色ID引用 (role_id)
     - [ ] 使用权限位掩码 (permission_bits)
     - [ ] 其他: ___________

     ### UI/UX交互相关
     **[Section 3.2] 审批流转模式:**
     - [ ] 串行审批(逐层依次审批)
     - [ ] 并行审批(所有层级同时进行)
     - [ ] 其他: ___________
     ```

   **Scope Guidance (Default: Option A)**:
   - Apply structured formats to: Boundary conditions, logic rules, technical decisions, numeric limits
   - Apply deduplication to ALL sections before generating final document
   - Consolidate ALL questions in dedicated "待澄清问题汇总" section
   - Target sections: Section 5 (Data Schema), Section 6 (Operations), boundary condition tables

   **7.6 HTML Comment Wrapper for Clarification Questions** 🆕

   **ALL clarification questions MUST be wrapped with HTML comments for frontend parsing:**

   **Format Specification:**
   ```html
   <!-- clarification:start,id={id},type={type},section={section_id},prd_ref={prd_ref},priority={priority},status=pending -->
   **Question Topic:**
   - [ ] Option 1 (explanation)
   - [ ] Option 2 (explanation)
   - [ ] 其他: ___________
   <!-- clarification:end -->
   ```

   **ID Generation Rules:**
   - Format: `c-{section}-{number}` or `c-{section}-op{op_id}-{number}`
   - Examples:
     * `c-2-1` (Section 2, Question 1)
     * `c-5.2-3` (Section 5.2, Question 3)
     * `c-6.1-op1-2` (Section 6.1, Operation 1, Question 2)
   - Must be unique within document
   - Sequential numbering within each section

   **Type Classification:**
   - `tech_choice`: Framework/tool selection, technology decisions
   - `data_schema`: Data structure, field definitions, data types
   - `business_logic`: Business rules, workflows, process logic
   - `ui_ux`: Interface design, interaction patterns, visual elements
   - `boundary`: Limits, constraints, thresholds, capacity
   - `integration`: External systems, APIs, third-party services

   **Priority Levels:**
   - `high`: Blocking implementation, must be answered first
   - `medium`: Important but not blocking
   - `low`: Nice to have, can be deferred

   **Complete Example:**
   ```markdown
   <!-- clarification:start,id=c-5.2-1,type=data_schema,section=5.2,prd_ref=行217,priority=high,status=pending -->
   **审批人员配置存储格式:**
   - [ ] 使用 JSON 类型 (MySQL 5.7+)
   - [ ] 使用 TEXT 类型存储 JSON 字符串
   - [ ] 其他: ___________
   <!-- clarification:end -->

   <!-- clarification:start,id=c-5.2-2,type=business_logic,section=5.2,prd_ref=行217,priority=high,status=pending -->
   **或签逻辑确认:**
   - [ ] 或签为true时任意一人通过即可，为false时所有人都需通过
   - [ ] 采用其他规则: ___________
   <!-- clarification:end -->

   <!-- clarification:start,id=c-5.2-3,type=boundary,section=5.2,prd_ref=需补充,priority=medium,status=pending -->
   **审批层级限制:**
   - 最多支持 _______ 个审批层级
   - 每层最多 _______ 个审批人
   <!-- clarification:end -->
   ```

   **Wrapping Rules:**
   1. **All questions in Rule 1-7 must be wrapped** (checkboxes, fill-in-the-blank, etc.)
   2. **Wrap immediately around the question block** (from topic title to last option)
   3. **Do not wrap table headers or PRD location notes** (only the questions)
   4. **Each question gets its own wrapper** (no grouping multiple questions in one wrapper)
   5. **Ensure proper nesting** (no overlapping wrappers)

   **Application Order:**
   - First: Apply tech stack filtering (Step 6.5)
   - Second: Apply structured formatting (Rules 1-7)
   - Third: Apply HTML wrappers to all structured questions
   - Fourth: Validate format with Python script

   **Part B: IMMEDIATELY Run Validation (MANDATORY - DO NOT SKIP)**
   🚨 **STOP! Before proceeding to Step 8, you MUST run validation:**

   Run this command RIGHT AFTER generating clarification.md:
   ```bash
   cd .claude/script && python generate_clarification_index.py
   ```

    This will:
   1. Parse the markdown file
   2. Generate `clarification_index.json` with navigation indices
   3. Validate the format automatically
   4. Check structured format compliance (Section 7.5 rules):
      - No unstructured blockquote lists with "待明确:" pattern
      - All clarification questions use structured formats (checkboxes or fill-in-the-blank)
      - Boundary conditions and logic rules use structured formats
      - Numeric/limit questions use fill-in-the-blank format

   **If validation FAILS:**
   - Display validation errors to user
   - **Format compliance errors**: If unstructured "待明确:" blockquotes detected:
     * Identify the section(s) with unstructured questions
     * Convert to structured format per Section 7.5 rules
     * Re-generate clarification.md with corrected format
   - Fix other issues in `clarification.md` (metadata, tables, PRD定位)
   - Re-run validation until it PASSES
   - DO NOT proceed to Step 8 until validation succeeds

   **If validation PASSES:**
   - Confirm both files are ready
   - Show validation statistics:
     * ✅ Sections: [count]
     * ✅ Operations: [count]
     * ✅ Scenarios: [count]
     * ✅ Validation passed!
   - Generated files:
     * ✅ docs/PRD-Gen/clarification.md (human-readable)
     * ✅ docs/PRD-Gen/clarification_index.json (machine-readable)

8. **Output Summary** (Only after validation passes)
   After successful generation and validation, provide:
   - Module name and ID
   - Number of operations identified
   - Number of scenarios generated
   - Number of critical blockers found
   - Validation status (✅ or ❌)
   - Files generated:
     * `docs/PRD-Gen/clarification.md` - Human-readable questionnaire
     * `docs/PRD-Gen/clarification_index.json` - Machine-readable index
   - Statistics summary:
     * Total sections
     * Total operations with all required components
     * PRD coverage percentage
     * Required items vs optional items
   - Recommended next steps for PM

9. **Handle Review Messages (Iterative Refinement)**
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
User: /analyze-prd --module "D1组建团队" --feature-tree "docs/PRD-Gen/FEATURE_TREE.md" --prd "doc/System-Design_text_only.md"

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
       [Generates docs/PRD-Gen/clarification.md in Chinese with format markers]

       📝 Generating clarification.md with machine-readable format...
       ✅ Generated docs/PRD-Gen/clarification.md

       🔨 Running validation and index generation...
       📝 Parsing clarification.md...
       🔨 Generating index...
       💾 Writing to clarification_index.json...

       ✅ Generation complete!
          - Sections: 11
          - Operations: 9
          - Scenarios: 27

       🔍 Running validation...
       ✅ Validation passed!

       📊 Summary:
       - Module: D1组建团队 (d1-team-formation)
       - Operations: 9 (all with required components)
       - Scenarios: 27 testable scenarios generated
       - Critical blockers: 6
         * 业务价值量化指标缺失 (Section 1.2)
         * 甘特图组件选型未定 (Section 2.5)
         * UI/UX蓝湖链接待提供 (Section 3)
         * 扩展字段定义缺失 (Section 5.3)
         * 测试数据需求未明确 (Section 8)
       - PRD Coverage: 72.7% (8/11 lines covered)

       📁 Generated Files:
       ✅ docs/PRD-Gen/clarification.md (human-readable)
       ✅ docs/PRD-Gen/clarification_index.json (machine-readable)

       🎯 Next Steps:
       1. 产品经理填写clarification.md中的待填写项
       2. 确认或更新"待确认"的范围项
       3. 解决6个阻塞项
       4. 运行 /openspec:proposal 生成正式提议
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

**Example 4: Structured Clarification Questions (After Formatting Rules Update)**
```
User: /analyze-prd --module "D1组建团队" --feature-tree "docs/PRD-Gen/FEATURE_TREE.md" --prd "doc/System-Design_text_only.md"

Agent: [Reads FEATURE_TREE.md and PRD]
       [Applies 4-pass analysis]
       [Generates clarification.md with NEW structured format]

       📝 Section 5.4 (审批节点配置) now uses structured questions:

       ```markdown
       ### 5.4 审批节点人员配置存储

       | 字段名 | 数据类型 | 必填 | 说明 | PRD定位 |
       |--------|---------|------|------|------------|
       | approval_level | INT | 是 | 审批层级 | [PRD:行217-审批层级] |
       | user_ids | JSON | 是 | 审批人员ID列表 | [PRD:行217-下拉多选框] |
       | is_or_sign | BOOLEAN | 是 | 是否或签 | [PRD:行217-或签，默认为关] |

       > **待明确:**

       **或签逻辑确认:**
       - [ ] 或签为true时任意一人通过即可，为false时所有人都需通过
       - [ ] 采用其他规则: ___________

       **审批流转模式:**
       - [ ] 串行审批（逐层依次审批）
       - [ ] 并行审批（所有层级同时进行）
       - [ ] 混合模式: ___________

       **审批流转处理方式:**
       - [ ] 由工作流引擎统一处理
       - [ ] 自研审批逻辑
       - [ ] 其他: ___________

       **审批层级限制:**
       - 最多支持 _______ 个审批层级
       - 每层最多 _______ 个审批人

       **PRD定位:** [需补充] - PRD未明确审批流转逻辑细节
       ```

       ✅ Benefits of structured format:
       - PM can quickly check boxes instead of writing free text
       - Machine-parsable for tracking completion status
       - Clearer options reduce ambiguity
       - Fill-in-the-blank prompts for numeric values

       🔨 Running validation...
       ✅ Validation passed! All clarification questions use structured formats.

       📊 Summary:
       - Module: D1组建团队 (d1-team-formation)
       - Operations: 8 (all with structured clarification questions)
       - Structured questions: 45 (checkboxes: 32, fill-in-the-blank: 13)
       - Format compliance: 100% ✅
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
- **Format compliance is mandatory**:
  - All sections must have HTML metadata comments
  - All tables must have "PRD定位" column
  - All operations must have 7 required components
  - Validation will fail if format requirements are not met
- **Validation tools**:
  - `generate_clarification_index.py` - Main generation and validation tool
  - `validate_with_schema.py` - JSON Schema validation (optional)
  - `example_usage.py` - Usage examples for working with the generated index
- **Documentation**:
  - `docs/PRD-Gen/README.md` - Complete usage guide
  - `docs/PRD-Gen/IMPLEMENTATION_GUIDE.md` - Implementation and integration guide
  - `docs/PRD-Gen/clarification_schema.json` - JSON Schema definition
- **Automatic validation ensures**:
  - Metadata completeness (module_id, prd_file, prd_section, etc.)
  - Structural integrity (valid section types, operation IDs)
  - Navigation index consistency (all references are valid)
  - PRD traceability (all items link back to PRD source)

