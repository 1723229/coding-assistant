---
name: Analyze PRD
description: Convert a vague PRD into a structured clarification list for OpenSpec proposal generation
category: project
tags: [prd, analysis, openspec, clarification]
---

**Objective**
Convert the provided PRD into `openspec/prd-context.md` - a structured questionnaire that PM can fill to enable OpenSpec proposal generation.

**Guardrails**
- Follow the 4-pass analysis algorithm defined in `openspec/PRD_ANALYSIS_STANDARD.md`
- Every clarification question MUST serve the goal of writing testable OpenSpec Scenarios (`WHEN...THEN` format)
- Flag features that cannot be decomposed into concrete input/output as BLOCKERS
- Use the exact template structure from `PRD_ANALYSIS_STANDARD.md` Section 2
- **IMPORTANT**: Generate `openspec/prd-context.md` in the SAME LANGUAGE as the input PRD
  - If PRD is in Chinese, output in Chinese
  - If PRD is in English, output in English
  - Keep technical terms and OpenSpec keywords (WHEN, THEN, SHALL) in English regardless of language

**Prerequisites**
1. User must provide a PRD file (PDF/Markdown/Text)
2. Read `openspec/PRD_ANALYSIS_STANDARD.md` to understand the analysis standard

**Steps**

1. **Read the Standard**
   - Read `openspec/PRD_ANALYSIS_STANDARD.md` to internalize the 4-pass algorithm

2. **Detect PRD Language**
   - Identify the primary language of the PRD (Chinese, English, etc.)
   - All subsequent output in `prd-context.md` MUST use this language
   - Exception: Keep OpenSpec technical terms in English (WHEN, THEN, SHALL, etc.)

3. **Execute Four-Pass Analysis**
   Apply each pass to the PRD:
   - **Pass 1**: Value & Root Need Check → Extract for Section A (Business Value)
   - **Pass 2**: Developer Onboarding Check → Extract for Section F (Tech Stack)
   - **Pass 3**: Technical Ambiguity Check → Extract for Sections C (Data Schema) & D (UI/UX)
   - **Pass 4**: Scenario Decomposition Check → Extract for Section B (Feature Breakdown)

4. **Generate `openspec/prd-context.md`**
   - Use the exact template from `openspec/PRD_ANALYSIS_STANDARD.md` Section 2
   - **Write all content in the PRD's language** (detected in Step 2)
   - For Section B (Features): List each PRD feature and apply the "🚨 OpenSpec Testability Check"
   - For Section C (Data): Create schema mapping tables for each data source mentioned
   - For Section E (Tests): Extract any test criteria mentioned in PRD
   - Fill in "Critical Blockers Summary" based on missing information
   - **Language Guidelines**:
     - Section headers: Use PRD language (e.g., "## 章节 A: 业务价值" for Chinese)
     - Questions/prompts: Use PRD language
     - Technical terms: Keep in English (WHEN, THEN, SHALL, API, JSON, etc.)
     - Code examples: Always in English

5. **Validate Completeness**
   - Ensure every feature has the 5 clarification sub-sections (Input/Output/Examples/Errors/Boundaries)
   - Ensure at least one concrete WHEN...THEN example is requested for each feature
   - Mark items that block OpenSpec generation in the Critical Blockers section

5. **Output Summary**
   After generating `openspec/prd-context.md`, provide a brief summary:
   - Number of features identified
   - Number of critical blockers found
   - Recommended next steps for PM

**Reference**
- Standard: `openspec/PRD_ANALYSIS_STANDARD.md`
- OpenSpec conventions: `openspec/AGENTS.md`
- Project context: `openspec/project.md`

**Example Usage**

Example 1: Chinese PRD
```
User: /analyze-prd
      [Attaches PRD.pdf in Chinese]

Agent: [Detects language: Chinese]
       [Reads openspec/PRD_ANALYSIS_STANDARD.md]
       [Executes 4-pass analysis]
       [Generates openspec/prd-context.md in Chinese]

       ✅ 已生成 openspec/prd-context.md

       摘要:
       - 识别到 3 个功能 (问数配置, 报表生成, 数据获取)
       - 发现 4 个关键阻塞项:
         * MES/ERP API schema 缺失
         * 查询的输入输出格式未定义
         * 测试 Ground Truth 未提供
         * 报表视觉设计缺失

       下一步: 请填写 openspec/prd-context.md，然后运行 /openspec:proposal
```

Example 2: English PRD
```
User: /analyze-prd
      [Attaches PRD.pdf in English]

Agent: [Detects language: English]
       [Reads openspec/PRD_ANALYSIS_STANDARD.md]
       [Executes 4-pass analysis]
       [Generates openspec/prd-context.md in English]

       ✅ Generated openspec/prd-context.md

       Summary:
       - 3 features identified (Query Configuration, Report Generation, Data Sync)
       - 4 critical blockers:
         * MES/ERP API schema missing
         * Query input/output format undefined
         * Test Ground Truth not provided
         * Report visual design missing

       Next: Please fill openspec/prd-context.md, then run /openspec:proposal
```
