# BIR 2307 Checkbox Selection Feature - Implementation Summary

## Problem
Checkboxes were not passing selected record IDs from the frontend to the PDF report, resulting in all records being rendered instead of just the checked ones.

## Root Cause Analysis
The issue was in the data flow sequence:
1. **loadData()** was updating the preview BEFORE attaching checkbox event listeners
2. Checkboxes were being rendered but events weren't properly attached
3. The preview update order caused the iframe to load before checkboxes could capture state

## Solutions Implemented

### 1. Fixed Data Flow in Frontend (`bir_forms.js`)
**File**: `addons/custom_addons/Client-Trial/bir_module/static/src/js/bir_forms.js`

**Change 1**: Moved `updatePreviewOnly()` call to the end of `loadData()`
- Now the preview updates AFTER the table is loaded and checkbox listeners are attached
- Ensures checkboxes can properly track state

**Change 2**: Improved `updatePreviewOnly()` URL construction
- Replaced string concatenation with `URLSearchParams` for safer parameter encoding
- Ensures special characters and JSON data are properly encoded
- Parameters passed: `id`, `month`, `trigger`, `search`, `checked_ids`

### 2. Enhanced Backend Filtering (`models.py`)
**File**: `addons/custom_addons/Client-Trial/bir_module/models/models.py`

**Change**: Updated `_2307_params()` method
- Added logging to track when checked_ids filtering is applied
- Properly converts checked_ids from frontend to SQL IN clause
- Only filters when valid checked_ids exist

### 3. Cleaned Up Report Template (`bir_form_2307.xml`)
**File**: `addons/custom_addons/Client-Trial/bir_module/reports/bir_form_2307.xml`

**Change**: Removed debug output line
- Removed: `<div style="color: red; font-size: 10pt;">DEBUG checked_ids: <t t-esc="checked_ids"/></div>`
- Now displays cleaner report output

## How It Works Now

### Frontend Flow
1. User selects/deselects checkboxes in the table
2. `handleIndividualCheckboxChange()` updates `this.state.checkedIds` Set
3. `updatePreviewOnly()` builds URL with checked IDs
4. Preview iframe loads with the correct parameters

### Backend Flow
1. Report receives `checked_ids` parameter from request
2. `_parse_checked_ids()` converts JSON string to list of integers
3. `x_get_2307_data()` receives the checked_ids list
4. `_2307_query_normal()` uses `_2307_params()` to add SQL filter
5. Only selected records are rendered in the preview/print

### URL Structure
```
/report/pdf/bir_module.form_2307/?id=123&month=2026-01&trigger=view&search=&checked_ids=[1,2,3]
```

## Behavior

### When No Checkboxes are Selected
- `checked_ids` = `[]`
- SQL query has NO additional filter
- ALL records matching search criteria are rendered

### When Checkboxes are Selected
- `checked_ids` = `[id1, id2, id3]`
- SQL query adds: `AND T0.id IN (id1, id2, id3)`
- ONLY selected records are rendered

## Testing Checklist
- [ ] Form loads and displays all records in table
- [ ] Checkboxes are properly rendered with IDs
- [ ] Single checkbox selection updates preview
- [ ] Multiple checkbox selections work correctly
- [ ] "Select All" checkbox works
- [ ] Unchecking resets to show all records
- [ ] Print button shows only selected records
- [ ] Preview updates in real-time without page refresh
- [ ] Search + checkbox selection work together
- [ ] Checkbox state persists when changing search/month

## Technical Details

### Checkbox Elements (rendered by `construct_ammendment_no_action()`)
```html
<input type='checkbox' class='form-check-input bir-checkbox-2307' data-move-id='[MOVE_ID]'/>
```

### Event Delegation
- Uses change event listener on table container
- Targets checkboxes with class `bir-checkbox-2307`
- Maintains Set of checked move IDs in component state

### URL Parameter Encoding
- Uses `URLSearchParams` API for automatic encoding
- Handles special characters and JSON data correctly
- Compatible with Odoo's request.params parsing
