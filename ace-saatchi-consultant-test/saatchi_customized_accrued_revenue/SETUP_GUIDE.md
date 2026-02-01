# Multi-Company Setup Quick Reference

## Setting Up Accrual Configuration for Multiple Companies

### Step 1: Access Configuration Menu
1. Go to **Accounting** → **Configuration** → **Accrual Configuration**
2. Click **Create** button

### Step 2: Configure Company A
- **Company**: Select "Company A"
- **Accrual Journal**: Select the general journal for Company A
- **Accrued Revenue Account**: Select account 1210 (or equivalent) for Company A
- **Digital Income Account**: Select account 5787 (or equivalent) for Company A
- Click **Save**

### Step 3: Configure Company B
- Click **Create** button again
- **Company**: Select "Company B"
- **Accrual Journal**: Select the general journal for Company B
- **Accrued Revenue Account**: Select account 1210 (or equivalent) for Company B
- **Digital Income Account**: Select account 5787 (or equivalent) for Company B
- Click **Save**

## How It Works

### When Creating an Accrued Revenue Entry
1. System automatically detects the company context
2. Looks up the company in `saatchi.accrual_config`
3. Uses that company's configured accounts and journal
4. Creates journal entries with proper company-specific accounts

### Example
```
Company A Context:
└─ System finds: Account 1210-A, Journal JA

Company B Context:
└─ System finds: Account 1210-B, Journal JB
```

## Validation Rules

The system automatically validates:
- ✓ Journal belongs to selected company
- ✓ Accrued revenue account available for selected company
- ✓ Digital income account available for selected company

If validation fails, you'll see clear error message explaining what's wrong.

## Access Permissions

| Group | Read | Write | Create | Delete |
|-------|------|-------|--------|--------|
| Account Managers | ✓ | ✓ | ✓ | ✗ |
| Regular Users | ✓ | ✗ | ✗ | ✗ |

## Troubleshooting

### Missing Configuration Warning
**Symptom**: Log shows "No accrual configuration found for company ABC"

**Solution**: 
1. Go to Accounting > Configuration > Accrual Configuration
2. Create configuration for the company
3. Select appropriate accounts and journal
4. Save and retry

### Wrong Account Being Used
**Symptom**: Accrual entries use wrong accounts

**Solution**:
1. Check company context when creating entries
2. Verify configuration exists for that company
3. Edit configuration if accounts need to change

### Constraint Validation Failed
**Symptom**: "The accrual journal must belong to the selected company"

**Solution**:
1. Select journal that belongs to the chosen company
2. Accounts and journals must be company-specific
3. Check company master data to ensure accounts exist there

## Related Documentation

- See [MULTI_COMPANY_IMPLEMENTATION.md](MULTI_COMPANY_IMPLEMENTATION.md) for technical details
- Module docstring in models.py explains architecture

## Key Methods Using Configuration

These methods automatically use the configured accounts/journals:

1. **_get_accrued_revenue_account_id()** → Returns configured account 1210
2. **_get_accrued_journal_id()** → Returns configured journal
3. **_get_adjustment_accrued_revenue_account_id()** → Returns configured account 5787

All fallback gracefully with warning logs if configuration missing.
