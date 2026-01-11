from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class SalesOrderRevenueWizard(models.TransientModel):
    _name = 'sales.order.revenue_report.wizard'
    _description = 'Sales Order Revenue Report Wizard'
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Customers',
        help='Select specific customers. Leave empty to include all customers.'
    )
    
    report_date = fields.Date(
        string='Report Month',
        required=True,
        default=lambda self: fields.Date.context_today(self) - relativedelta(months=1),
        help='Select any date in the month you want to report on'
    )
    
    def action_print_report(self):
        """Generate the Sales Order Revenue XLSX report"""
        self.ensure_one()
        
        # Get the accrued revenue account ID
        accrued_account_ids = self._get_accrued_revenue_account_id()
        if not accrued_account_ids:
            raise UserError(
                "Accrued Revenue account not configured. "
                "Please set it in system parameters (account.accrued_revenue_account_id)."
            )
        
        # Calculate month range
        month_start = self.report_date.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
        
        # Build domain for account.move.line search (accrued entries)
        domain = [
            ('account_id', 'in', accrued_account_ids),
            ('parent_state', '=', 'posted'),
            ('x_sales_order', '!=', False),  # Must have sales order link
        ]

        
        # Add partner filter if specific customers selected
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        # Fetch all relevant accrued revenue move lines
        accrued_lines = self.env['account.move.line'].search(domain)
        
        # Get Sales Orders that were billed in the report month
        invoice_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
        ]
        
        if self.partner_ids:
            invoice_domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        invoices = self.env['account.move'].search(invoice_domain)
        
        # Get ALL sales orders from these invoices (whether they have accrued entries or not)
        all_billed_sales_orders = invoices.mapped('invoice_line_ids.sale_line_ids.order_id')
        # raise UserError(accrued_account_ids)
        if not accrued_lines and not all_billed_sales_orders:
            if self.partner_ids:
                customer_names = ', '.join(self.partner_ids.mapped('name'))
                raise UserError(
                    f"No accrued revenue entries or billed sales orders found for selected customer(s): {customer_names}"
                )
            else:
                raise UserError("No accrued revenue entries or billed sales orders found.")
        
        # Prepare data to pass to report
        report_data = {
            'report_date': self.report_date.isoformat(),
            'partner_ids': self.partner_ids.ids if self.partner_ids else [],
            'move_line_ids': accrued_lines.ids,  # Pass move line IDs for accrued entries
            'all_billed_so_ids': all_billed_sales_orders.ids,  # Pass ALL billed SO IDs
        }
        
        # Return the report action
        return self.env.ref('saatchi_soa.action_report_sales_order_revenue_xlsx').report_action(
            self.env['account.move.line'],
            data=report_data
        )
    
    def _get_accrued_revenue_account_id(self):
        """Get accrued revenue account IDs with fallback for multiple companies"""
        # Use user's allowed companies as target companies
        target_companies = self.env.companies
        
        try:
            account_id = int(self.env['ir.config_parameter'].sudo().get_param(
                'account.accrued_revenue_account_id',
                default='0'
            ) or 0)
            
            if account_id:
                template_account = self.env['account.account'].sudo().browse(account_id)
                if template_account.exists() and not template_account.deprecated:
                    # Check if account is accessible by user's allowed companies
                    if any(company in template_account.company_ids for company in target_companies):
                        # Account is accessible and valid for at least one target company
                        return template_account.ids
                    
                    # Find the equivalent accounts in target companies
                    equivalent_accounts = self.env['account.account'].sudo().search([
                        ('name', '=', template_account.name),
                        ('company_ids', 'in', target_companies.ids),
                        ('deprecated', '=', False)
                    ])
                    
                    if not equivalent_accounts:
                        # Fallback: try by name
                        equivalent_accounts = self.env['account.account'].sudo().search([
                            ('name', '=', template_account.name),
                            ('company_ids', 'in', target_companies.ids),
                            ('deprecated', '=', False)
                        ])
                    if equivalent_accounts:
                        return equivalent_accounts.ids
            
            # Fallback: Find miscellaneous income accounts
            misc_accounts = self.env['account.account'].sudo().search([
                ('account_type', '=', 'income_other'),
                ('deprecated', '=', False),
                ('company_ids', 'in', target_companies.ids)
            ])
            
            return misc_accounts.ids if misc_accounts else []
            
        except (ValueError, TypeError):
            return []