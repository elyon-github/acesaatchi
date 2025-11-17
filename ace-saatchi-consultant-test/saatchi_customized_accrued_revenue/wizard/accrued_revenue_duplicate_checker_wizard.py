from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class SaatchiAccruedRevenueWizard(models.TransientModel):
    _name = 'saatchi.accrued_revenue.wizard'
    _description = 'Wizard to Confirm Accrual Creation for Duplicates'
    
    accrual_date = fields.Date(
        string="Accrual Date", 
        required=True,
        default=lambda self: self._default_accrual_date(),
    )
    
    reversal_date = fields.Date(
        string="Reversal Date",
        required=True,
        default=lambda self: self._default_reversal_date(),
        store=True
    )
    
    so_line_ids = fields.One2many(
        'saatchi.accrued_revenue.wizard.line',
        'wizard_id',
        string="Sale Orders with Existing Accruals"
    )
    

    has_existing_accruals = fields.Boolean(compute="_compute_has_existing_accruals")


    def _compute_has_existing_accruals(self):
        self['has_existing_accruals'] = False
        for line in self.so_line_ids:
            if line.existing_accrual_ids:
                self['has_existing_accruals'] = True
                return
        
    def _default_accrual_date(self):
        """
        Default to last day of previous month
        Example: If today is Nov 11, 2025, default to Oct 31, 2025
        """
        today = fields.Date.context_today(self)
        first_of_current_month = today.replace(day=1)
        last_day_of_prev_month = first_of_current_month - relativedelta(days=1)
        return last_day_of_prev_month
        

    def _default_reversal_date(self):
        """
        Default to first day of current month
        Example: If today is Nov 11, 2025, default to Nov 1, 2025
        
        This is one day after the default accrual date (Oct 31 + 1 = Nov 1).
        Reversals always happen the day after accrual.
        """
        today = fields.Date.context_today(self)
        first_of_current_month = today.replace(day=1)
        return first_of_current_month


    
    def action_create_accruals(self):
        """Create accruals for selected sale orders (these are overrides since they have existing accruals)"""
        self.ensure_one()
        
        selected_lines = self.so_line_ids.filtered(lambda l: l.create_accrual)
        
        if not selected_lines:
            raise UserError(_('Please select at least one sale order to create accruals.'))
        
        created_count = 0
        failed_sos = []
        
        for line in selected_lines:
            try:
                # Always override since this wizard only shows SOs with existing accruals
                result = line.sale_order_id.action_create_custom_accrued_revenue(is_override=False, accrual_date=self.accrual_date, reversal_date=self.reversal_date)
                if result:
                    created_count += 1
            except Exception as e:
                failed_sos.append(line.sale_order_id.name)
                continue
        
        # Prepare the message
        message = _('%d accrual(s) created successfully out of %d selected. Please refresh the Page to view the records.') % (created_count, len(selected_lines))
        if failed_sos:
            message += _('\n\nFailed to create accruals for: %s') % ', '.join(failed_sos)
        
        # Close the wizard and show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Accrual Creation Complete'),
                'message': message,
                'type': 'success' if not failed_sos else 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class SaatchiAccruedRevenueWizardLine(models.TransientModel):
    _name = 'saatchi.accrued_revenue.wizard.line'
    _description = 'Wizard Line for Sale Order Selection'
    _order = 'sale_order_id'
    
    wizard_id = fields.Many2one(
        'saatchi.accrued_revenue.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade'
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        required=True,
        readonly=True
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
    
    amount_total = fields.Monetary(
        string="For Accrue Amount",
        readonly=True,
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='sale_order_id.currency_id',
        readonly=True
    )
    
    has_existing_accrual = fields.Boolean(
        string="Has Existing Accrual",
        default=True,
        readonly=True,
        help="This sale order already has an accrual for this period"
    )
    
    existing_accrual_ids = fields.Many2many(
        'saatchi.accrued_revenue',
        string="Existing Accruals",
        compute="_compute_existing_accruals",
        store=True
    )
    
    create_accrual = fields.Boolean(
        string="Create",
        default=False,
        help="Check to create another accrual for this sale order (this will be a duplicate)"
    )
    

            
            
    @api.depends('sale_order_id', 'wizard_id.accrual_date', 'wizard_id.reversal_date')
    def _compute_existing_accruals(self):
        for line in self:
            if line.sale_order_id and line.wizard_id.accrual_date and line.wizard_id.reversal_date:
                existing = self.env['saatchi.accrued_revenue'].search([
                    ('related_ce_id', '=', line.sale_order_id.id),
                    ('date', '>=', line.wizard_id.accrual_date),
                    ('date', '<=', line.wizard_id.reversal_date),
                    ('state', 'in', ['draft', 'accrued'])
                ])
                line.existing_accrual_ids = [(6, 0, existing.ids)]
            else:
                line.existing_accrual_ids = [(5, 0, 0)]



            