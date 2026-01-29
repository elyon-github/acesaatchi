# BIR 2307 Checkbox Selection Feature - Complete Implementation

## Overview
The BIR Form 2307 now has a fully functional checkbox selection feature that allows users to:
- Select specific invoices from the table to include in the form
- See a real-time preview update when selections change
- View a loading animation while the preview is being generated
- Print only selected records or all records (if none selected)

## Changes Made

### 1. **Frontend - JavaScript Enhancements** (`bir_forms.js`)

#### Added Components:
- **Checkbox State Management**: Tracks selected invoice IDs in `state.checkedIds` Set
- **Event Delegation**: Listens for checkbox changes without re-attaching listeners
- **Loading Animation**: Shows spinner when preview is loading, hides when complete

#### Key Methods:
```javascript
// Handles individual checkbox changes
handleIndividualCheckboxChange(e)

// Handles "select all" checkbox
handleSelectAllChange(e)

// Updates preview with selected filters
updatePreviewOnly()

// Shows loading spinner
showPreviewLoading()

// Hides loading spinner when preview loads
hidePreviewLoading()

// Attaches load listener to iframe
attachPreviewLoadListener()
```

#### Documentation:
- Added comprehensive JSDoc comments explaining the checkbox feature
- Added inline comments throughout the component
- Documented the filtering behavior (all records when empty, selected when checked)

### 2. **Table Rendering** (`bir_utils.js`)

#### Fixed:
- **Correct Data Index**: Changed moveId extraction from index [8] to [0]
- The `process_2307_ammend()` returns array: `[moveId, name, type, untaxed, total, billDate, dueDate, paymentStatus]`

#### Added:
- Comment explaining the data structure and checkbox rendering
- Documentation of how move IDs are extracted and used

### 3. **Backend Query Logic** (`models.py`)

#### Enhanced:
- **`_parse_checked_ids()`**: Safely parses JSON checked_ids from frontend
- **`_2307_query_normal()`**: Executes SQL query with optional checkbox filtering
- **`_2307_params()`**: Builds WHERE clause with SQL IN filter when records are selected

#### Documentation:
- Added docstrings explaining parameter filtering behavior
- Comments explaining that empty checked_ids means "show all records"
- Comments explaining that selected checked_ids means "show only these records"

### 4. **Report Template** (`bir_form_2307.xml`)

#### Changes:
- Removed debug output lines
- Added comments explaining parameter parsing and checkbox filtering flow
- Clean, production-ready template

### 5. **UI Template** (`bir_forms_templates.xml`)

#### Updated:
- Wrapped preview in container with `position: relative` to contain loading spinner
- Added class `preview-container-2307` for JavaScript targeting

### 6. **Loading Animation Styles** (`style.css`)

#### Added CSS:
```css
.preview-loader-2307 - Loading overlay container
.loader-spinner - Spinner wrapper with text
.spinner - Animated rotating circle
@keyframes spin - 360° rotation animation
```

#### Features:
- Semi-transparent white background overlay
- Centered spinner with text "Generating preview..."
- Smooth rotation animation (0.8s per rotation)
- Green spinner matching BIR theme colors
- Automatically hidden when iframe finishes loading

## How It Works

### User Workflow:
1. User selects/deselects checkboxes in the table
2. Loading spinner appears over preview
3. Backend query is executed with filtered results
4. Preview loads and spinner disappears
5. User sees only checked records in preview/print

### Data Flow:

```
Frontend (Checkboxes)
    ↓
checkedIds Set (JavaScript state)
    ↓
URL parameters (URLSearchParams)
    ↓
Backend request.params
    ↓
_parse_checked_ids() → List of integers
    ↓
_2307_params() → SQL IN clause
    ↓
Database query with filtering
    ↓
Filtered results
    ↓
Report template rendering
    ↓
PDF preview with only selected records
```

## Behavior

### When No Checkboxes Selected:
- `checked_ids = []` (empty array)
- SQL query has NO additional filter
- **ALL records** matching date/search criteria are rendered
- User can preview and print complete form

### When Checkboxes Selected:
- `checked_ids = [1, 2, 3]` (selected move IDs)
- SQL adds: `AND T0.id IN (1, 2, 3)`
- **ONLY selected records** are rendered
- User can preview and print form with subset of invoices

## Code Quality Improvements

### Comments Added:
- JSDoc comments for all major methods
- Inline comments explaining complex logic
- Documentation of data structures
- Explanation of filtering behavior
- CSS animation documentation

### Removed:
- All `console.log()` debug statements
- All `_logger.info()` debug logging
- Debug HTML output in report
- Obsolete commented code

## Testing Checklist

✅ Form loads correctly  
✅ All invoices display in table initially  
✅ Checkboxes properly render with move IDs  
✅ Single checkbox selection updates preview  
✅ Multiple checkbox selections work together  
✅ "Select All" checkbox selects/deselects all  
✅ Unchecking resets to show all records  
✅ Loading spinner appears during preview fetch  
✅ Loading spinner disappears when preview loads  
✅ Preview updates in real-time without page refresh  
✅ Search + checkbox selection work together  
✅ Month/partner changes clear checkbox selections  
✅ Print button shows only selected records  
✅ No selected records = all records printed  

## File Changes Summary

| File | Changes |
|------|---------|
| `bir_forms.js` | Added checkbox handlers, loading animation, comprehensive comments |
| `bir_utils.js` | Fixed data index for moveId, added comments |
| `models.py` | Enhanced filtering logic, improved docstrings |
| `bir_form_2307.xml` | Removed debug output, added comments |
| `bir_forms_templates.xml` | Wrapped preview in position:relative container |
| `style.css` | Added loading animation styles with keyframe animations |

## Browser Compatibility

- ✅ All modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ Uses standard CSS and JavaScript features
- ✅ No external dependencies required
- ✅ Responsive design maintained

