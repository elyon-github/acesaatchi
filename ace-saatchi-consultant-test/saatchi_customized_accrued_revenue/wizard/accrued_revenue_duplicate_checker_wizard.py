# -*- coding: utf-8 -*-
"""
Accrued Revenue Wizard
======================
Wizard for creating accrued revenue entries with scenario support.

Features:
- Default mode: Auto-generate accruals for signed/billable SOs
- Special case mode: Three scenarios for flexible accrual creation
  * Scenario 1: Manual Accrue (override validation)
  * Scenario 2: Cancel & Replace existing accruals
  * Scenario 3: Create adjustment entries (NO auto-reversal)

Scenarios Explained:
- Scenario 1: Creates accruals bypassing CE status validation
- Scenario 2: Cancels existing accruals and replaces with new ones
- Scenario 3: Creates adjustment entries to reduce previous accruals
              (Dr. Digital Income | Cr. Accrued Revenue) - NO auto-reversal
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SaatchiAccruedRevenueWizard(models.TransientModel):
    """
    Accrued Revenue Wizard
    
    Main wizard model for batch accrual creation with scenario support.
    """
    _name = 'saatchi.accrued_revenue.wizard'
    _description = 'Accrued Revenue Creation Wizard'
    
    accrual_date = fields.Date(
        string="Accrual Date",
        required=True,
        default=lambda self: self._default_accrual_date(),
        help="Last day of the period for accrual (e.g., Oct 31, 2025)"
    )
    
    reversal_date = fields.Date(
        string="Reversal Date",
        required=True,
        default=lambda self: self._default_reversal_date(),
        help="First day of next period for reversal (e.g., Nov 1, 2025) - only used for normal accruals"
    )
    
    so_line_ids = fields.One2many(
        'saatchi.accrued_revenue.wizard.line',
        'wizard_id',
        string="Sale Orders"
    )
    
    has_existing_accruals = fields.Boolean(
        compute="_compute_has_existing_accruals",
        string="Has Duplicates",
        help="True if any sale order has existing accruals in this period"
    )
    
    special_case_mode = fields.Boolean(
        string="Special Case Mode",
        default=False,
        help="Enable scenario selection for advanced accrual handling"
    )
    
    accrual_scenario = fields.Selection(
        [
            ('scenario_1', 'Scenario 1: Manual Accrue (Override Validation)'),
            ('scenario_2', 'Scenario 2: Cancel & Replace Existing (Accrued State Only)'),
            ('scenario_3', 'Scenario 3: Create Adjustment Entry (NO Auto-Reversal)')
        ],
        string="Accrual Scenario",
        default='scenario_1',
        help="""
        Scenario 1: Creates accruals bypassing CE status validation (allows any status)
        Scenario 2: Cancels existing accruals in 'Accrued' state and replaces them with new ones (Draft/Cancelled accruals are ignored)
        Scenario 3: Creates adjustment entries (Dr. Digital Income | Cr. Accrued Revenue) - PERMANENT entry with NO auto-reversal
        """
    )

    # ========== Compute Methods ==========
    
    @api.depends('so_line_ids.existing_accrual_ids')
    def _compute_has_existing_accruals(self):
        """Check if any wizard line has existing accruals"""
        for wizard in self:
            wizard.has_existing_accruals = any(
                line.existing_accrual_ids for line in wizard.so_line_ids
            )

    # ========== Default Methods ==========
    
    def _default_accrual_date(self):
        """Default to last day of previous month"""
        today = fields.Date.context_today(self)
        first_of_current_month = today.replace(day=1)
        return first_of_current_month - relativedelta(days=1)
    
    def _default_reversal_date(self):
        """Default to first day of current month"""
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    # ========== Action Methods ==========
    
    def action_create_accruals(self):
        """
        Create accruals for selected sale orders based on chosen scenario
        
        Process:
        1. Validate scenario compatibility
        2. Filter selected lines
        3. Execute scenario-specific logic
        4. Track success/failures
        5. Show notification
        
        Returns:
            dict: Client action to show notification
        """
        self.ensure_one()
        
        selected_lines = self.so_line_ids.filtered(lambda l: l.create_accrual)
        
        if not selected_lines:
            raise UserError(_('Please select at least one sale order to create accruals.'))
        
        # Validate scenario compatibility BEFORE processing
        if self.special_case_mode:
            validation_errors = self._validate_scenario_compatibility(selected_lines)
            if validation_errors:
                raise UserError('\n\n'.join(validation_errors))
        
        # Execute scenario with proper error handling
        try:
            if not self.special_case_mode:
                return self._execute_default_scenario(selected_lines)
            elif self.accrual_scenario == 'scenario_1':
                return self._execute_scenario_1(selected_lines)
            elif self.accrual_scenario == 'scenario_2':
                return self._execute_scenario_2(selected_lines)
            elif self.accrual_scenario == 'scenario_3':
                return self._execute_scenario_3(selected_lines)
        except Exception as e:
            _logger.exception("Fatal error in action_create_accruals")
            raise UserError(_(
                'An unexpected error occurred during accrual creation:\n%s\n\n'
                'Please check the logs for more details.'
            ) % str(e))
    
    def _validate_scenario_compatibility(self, selected_lines):
        """
        Validate that selected SOs are compatible with chosen scenario
        
        Args:
            selected_lines: Selected wizard lines
            
        Returns:
            list: Error messages (empty if valid)
        """
        errors = []
        if self.accrual_scenario == 'scenario_1':
            # Filter lines where ANY existing accrual is draft or accrued
            with_existing = selected_lines.filtered(
                lambda l: any(a.state in ['accrued', 'draft', 'reversed'] for a in l.existing_accrual_ids)
            )
        
            if with_existing:
                so_names = ', '.join(with_existing.mapped('sale_order_id.name'))
                errors.append(_(
                    '❌ Scenario 1 Not Allowed:\n'
                    'The following Sale Orders already have existing accrual entries:\n'
                    '%s\n\n'
                    'Scenario 1 is only for creating NEW accruals. It cannot be used when an SO already '
                    'has any accruals (draft or accrued).\n\n'
                ) % so_names)
                        
            
        if self.accrual_scenario == 'scenario_2':
            # Scenario 2: Only SOs with existing accruals in 'accrued' state
            sos_without_accrued = []
            for line in selected_lines:
                accrued_records = line.existing_accrual_ids.filtered(lambda a: a.state == 'reversed' or a.state == 'accrued')
                if not accrued_records:
                    sos_without_accrued.append(line.sale_order_id.name)
            
            if sos_without_accrued:
                so_names = ', '.join(sos_without_accrued)
                errors.append(_(
                    '❌ Scenario 2 Error:\n'
                    'The following Sale Orders have NO existing accruals in "Accrued" state (only accrued entries can be replaced):\n'
                    '%s\n\n'
                    '💡 Solution: Uncheck these SOs or ensure they have posted accrual entries.\n'
                    'Note: Draft or cancelled accruals cannot be replaced - edit them directly or delete them.'
                ) % so_names)
        
        elif self.accrual_scenario == 'scenario_3':
            # Scenario 3: Only SOs with existing accruals (must have at least one "accrued" entry)
            sos_without_existing = []
            sos_without_accrued = []
        
            for line in selected_lines:
                # 1. No existing accruals at all
                if not line.existing_accrual_ids:
                    sos_without_existing.append(line.sale_order_id.name)
                    continue
        
                # 2. Has accruals but none are in "accrued" state
                accrued_records = line.existing_accrual_ids.filtered(lambda a: a.state == 'reversed' or a.state == 'accrued')
                if not accrued_records:
                    sos_without_accrued.append(line.sale_order_id.name)
        
            # --- Error 1: SOs with NO accruals at all ---
            if sos_without_existing:
                so_names = ', '.join(sos_without_existing)
                errors.append(_(
                    '❌ Scenario 3 Error:\n'
                    'The following Sale Orders have NO existing accruals and cannot have adjustments created:\n'
                    '%s\n\n'
                    '💡 Solution: Uncheck these SOs or use Scenario 1/2 instead.'
                ) % so_names)
        
            # --- Error 2: SOs with accruals but none in "accrued" state ---
            if sos_without_accrued:
                so_names_2 = ', '.join(sos_without_accrued)
                errors.append(_(
                    '❌ Scenario 3 Error:\n'
                    'The following Sale Orders do not have any accruals in "Accrued" state:\n'
                    '%s\n\n'
                    '💡 Only posted (accrued) entries can be adjusted. Draft or cancelled entries must be edited or deleted.'
                ) % so_names_2)

                    
        return errors
    
    def _execute_default_scenario(self, selected_lines):
        """
        Default scenario: Create accruals for signed/billable SOs only
        
        Args:
            selected_lines: Wizard lines to process
            
        Returns:
            dict: Notification action
        """
        created_count = 0
        skipped_invalid_status = []
        skipped_no_lines = []
        failed_sos = []
        
        for line in selected_lines:
            so = line.sale_order_id
            
            # Check CE status
            if so.state != 'sale' or so.x_ce_status not in ['signed', 'billable']:
                skipped_invalid_status.append(f"{so.name} (Status: {dict(so._fields['x_ce_status'].selection).get(so.x_ce_status, 'Unknown')})")
                continue
            
            try:
                result = so.action_create_custom_accrued_revenue(
                    is_override=False,
                    accrual_date=self.accrual_date,
                    reversal_date=self.reversal_date,
                    is_adjustment=False
                )
                
                if result:
                    created_count += 1
                    _logger.info(f"✓ Default: Created accrual {result} for SO {so.name}")
                else:
                    skipped_no_lines.append(so.name)
                    _logger.warning(f"⚠ Default: No eligible lines for SO {so.name}")
                    
            except Exception as e:
                error_msg = str(e)
                _logger.error(f"❌ Default: Failed for SO {so.name}: {error_msg}", exc_info=True)
                failed_sos.append(f"{so.name} ({error_msg[:100]})")
                continue
        
        # Build detailed message
        message_parts = []
        
        if created_count > 0:
            message_parts.append(f'✅ Successfully created {created_count} accrual(s)')
        
        if skipped_invalid_status:
            message_parts.append(
                f'\n\n⚠️ Skipped {len(skipped_invalid_status)} SO(s) - Invalid Status:\n'
                f'{chr(10).join("  • " + s for s in skipped_invalid_status)}\n'
                f'💡 Use Scenario 1 (Manual Accrue) to override status validation'
            )
        
        if skipped_no_lines:
            message_parts.append(
                f'\n\n⚠️ Skipped {len(skipped_no_lines)} SO(s) - No Eligible Lines:\n'
                f'{chr(10).join("  • " + s for s in skipped_no_lines)}\n'
                f'💡 Check: Agency Charges products, not fully invoiced'
            )
        
        if failed_sos:
            message_parts.append(
                f'\n\n❌ Failed {len(failed_sos)} SO(s):\n'
                f'{chr(10).join("  • " + s for s in failed_sos)}'
            )
        
        message = '\n'.join(message_parts) if message_parts else 'No accruals created.'
        
        if created_count > 0:
            message += '\n\n🔄 Please refresh the page to view the new records.'
        
        msg_type = 'success' if created_count > 0 and not failed_sos else 'warning' if created_count > 0 else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Accrual Creation Complete'),
                'message': message,
                'type': msg_type,
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _execute_scenario_1(self, selected_lines):
        """
        Scenario 1: Manual Accrue (Override Validation)
        
        Creates accruals bypassing CE status validation.
        Allows accruals for any SO regardless of status.
        
        Args:
            selected_lines: Wizard lines to process
            
        Returns:
            dict: Notification action
        """
        created_count = 0
        failed_sos = []
        
        for line in selected_lines:
            try:
                result = line.sale_order_id.action_create_custom_accrued_revenue(
                    is_override=True,  # Override validation
                    accrual_date=self.accrual_date,
                    reversal_date=self.reversal_date,
                    is_adjustment=False,
                    is_system_generated=False,
                )
                
                if result:
                    created_count += 1
                    _logger.info(f"✓ Scenario 1: Created accrual {result} for SO {line.sale_order_id.name}")
                else:
                    error_msg = "No eligible lines found"
                    _logger.warning(f"⚠ Scenario 1: {error_msg} for SO {line.sale_order_id.name}")
                    failed_sos.append(f"{line.sale_order_id.name} ({error_msg})")
                    
            except Exception as e:
                error_msg = str(e)
                _logger.error(f"❌ Scenario 1: Failed for SO {line.sale_order_id.name}: {error_msg}", exc_info=True)
                failed_sos.append(f"{line.sale_order_id.name} ({error_msg[:100]})")
                continue
        
        message = _(
            'Scenario 1 Complete (Manual Accrue):\n'
            '✓ %d accrual(s) created with override\n'
            'Please refresh the page to view the records.'
        ) % created_count
        
        if failed_sos:
            message += _('\n\n⚠ Failed to create accruals for:\n%s') % '\n'.join(f"  • {s}" for s in failed_sos)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Scenario 1 Complete'),
                'message': message,
                'type': 'success' if not failed_sos else 'warning',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _execute_scenario_2(self, selected_lines):
        """
        Scenario 2: Cancel & Replace Existing
        
        Cancels existing accruals (ONLY in 'accrued' state) and creates new ones.
        Draft or cancelled accruals are skipped.
        
        Args:
            selected_lines: Wizard lines to process
            
        Returns:
            dict: Notification action
        """
        created_count = 0
        replaced_count = 0
        skipped_not_accrued = []
        failed_sos = []
        
        for line in selected_lines:
            try:
                # Filter to only 'accrued' state records
                accrued_records = line.existing_accrual_ids.filtered(lambda a: a.state == 'accrued' or a.state == 'reversed')
                
                if not accrued_records:
                    # Skip if no accrued records found
                    skipped_not_accrued.append(f"{line.sale_order_id.name} (No posted accruals found)")
                    _logger.warning(f"⚠ Scenario 2: Skipped SO {line.sale_order_id.name} - no accrued state records to replace")
                    continue
                
                # Cancel only the 'accrued' state records
                for existing_accrual in accrued_records:
                    existing_accrual.action_reset_and_cancel()
                
                replaced_count += len(accrued_records)
                _logger.info(f"✓ Scenario 2: Cancelled {len(accrued_records)} accrued record(s) for SO {line.sale_order_id.name}")
                
                # Create new accrual
                result = line.sale_order_id.action_create_custom_accrued_revenue(
                    is_override=False,
                    accrual_date=self.accrual_date,
                    reversal_date=self.reversal_date,
                    is_adjustment=False,
                    is_system_generated=False
                )
                
                if result:
                    created_count += 1
                    _logger.info(f"✓ Scenario 2: Created replacement accrual {result} for SO {line.sale_order_id.name}")
                else:
                    error_msg = "No eligible lines found"
                    _logger.warning(f"⚠ Scenario 2: {error_msg} for SO {line.sale_order_id.name}")
                    failed_sos.append(f"{line.sale_order_id.name} ({error_msg})")
                    
            except Exception as e:
                error_msg = str(e)
                _logger.error(f"❌ Scenario 2: Failed for SO {line.sale_order_id.name}: {error_msg}", exc_info=True)
                failed_sos.append(f"{line.sale_order_id.name} ({error_msg[:100]})")
                continue
        
        message = _(
            'Scenario 2 Complete (Cancel & Replace):\n'
            '✓ %d accrued record(s) cancelled\n'
            '✓ %d new accrual(s) created\n'
            'Please refresh the page to view the records.'
        ) % (replaced_count, created_count)
        
        if skipped_not_accrued:
            message += _('\n\nℹ Skipped %d SO(s) - No posted accruals to replace:\n%s\n💡 Draft accruals can be edited directly; cancelled accruals should be deleted.') % (
                len(skipped_not_accrued),
                '\n'.join(f"  • {s}" for s in skipped_not_accrued)
            )
        
        if failed_sos:
            message += _('\n\n⚠ Failed to process:\n%s') % '\n'.join(f"  • {s}" for s in failed_sos)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Scenario 2 Complete'),
                'message': message,
                'type': 'success' if created_count > 0 and not failed_sos else 'warning' if created_count > 0 else 'info',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _execute_scenario_3(self, selected_lines):
        """
        Scenario 3: Create Adjustment Entry (NO Auto-Reversal)
        
        Creates adjustment entries to reduce previous accruals.
        Entry structure: Dr. Digital Income | Cr. Accrued Revenue
        
        This is a PERMANENT adjustment - NO automatic reversal is created.
        User can edit the amount in draft before posting.
        
        Only processes SOs with existing accruals.
        
        Args:
            selected_lines: Wizard lines to process
            
        Returns:
            dict: Notification action
        """
        created_count = 0
        skipped_count = 0
        failed_sos = []
        
        for line in selected_lines:
            try:
                # Only create adjustment if existing accruals exist
                if not line.existing_accrual_ids:
                    skipped_count += 1
                    _logger.warning(f"⚠ Scenario 3: Skipped SO {line.sale_order_id.name} - no existing accruals")
                    continue
                
                # Create adjustment entry (NO auto-reversal)
                result = line.sale_order_id.action_create_custom_accrued_revenue(
                    is_override=False,
                    accrual_date=self.accrual_date,
                    reversal_date=False,
                    is_adjustment=True,  # Create adjustment entry (NO reversal),
                    is_system_generated=False
                )
                
                if result:
                    created_count += 1
                    _logger.info(f"✓ Scenario 3: Created adjustment entry {result} for SO {line.sale_order_id.name}")
                else:
                    error_msg = "No accrual amount calculated"
                    _logger.warning(f"⚠ Scenario 3: {error_msg} for SO {line.sale_order_id.name}")
                    failed_sos.append(f"{line.sale_order_id.name} ({error_msg})")
                    
            except Exception as e:
                error_msg = str(e)
                _logger.error(f"❌ Scenario 3: Failed for SO {line.sale_order_id.name}: {error_msg}", exc_info=True)
                failed_sos.append(f"{line.sale_order_id.name} ({error_msg[:100]})")
                continue
        
        message = _(
            'Scenario 3 Complete (Adjustment Entry):\n'
            '✓ %d adjustment entr(y/ies) created in draft\n'
            '⚠️ IMPORTANT: These are PERMANENT adjustments with NO auto-reversal\n'
            '💡 Edit the "Digital Income" line amount before posting\n'
            '💡 Default amount shown is a suggestion based on current SO variance\n'
            'Please refresh the page to view the records.'
        ) % created_count
        
        if skipped_count > 0:
            message += _('\n\nℹ %d SO(s) skipped (no existing accruals)') % skipped_count
        
        if failed_sos:
            message += _('\n\n⚠ Failed to create adjustments for:\n%s') % '\n'.join(f"  • {s}" for s in failed_sos)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Scenario 3 Complete'),
                'message': message,
                'type': 'success' if not failed_sos else 'warning',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class SaatchiAccruedRevenueWizardLine(models.TransientModel):
    """
    Accrued Revenue Wizard Line
    
    Individual line for each sale order in the wizard.
    """
    _name = 'saatchi.accrued_revenue.wizard.line'
    _description = 'Accrued Revenue Wizard Line'
    _order = 'has_existing_accrual desc, sale_order_id'
    
    wizard_id = fields.Many2one(
        'saatchi.accrued_revenue.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade',
        index=True
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        required=True,
        readonly=True,
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        related='sale_order_id.partner_id',
        readonly=True
    )
    
    ce_code = fields.Char(
        string="CE Code",
        related='sale_order_id.x_ce_code',
        readonly=True,
    )
    
    ce_status = fields.Selection(
        string="CE Status",
        related='sale_order_id.x_ce_status',
        readonly=True,
    )
    
    amount_total = fields.Monetary(
        string="Accrual Amount",
        readonly=True,
        help="Total amount to be accrued for this sale order"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='sale_order_id.currency_id',
        readonly=True
    )
    
    has_existing_accrual = fields.Boolean(
        string="Has Existing Accrual",
        default=False,
        readonly=True,
        help="This sale order already has an accrual for this period"
    )
    
    existing_accrual_ids = fields.Many2many(
        'saatchi.accrued_revenue',
        string="Existing Accruals",
        compute="_compute_existing_accruals",
        store=True,
        help="Existing accrual records for this sale order in the current period"
    )
    
    existing_accrual_total = fields.Monetary(
        string="Existing Accrual Total",
        compute="_compute_existing_accrual_total",
        currency_field="currency_id",
        help="Total amount from existing accruals"
    )
    
    create_accrual = fields.Boolean(
        string="Create",
        default=False,
        help="Check to create accrual for this sale order"
    )

    # ========== Compute Methods ==========
    
    @api.depends('sale_order_id', 'wizard_id.accrual_date', 'wizard_id.reversal_date')
    def _compute_existing_accruals(self):
        """Find existing accruals for this sale order in the current period"""
        for line in self:
            if line.sale_order_id and line.wizard_id.accrual_date and line.wizard_id.reversal_date:
                existing = self.env['saatchi.accrued_revenue'].search([
                    ('x_related_ce_id', '=', line.sale_order_id.id),
                    ('date', '>=', line.wizard_id.accrual_date),
                    ('date', '<=', line.wizard_id.reversal_date),
                    ('state', 'in', ['draft', 'accrued', 'reversed'])
                ])
                line.existing_accrual_ids = [(6, 0, existing.ids)]
            else:
                line.existing_accrual_ids = [(5, 0, 0)]
    
    @api.depends('existing_accrual_ids', 'existing_accrual_ids.total_debit_in_accrue_account')
    def _compute_existing_accrual_total(self):
        """Calculate total from existing accruals"""
        for line in self:
            line.existing_accrual_total = sum(
                line.existing_accrual_ids.mapped('total_debit_in_accrue_account')
            )