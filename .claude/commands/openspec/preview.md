---
name: OpenSpec: Preview
description: Preview frontend implementation with mocked data before backend is ready on an approved OpenSpec change
tags: [openspec, preview]
---

# OpenSpec Preview Implementation Workflow

Implement frontend UI with mocked data as a preview before backend database is configured, allowing rapid iteration and early validation of UX/UI design.

## When to Use This Approach

Use preview implementation when:
- You want to validate UI/UX design with stakeholders early **before backend exists**
- You need rapid UX feedback iteration without waiting for database/backend setup
- You want to demonstrate visual progress and user flows immediately
- The backend implementation will be done later (using `/openspec:apply`)

## ⚠️ CRITICAL: Preview = Frontend ONLY

**DO NOT implement backend during preview!**
- ✅ Create frontend pages with mocked data
- ✅ Implement UI components and navigation
- ✅ Add routing and internationalization
- ❌ DO NOT create backend entities, services, controllers
- ❌ DO NOT set up database or Nacos configuration
- ❌ DO NOT write any Java/Spring Boot code

The backend will be implemented later when you run `/openspec:apply`.

## Arguments

The user will provide: `<change-id>`

## Standard Directory Structure

All preview artifacts should follow this standardized structure:

```
openspec/changes/<change-id>/
├── proposal.md              # Original change proposal
├── design.md                # Design document
├── tasks.md                 # Implementation tasks
├── specs/                   # Detailed specifications
├── PREVIEW_SUMMARY.md       # ✅ Preview implementation summary (CREATE THIS)
└── screenshots/             # ✅ All preview screenshots (CREATE THIS)
    ├── {feature}-list-with-mock-data.png
    ├── {feature}-detail-page.png
    ├── {feature}-create-edit-form.png
    └── ... (minimum 4 screenshots)
```

**Key Files to Create:**
1. **PREVIEW_SUMMARY.md** - Complete documentation of your preview implementation
2. **screenshots/** directory - Organized storage of all UI screenshots

## Preview Implementation Steps

### Step 0: Environment Setup (MANDATORY FIRST STEP)

**⚠️ CRITICAL: Verify Node.js Version BEFORE Starting**

```bash
# Check current Node.js version
node --version

# If not 14.x, switch immediately
nvm use 14

# Verify switch was successful
node --version  # MUST show v14.x.x

# Also verify yarn
yarn --version
```

**Why This Matters:**
- ❌ Node.js 16+ will cause compilation errors
- ❌ Ant Design 3.26.20 requires Node.js 14.x
- ❌ HVisions framework incompatible with newer Node versions
- ⚠️ You'll waste hours debugging if using wrong version

**Example Errors if Wrong Version:**
```
Module not found: Can't resolve 'xxx'
Invalid hook call. Hooks can only be called inside...
```

**Pre-Flight Checklist:**
- [ ] Node.js 14.x active (`nvm use 14`)
- [ ] Yarn installed and working
- [ ] Frontend dependencies installed (`cd frontend && yarn install`)
- [ ] Dev server starts without errors (`yarn start`)

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
- What UI screens/pages are needed?
- What data will be displayed?
- What user interactions are required?

**Extract from specs/*/spec.md:**
- List ALL UI-related requirements
- Identify form fields, table columns, filters
- Note validation rules and error messages

**Extract from design.md (if exists):**
- What are the expected API endpoints (for mocking)?
- What data structure should be returned?

### 3. Analyze Existing Reference Pages

**Find Similar Pages:**
```bash
# Look for similar UI patterns in the codebase
ls frontend/src/pages/
# Study existing list pages, forms, detail pages
```

**Study UI Patterns:**
- How are list pages structured?
- How are forms handled (create/edit)?
- What Ant Design components are commonly used?
- How is pagination implemented?
- How are filters structured?

### 4. Implement Service Layer with Mock Data (MANDATORY)

**🎯 Mock Data is REQUIRED for Preview**

Without mock data:
- ❌ UI shows empty tables and 404 errors
- ❌ Poor stakeholder experience
- ❌ Cannot test CRUD operations
- ❌ Cannot demonstrate user flows

**Create Service Class with Mock Data** (`src/api/<ServiceName>.js`):

```javascript
import BaseService from './BaseService';

// ============ MOCK DATA FOR PREVIEW (Remove when backend is ready) ============
const PREVIEW_MODE = true; // Set to false when backend is implemented

let mockData = [
  {
    id: 1,
    code: 'QT00001',
    name: '标准8D问题类型',
    solutionMethod: '8D',
    remarks: '适用于复杂质量问题的标准8D流程，包含完整的团队协作和根因分析',
    enabled: true,
    createTime: '2024-11-15 09:30:00',
    updateTime: '2024-11-20 14:25:00',
    createUser: '张三',
    updateUser: '李四',
    workflow: {
      nodes: [
        // Complex workflow example
      ]
    }
  },
  {
    id: 2,
    name: '精益改善问题类型',
    solutionMethod: 'Lean',
    enabled: true,
    // ... more fields
  },
  {
    id: 3,
    name: '简单问题解决类型',
    solutionMethod: 'Simple',
    enabled: true,
    // ... more fields
  },
  {
    id: 4,
    name: '禁用示例',
    enabled: false,  // Example of disabled record
    // ... more fields
  },
  // Add 2-6 more realistic examples covering different scenarios
];

let nextId = mockData.length + 1;

class ServiceName extends BaseService {
  async getList(queryParams = {}) {
    if (PREVIEW_MODE) {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 300));

      const { code, name, solutionMethod, enabled, page = 0, pageSize = 20 } = queryParams;

      // Implement filtering logic
      let filtered = [...mockData];

      if (code) {
        filtered = filtered.filter(item =>
          item.code.toLowerCase().includes(code.toLowerCase())
        );
      }
      if (name) {
        filtered = filtered.filter(item =>
          item.name.toLowerCase().includes(name.toLowerCase())
        );
      }
      if (solutionMethod) {
        filtered = filtered.filter(item => item.solutionMethod === solutionMethod);
      }
      if (enabled !== undefined && enabled !== null && enabled !== '') {
        filtered = filtered.filter(item => item.enabled === enabled);
      }

      // Implement pagination
      const start = page * pageSize;
      const end = start + pageSize;
      const content = filtered.slice(start, end);

      return {
        content,
        totalElements: filtered.length,
        totalPages: Math.ceil(filtered.length / pageSize),
        number: page,
        size: pageSize
      };
    }

    // Real backend call
    return await this.post('/api/endpoint/list', queryParams);
  }

  async getById(id) {
    if (PREVIEW_MODE) {
      await new Promise(resolve => setTimeout(resolve, 200));
      const record = mockData.find(item => item.id === parseInt(id));
      if (!record) {
        throw new Error('记录不存在');
      }
      return record;
    }
    return await this.get(`/api/endpoint/${id}`);
  }

  async create(data) {
    if (PREVIEW_MODE) {
      await new Promise(resolve => setTimeout(resolve, 500));

      const newRecord = {
        id: nextId++,
        code: data.code || `QT${String(nextId - 1).padStart(5, '0')}`,
        ...data,
        enabled: true,
        createTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
        updateTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
        createUser: '当前用户',
        updateUser: '当前用户'
      };

      mockData.push(newRecord);
      return newRecord;
    }
    return await this.post('/api/endpoint', data);
  }

  async update(id, data) {
    if (PREVIEW_MODE) {
      await new Promise(resolve => setTimeout(resolve, 400));

      const index = mockData.findIndex(item => item.id === parseInt(id));
      if (index === -1) {
        throw new Error('记录不存在');
      }

      mockData[index] = {
        ...mockData[index],
        ...data,
        updateTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
        updateUser: '当前用户'
      };

      return mockData[index];
    }
    return await this.put(`/api/endpoint/${id}`, data);
  }

  async delete(id) {
    if (PREVIEW_MODE) {
      await new Promise(resolve => setTimeout(resolve, 300));

      const index = mockData.findIndex(item => item.id === parseInt(id));
      if (index === -1) {
        throw new Error('记录不存在');
      }

      mockData.splice(index, 1);
      return { success: true };
    }
    return await this.delete(`/api/endpoint/${id}`);
  }

  async toggleEnable(id, enabled) {
    if (PREVIEW_MODE) {
      await new Promise(resolve => setTimeout(resolve, 300));

      const index = mockData.findIndex(item => item.id === parseInt(id));
      if (index === -1) {
        throw new Error('记录不存在');
      }

      mockData[index].enabled = enabled;
      mockData[index].updateTime = new Date().toISOString().replace('T', ' ').substring(0, 19);
      mockData[index].updateUser = '当前用户';

      return mockData[index];
    }
    return await this.put(`/api/endpoint/${id}/enable`, { enabled });
  }
}

export default new ServiceName();
```

**Mock Data Best Practices:**

**Minimum Requirements:**
- ✅ 5-10 realistic sample records
- ✅ Different states (enabled/disabled, active/inactive)
- ✅ Edge cases (empty fields, maximum length text)
- ✅ Complex and simple examples
- ✅ Different users (张三, 李四, 王五) for audit trail
- ✅ Different dates (recent, old)
- ✅ Relationships if applicable (parent-child, workflows)

**Variety Examples:**
```javascript
mockData = [
  { id: 1, name: '复杂示例', enabled: true, workflow: { /*complex*/ } },
  { id: 2, name: '简单示例', enabled: true, workflow: { nodes: [] } },
  { id: 3, name: '禁用示例', enabled: false, /* ... */ },
  { id: 4, name: '长文本示例', remarks: '很长很长的备注...' },
  // ... 2-6 more realistic examples
];
```

**CRITICAL Service Pattern:**
- Extend `BaseService` (local), NOT `@hvisions/toolkit` Service
- Use relative paths (`/list`, `/{id}`) with baseURL, not full URLs
- This prevents URL duplication (baseURL already includes full path)

### 5. Implement FULL Production UI Components

**🚨 CRITICAL: Do NOT Simplify UI for Preview**

**MUST Implement Full Production UI:**
- ✅ Drag-and-drop workflow designers (use React Flow, jsPlumb, etc.)
- ✅ All interactive components (modals, drawers, tabs, accordions)
- ✅ Complete form layouts with all fields
- ✅ Real navigation structure
- ✅ Full data grid with ALL columns
- ✅ All action buttons and menus
- ✅ Complex filters and search functionality

**Acceptable to Skip in Preview:**
- ✅ Complex animations (loading animations OK, fancy transitions can wait)
- ✅ Performance optimizations (can be slower with mock data)
- ✅ Real-time features (WebSocket, polling)
- ✅ Backend integration complexities

**NOT Acceptable to Simplify:**
- ❌ Replacing drag-and-drop with tables
- ❌ Removing UI components
- ❌ Changing page layouts
- ❌ Reducing functionality

**Example - Workflow Designer:**
- ✅ Use React Flow or jsPlumb for drag-and-drop
- ✅ Show node palette, canvas, property panels
- ✅ Allow dragging, connecting, configuring nodes
- ⚠️ Can skip: Auto-layout algorithms, advanced validations
- ❌ Don't replace with: Simple table configuration

**Rationale:**
- Preview validates actual user experience
- Stakeholder feedback on real UI prevents costly redesigns
- Implementation complexity similar whether preview or final
- Simplifying defeats the purpose of early UX validation

**Create UI Components:**

1. **List Page** (`pages/<Module>/<Feature>/index.js`)
   - Search filters
   - Data table with ALL columns
   - Action buttons (Create, Edit, Delete, Copy, etc.)
   - Pagination
   - Enable/disable toggles

2. **Detail Page** (`pages/<Module>/<Feature>/Detail.js`)
   - Read-only view of record
   - Display all fields and relationships
   - Collapsible sections
   - Back and Edit navigation

3. **Form Component** (`pages/<Module>/<Feature>/Form.js`)
   - Create/Edit mode handling
   - All form fields from requirements
   - Form validation (frontend)
   - Save/Cancel actions

4. **Complex Components** (if in requirements)
   - Workflow designers with drag-and-drop
   - Tree structures
   - File upload with preview
   - Rich text editors

**Add Routes** (`src/router.js`):
```javascript
const Feature = React.lazy(() => import('~/pages/<Module>/<Feature>'));
const FeatureDetail = React.lazy(() => import('~/pages/<Module>/<Feature>/Detail'));
const FeatureEdit = React.lazy(() => import('~/pages/<Module>/<Feature>/CreateEdit'));

export default [
  { path: '/<module>/<feature>', component: Feature, auth: false, exact: true },
  { path: '/<module>/<feature>/create', component: FeatureEdit, auth: false },
  { path: '/<module>/<feature>/edit/:id', component: FeatureEdit, auth: false },
  { path: '/<module>/<feature>/detail/:id', component: FeatureDetail, auth: false },
];
```

**Add Internationalization** (`src/locales/`):
- `zh_CN.js` - Chinese labels (primary) - COMPLETE ALL STRINGS
- `en_US.js` - English labels - COMPLETE ALL STRINGS

### 6. Document API Contract

**Create API documentation for backend developers:**

```markdown
## API Contract

**Base URL:** `/quality8d/api/problem-types`

### Endpoints

**POST /list** - Get paginated list
Request:
{
  code: string (optional),
  name: string (optional),
  page: number,
  pageSize: number
}

Response:
{
  content: [...],
  totalElements: number,
  totalPages: number
}

**GET /{id}** - Get by ID
Response: { id, code, name, ... }

**POST /** - Create new record
Request: { name, solutionMethod, ... }
Response: { id, code, name, ... }

**PUT /{id}** - Update record
Request: { name, remarks, ... }
Response: { id, code, name, ... }

**DELETE /{id}** - Delete record
Response: { success: true }
```

### 7. Test Frontend with Playwright

**Specific Test Checklist (Execute ALL):**

**Environment:**
- [ ] Node.js 14.x is active (`node --version`)
- [ ] Frontend dev server starts without errors (`yarn start`)
- [ ] No compilation errors

**UI Rendering:**
- [ ] List page loads with mock data visible
- [ ] Verify correct number of records (e.g., "共 6 条 记录")
- [ ] All columns display correctly
- [ ] No blank screens or React errors

**Interactive Features:**
- [ ] Click "新建" button → create/edit form appears
- [ ] Click "详情" button → detail page loads with data
- [ ] Click "编辑" button → edit page loads with pre-filled data
- [ ] Click "删除" button → confirmation modal appears
- [ ] Test enable/disable toggle → updates visually
- [ ] Test copy button (if applicable) → modal appears

**Search/Filter:**
- [ ] Enter filter values → click search
- [ ] Verify filtered results display correctly
- [ ] Test reset button → filters clear

**Navigation:**
- [ ] Navigate from list → detail → back to list
- [ ] Navigate from list → edit → back to list
- [ ] Verify browser back button works

**Data Display:**
- [ ] Chinese labels display correctly (primary language)
- [ ] English labels display correctly (toggle if possible)
- [ ] Dates formatted correctly
- [ ] Long text truncated with ellipsis/tooltip
- [ ] Different states visible (enabled/disabled, different types)

**Required Screenshots (MINIMUM 4):**
- [ ] `{feature}-list-with-mock-data.png` - List page with all records
- [ ] `{feature}-detail-page.png` - Detail page showing full record
- [ ] `{feature}-create-edit-form.png` - Create/edit form
- [ ] `{feature}-filtered-results.png` - Search results

**Screenshot Location:**
- Save to: `openspec/changes/<change-id>/screenshots/`
- Naming: `{feature}-{page-type}-{variant}.png`

**Console Check:**
- [ ] No React runtime errors
- [ ] Only expected warnings (prop-types, componentWillMount)
- [ ] No 404 errors (mock data prevents these)

**Playwright Test Code Example:**
```javascript
// Navigate to page
await page.goto('http://localhost:3000/<module>/<feature>');

// Verify mock data loads
await page.waitForSelector('text=共 6 条 记录');

// Take screenshot of list (save to standard location)
await page.screenshot({
  path: 'openspec/changes/<change-id>/screenshots/{feature}-list-with-mock-data.png'
});

// Click detail button
await page.locator('text=详情').first().click();
await page.waitForSelector('text=问题类型详情');

// Take screenshot of detail (save to standard location)
await page.screenshot({
  path: 'openspec/changes/<change-id>/screenshots/{feature}-detail-page.png'
});

// Test navigation
await page.locator('button:has-text("返回")').click();

// Test filter
await page.locator('text=请选择解决方法').click();
await page.locator('text=8D').first().click();
await page.locator('button:has-text("查询")').click();
await page.waitForTimeout(500);

// Take screenshot of filtered results (save to standard location)
await page.screenshot({
  path: 'openspec/changes/<change-id>/screenshots/{feature}-filtered-results.png'
});
```

## Common Frontend Patterns

**1. Page Component Structure:**
```javascript
class Page extends React.Component {
    state = {
        data: [],
        loading: false,
        pagination: { current: 1, pageSize: 20, total: 0 },
        filters: {}
    };

    componentDidMount() {
        this.loadData();
    }

    loadData = async () => {
        this.setState({ loading: true });
        try {
            const response = await Service.getList({
                ...this.state.filters,
                page: this.state.pagination.current - 1,
                pageSize: this.state.pagination.pageSize
            });
            this.setState({
                data: response.content || [],
                pagination: {
                  ...this.state.pagination,
                  total: response.totalElements || 0
                }
            });
        } catch (error) {
            notification.error({ message: '加载失败' });
        } finally {
            this.setState({ loading: false });
        }
    };
}
```

**2. Form Component Pattern:**
```javascript
const FormComponent = ({ form, initialValues, onSubmit }) => {
    const handleSubmit = async (values) => {
        try {
            if (initialValues?.id) {
                await Service.update(initialValues.id, values);
            } else {
                await Service.create(values);
            }
            notification.success({ message: '保存成功' });
            onSubmit();
        } catch (error) {
            notification.error({ message: '保存失败' });
        }
    };

    return (
        <Form form={form} onFinish={handleSubmit} initialValues={initialValues}>
            {/* Form fields */}
        </Form>
    );
};
```

## Common Problems and Solutions

### Problem 1: Wrong Node.js Version

**Symptom:** Compilation errors, module not found, blank screens

**Cause:** Using Node.js 16+ or latest instead of 14.x

**Solution:**
```bash
nvm use 14
node --version  # Verify it shows v14.x.x
# Restart dev server
cd frontend && yarn start
```

### Problem 2: URL Duplication in Service Calls

**Symptom:** API calls show duplicated URL like `http://localhost:9000/quality8d/api/problem-typeshttp://localhost:9000/quality8d/api/problem-types/list`

**Cause:** Using full URLs in methods when baseURL is already set

**Solution:**
```javascript
// ❌ Wrong
async getList() {
    return await this.post(`${this.baseURL}/list`, data);
}

// ✅ Correct
async getList() {
    return await this.post('/list', data);  // Relative path only
}
```

### Problem 3: Blank Screen or Component Errors

**Symptom:** Page loads but shows blank screen or console errors about missing components

**Cause:** Using incompatible component versions or incorrect Ant Design syntax

**Solution:**
- Verify Node.js 14.x is active: `nvm use 14` and `node --version`
- Ensure Ant Design 3.26.20 syntax is used (NOT version 4.x or 5.x)
- Check console for specific component errors
- Test with Playwright to catch rendering issues early

### Problem 4: React Class Component Warnings

**Symptom:** Deprecation warnings about componentWillMount, etc.

**Cause:** Legacy React patterns in HVisions framework (Ant Design 3.x)

**Solution:** These are framework warnings - safe to ignore. Use the existing patterns for consistency with the codebase.

### Problem 5: Chinese Characters Not Displaying

**Symptom:** UI shows squares or garbled text instead of Chinese characters

**Cause:** Missing locale configuration or incorrect file encoding

**Solution:**
- Ensure locale files (zh_CN.js, en_US.js) use UTF-8 encoding
- Verify ConfigProvider wraps the app with zh_CN locale
- Check browser encoding settings

### Problem 6: Routing Not Working

**Symptom:** Navigation doesn't change pages or shows 404

**Cause:** Routes not properly registered in router.js

**Solution:**
- Add route to `src/router.js` with correct path
- Use React.lazy() for code splitting
- Verify menu navigation uses correct path

## Files to Create Checklist

### Frontend

- [ ] `frontend/src/api/<ServiceName>.js` - Service class with mock data
- [ ] `frontend/src/pages/<Module>/<Feature>/index.js` - List page
- [ ] `frontend/src/pages/<Module>/<Feature>/Detail.js` - Detail page
- [ ] `frontend/src/pages/<Module>/<Feature>/CreateEdit.js` - Create/Edit page
- [ ] `frontend/src/pages/<Module>/<Feature>/Form.js` - Form component (if separate)
- [ ] `frontend/src/pages/<Module>/<Feature>/<ComplexComponent>.js` - Workflow designer, etc.
- [ ] `frontend/src/router.js` - Add routes (modify existing)
- [ ] `frontend/src/locales/zh_CN.js` - Chinese labels (modify existing)
- [ ] `frontend/src/locales/en_US.js` - English labels (modify existing)

### Documentation

- [ ] `openspec/changes/<change-id>/PREVIEW_SUMMARY.md` - Preview completion report
- [ ] `openspec/changes/<change-id>/screenshots/` - All screenshots organized by feature
- [ ] API contract documentation (in PREVIEW_SUMMARY.md)
- [ ] Notes on preview limitations (in PREVIEW_SUMMARY.md)

## Success Criteria

Preview implementation is complete when:

**Environment:**
- ✅ Node.js 14.x confirmed active and documented
- ✅ Dev server runs without compilation errors
- ✅ No console errors except expected warnings

**Mock Data:**
- ✅ 5-10+ realistic sample records implemented
- ✅ Different scenarios covered (enabled/disabled, simple/complex)
- ✅ PREVIEW_MODE flag for easy backend switch
- ✅ All CRUD operations functional

**UI Quality:**
- ✅ **Full production UI implemented** (not simplified!)
- ✅ All interactive components working (drag-and-drop, modals, etc.)
- ✅ No blank screens or rendering errors
- ✅ All pages accessible (List, Detail, Create/Edit)
- ✅ Navigation works between pages

**Internationalization:**
- ✅ Chinese labels complete and correct (primary language)
- ✅ English labels complete
- ✅ All UI text localized (no hardcoded strings)

**Testing:**
- ✅ Playwright test checklist completed
- ✅ All user flows tested
- ✅ Minimum 4 screenshots captured
- ✅ Interactive features verified (clicks, toggles, navigation)

**Documentation:**
- ✅ PREVIEW_SUMMARY.md created in `openspec/changes/<change-id>/`
- ✅ Screenshots saved in `openspec/changes/<change-id>/screenshots/`
- ✅ API contract documented for backend developers
- ✅ Preview limitations clearly stated
- ✅ Node.js 14.x requirement documented
- ✅ Screenshots included and labeled (minimum 4)

**User Experience:**
- ✅ Mock data displays correctly (no empty tables)
- ✅ No 404 errors (mock data prevents these)
- ✅ Realistic demo experience for stakeholders
- ✅ All CRUD operations feel natural

## Best Practices

### Code Organization

1. **Verify Node.js 14.x FIRST** - Before any coding (`nvm use 14`)
2. **Study existing frontend pages** - Use similar pages as templates
3. **Implement FULL production UI** - Don't simplify complex components
4. **Add comprehensive mock data** - Minimum 5-10 realistic records
5. **Use Needle build system** - Custom HVisions tooling
6. **Follow React class component patterns** - Consistency with codebase (React 16.9.0)
7. **Document expected API contracts** - For future backend implementation

### Development Workflow

1. **Switch to Node.js 14.x** - ALWAYS first step: `nvm use 14`
2. **Study reference pages** - Understand existing UI patterns before coding
3. **Implement service layer with mock data** - Enable realistic testing
4. **Implement full UI components** - List, Detail, Create/Edit, complex components
5. **Use Chinese as primary language** - Unless explicitly instructed otherwise
6. **Update router.js as soon as possible** - Plan pages to write and update router.js
7. **Test with Playwright immediately** - Catch errors early
8. **Capture screenshots** - Document working UI for stakeholders

### Error Prevention

1. **Always use Node.js 14.x** - NOT latest version (prevents compatibility issues)
2. **Use Ant Design 3.26.20 syntax** - NOT version 4.x or 5.x
3. **Extend local BaseService** - Not @hvisions/toolkit Service
4. **Use relative paths in service methods** - Not full URLs
5. **Add mock data immediately** - Don't wait for backend
6. **Don't simplify UI** - Stakeholders need to see real interface
7. **Test rendering with Playwright** - Avoid blank screens in production
8. **Verify Chinese labels first** - Primary language requirement

### Testing Strategy

1. **Verify Node.js 14.x before starting** - Save hours of debugging
2. **Test UI immediately after creation** - Don't wait for backend
3. **Use Playwright for automated testing** - Consistent validation
4. **Follow specific test checklist** - Don't skip scenarios
5. **Verify all UI elements render** - No blank screens or console errors
6. **Test all interactions** - Clicks, toggles, navigation, modals
7. **Capture required screenshots** - Minimum 4 screenshots

## Important Reminders

⚠️ **This is PREVIEW only - NO BACKEND implementation**

When running preview:
1. **Use Node.js 14.x** - Run `nvm use 14` BEFORE starting
2. **Add comprehensive mock data** - 5-10+ realistic records
3. **Implement FULL production UI** - Don't simplify complex components
4. **Use Chinese as default language** - Unless instructed otherwise
5. **Use Ant Design 3.26.20 syntax** - NOT version 4.x or 5.x
6. **Test with Playwright immediately** - Follow specific test checklist
7. **Capture minimum 4 screenshots** - Document working UI
8. **Backend will be implemented later** - Use `/openspec:apply` command

## Additional Resources

- **Reference Pages**: `frontend/src/pages/` - Study similar pages for patterns
- **CLAUDE.md**: Project overview and common commands
- **Frontend Framework**: React 16.9.0, Ant Design 3.26.20, HVisions Needle
- **Node Version**: 14.x (use `nvm use 14`)
- **Ant Design 3.x Docs**: https://3x.ant.design/ (NOT 4.x or 5.x)
- **Preview Standards**: `openspec/PREVIEW_COMMAND_STANDARDS.md` - Detailed template and best practices

---

**Remember**:
- **Node.js 14.x is MANDATORY** - Check first, always
- **Mock data is REQUIRED** - Enables realistic stakeholder demos
- **Full UI is REQUIRED** - Don't simplify for preview
- **Save to standard locations** - `openspec/changes/<change-id>/PREVIEW_SUMMARY.md` and `screenshots/`
- The preview approach allows stakeholders to see and interact with the REAL UI immediately, providing rapid feedback on UX/UI design before any backend work begins
