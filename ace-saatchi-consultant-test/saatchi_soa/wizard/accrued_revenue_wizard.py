from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import datetime


class AccruedRevenueWizard(models.TransientModel):
    _name = 'accrued.revenue_report.wizard'
    _description = 'Accrued Revenue Report Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help='Starting month for the accrued revenue report'
    )

    end_date = fields.Date(
        string='End Date',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help='Ending month for the accrued revenue report'
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate that end_date is not before start_date"""
        for wizard in self:
            if wizard.end_date < wizard.start_date:
                raise UserError("End Date cannot be earlier than Start Date.")

    def action_print_report(self):
        """Generate the Accrued Revenue XLSX report for the selected date range"""
        self.ensure_one()

        # Get the accrued revenue account ID
        accrued_account_id = self._get_accrued_revenue_account_id()
        if not accrued_account_id:
            raise UserError(
                "Accrued Revenue account not configured. "
                "Please set it in system parameters (account.accrued_revenue_account_id)."
            )

        # Calculate the first day of start month and last day of end month
        start_month = self.start_date.replace(day=1)
        end_month_last_day = (self.end_date.replace(
            day=1) + relativedelta(months=1)) - relativedelta(days=1)

        # We need to include the previous month's data for reversal entries
        # So we extend the search range to include the month BEFORE start_date
        search_start = start_month - relativedelta(months=1)

        # Fetch all account.move.line records for the accrued revenue account
        # within the extended date range
        domain = [
            ('account_id', '=', accrued_account_id),
            ('date', '>=', search_start),
            ('date', '<=', end_month_last_day),
            ('parent_state', '=', 'posted'),  # Only posted entries
        ]

        lines = self.env['account.move.line'].search(domain)

        if not lines:
            raise UserError(
                f"No accrued revenue entries found between {self.start_date.strftime('%B %Y')} "
                f"and {self.end_date.strftime('%B %Y')}."
            )

        # Return the report action with the wizard context
        return self.env.ref('saatchi_soa.action_report_accrued_revenue_xlsx').report_action(
            lines,
            data={
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
            }
        )

    def _get_accrued_revenue_account_id(self):
        """Get accrued revenue account ID with fallback"""
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
                        return account_id
                    
                    # Find the equivalent account in target companies
                    equivalent_account = self.env['account.account'].sudo().search([
                        ('code', '=', template_account.code),
                        ('company_ids', 'in', target_companies.ids),
                        ('deprecated', '=', False)
                    ], limit=1)
                    
                    if not equivalent_account:
                        # Fallback: try by name
                        equivalent_account = self.env['account.account'].sudo().search([
                            ('name', '=', template_account.name),
                            ('company_ids', 'in', target_companies.ids),
                            ('deprecated', '=', False)
                        ], limit=1)
                    
                    if equivalent_account:
                        return equivalent_account.id
            
            # Fallback: Find miscellaneous income account
            misc_account = self.env['account.account'].sudo().search([
                ('account_type', '=', 'income_other'),
                ('deprecated', '=', False),
                ('company_ids', 'in', target_companies.ids)
            ], limit=1)
            
            return misc_account.id if misc_account else 0
            
        except (ValueError, TypeError):
            return 0
