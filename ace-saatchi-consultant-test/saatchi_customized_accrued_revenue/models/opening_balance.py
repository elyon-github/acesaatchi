# -*- coding: utf-8 -*-
"""
Opening Balance Model for Accrued Revenue
==========================================

Provides a way to store historical opening balances for CE# entries that
existed before the accrual system was put in place. When generating the
accrued revenue XLSX report, if no prior DB history exists for a CE#,
the system falls back to this model to populate the previous month's
ending balance column.

Matching Logic:
- CE# is normalized (uppercased, all whitespace removed) for comparison
- The opening balance date must match the accrual config's cutoff date

Typical Usage:
1. Bulk import opening balances via CSV/Excel
2. Configure the cutoff month-end date in Accrual Configuration
3. When generating a report for months at or before that cutoff,
   the opening balance is used as the previous month balance
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
import logging

_logger = logging.getLogger(__name__)


class SaatchiAccruedRevenueOpeningBalance(models.Model):
    """
    Stores opening balances per CE# for bootstrapping the accrued revenue
    report when no prior transactional history exists in the database.

    Key Fields:
    - ce_code: The CE# identifier (normalized for matching)
    - ce_code_normalized: Auto-computed stripped version for fast lookup
    - balance_date: The month-end date this balance represents
    - balance_amount: The ending balance amount for that month
    - company_id: Multi-company support
    """
    _name = 'saatchi.accrued_revenue_opening_balance'
    _description = 'Accrued Revenue Opening Balance'
    _rec_name = 'ce_code'
    _order = 'balance_date desc, ce_code asc'

    # ========== CE Identification ==========
    ce_code = fields.Char(
        string='CE#',
        required=True,
        index=True,
        help='The CE code identifier. Will be normalized (uppercased, '
             'whitespace removed) for matching with report data.'
    )

    ce_code_normalized = fields.Char(
        string='CE# (Normalized)',
        compute='_compute_ce_code_normalized',
        store=True,
        index=True,
        help='Auto-computed normalized CE code for fast matching. '
             'All whitespace removed and uppercased.'
    )

    # ========== Balance Data ==========
    balance_date = fields.Date(
        string='Balance Date (Month-End)',
        required=True,
        index=True,
        help='The month-end date this opening balance represents. '
             'Example: 2025-12-31 for the December 2025 ending balance.'
    )

    balance_amount = fields.Float(
        string='Balance Amount',
        digits=(16, 2),
        required=True,
        default=0.0,
        help='The ending balance amount for this CE# as of the balance date. '
             'Positive = debit balance (asset/accrued revenue).'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='Currency of the balance amount.'
    )

    # ========== CE Descriptive Fields (for reference) ==========
    partner_name = fields.Char(
        string='Client Name',
        help='Client/partner name associated with this CE#. '
             'Used for display and cross-referencing.'
    )

    ce_date = fields.Date(
        string='CE Date',
        help='Original date of the Cost Estimate.'
    )

    ce_status = fields.Char(
        string='CE Status',
        help='Status text of the Cost Estimate at the time of opening balance. '
             'Store as plain text (e.g., "Closed", "Billable", etc.)'
    )

    job_description = fields.Char(
        string='Job Description',
        help='Description of the job/project for this CE#.'
    )

    # ========== Company ==========
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help='Company this opening balance belongs to.'
    )

    # ========== Audit Fields ==========
    notes = fields.Text(
        string='Notes',
        help='Any additional notes or remarks about this opening balance entry.'
    )

    # ========== Computed Fields ==========

    @api.depends('ce_code')
    def _compute_ce_code_normalized(self):
        """
        Compute normalized CE code by removing all whitespace and uppercasing.

        Examples:
            'CE 001'   -> 'CE001'
            'ce-001 '  -> 'CE-001'
            ' Ce 0 01' -> 'CE001'
        """
        for record in self:
            if record.ce_code:
                record.ce_code_normalized = re.sub(
                    r'\s+', '', record.ce_code.strip().upper()
                )
            else:
                record.ce_code_normalized = False

    # ========== Constraints ==========

    @api.constrains('ce_code', 'balance_date', 'company_id')
    def _check_unique_ce_balance(self):
        """Ensure no duplicate CE# + date + company combinations"""
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('ce_code_normalized', '=', record.ce_code_normalized),
                ('balance_date', '=', record.balance_date),
                ('company_id', '=', record.company_id.id),
            ], limit=1)
            if duplicate:
                raise UserError(_(
                    'An opening balance already exists for CE# "%(ce)s" '
                    'on %(date)s for company %(company)s.',
                    ce=record.ce_code,
                    date=record.balance_date,
                    company=record.company_id.name,
                ))

    @api.constrains('balance_date')
    def _check_balance_date_is_month_end(self):
        """Warn (but allow) if the balance date is not a month-end date"""
        for record in self:
            if record.balance_date:
                from dateutil.relativedelta import relativedelta
                next_day = record.balance_date + relativedelta(days=1)
                if next_day.day != 1:
                    _logger.warning(
                        'Opening balance for CE# %s has date %s which is not '
                        'a month-end date. This may cause matching issues.',
                        record.ce_code, record.balance_date
                    )

    # ========== Helper Methods ==========

    @api.model
    def get_opening_balances_for_month(self, balance_date, company_id=None):
        """
        Retrieve all opening balances for a specific month-end date.

        Args:
            balance_date: The month-end date to look up (e.g., 2025-12-31)
            company_id: Optional company ID to filter by

        Returns:
            dict: {normalized_ce_code: balance_amount}
        """
        domain = [('balance_date', '=', balance_date)]
        if company_id:
            domain.append(('company_id', '=', company_id))

        records = self.sudo().search(domain)
        return {
            rec.ce_code_normalized: rec.balance_amount
            for rec in records
        }

    @api.model
    def get_opening_balance_records_for_month(self, balance_date, company_id=None):
        """
        Retrieve full opening balance records for a specific month-end date.
        Includes all descriptive fields for populating report rows.

        Args:
            balance_date: The month-end date to look up
            company_id: Optional company ID to filter by

        Returns:
            dict: {normalized_ce_code: {
                'balance': float,
                'partner_name': str,
                'ce_date': date,
                'ce_status': str,
                'job_description': str,
                'ce_code_display': str (original CE code)
            }}
        """
        domain = [('balance_date', '=', balance_date)]
        if company_id:
            domain.append(('company_id', '=', company_id))

        records = self.sudo().search(domain)
        result = {}
        for rec in records:
            result[rec.ce_code_normalized] = {
                'balance': rec.balance_amount,
                'partner_name': rec.partner_name or '',
                'ce_date': rec.ce_date,
                'ce_status': rec.ce_status or '',  # Now a plain text Char field
                'job_description': rec.job_description or '',
                'ce_code_display': rec.ce_code or '',
            }
        return result
