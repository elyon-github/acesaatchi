# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from dateutil.relativedelta import relativedelta
from odoo.tools import SQL
_logger = logging.getLogger(__name__)
import re

class SaleOrder(models.Model):
    _inherit="sale.order"




    x_ce_status = fields.Selection([
        ('for_client_signature', 'For Client Signature'),
        ('signed', 'Signed'),
        ('billable', 'Billable'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')

    ], default='for_client_signature', required=True, string='C.E. Status', tracking=True)

    x_job_number = fields.Char(string="Job Number")

    @api.model
    def collect_potential_accruals(self, accrual_date, reversal_date):
        """
        Collect sale orders eligible for accrual creation.
        Returns two recordsets:
        - potential: All SOs that meet criteria (state=sale, status=signed/billable)
        - duplicates: SOs that already have accruals in this period
        """
        reversal_date = accrual_date + relativedelta(months=1) - relativedelta(days=1)
        potential = self.env['sale.order']
        duplicates = self.env['sale.order']

        # Find all eligible sale orders
        eligible_sos = self.search([
            ('state', '=', 'sale'),
            ('x_ce_status', 'in', ['signed', 'billable'])
        ])
        
        # Check each SO for existing accruals in this period
        for so in eligible_sos:
            # Add to potential list (all eligible SOs)
            potential |= so
            
            # Check if it already has accruals in this period
            existing = self.env['saatchi.accrued_revenue'].search([
                ('related_ce_id', '=', so.id),
                ('date', '>=', accrual_date),
                ('date', '<=', reversal_date),
                ('state', 'in', ['draft', 'accrued'])
            ], limit=1)
            
            if existing:
                duplicates |= so

        return potential, duplicates

    # Deprecated
    # @api.model
    # def create_accruals_for_sos(self, sos_list, is_override=False):
    #     """
    #     Create accruals for a list of sale orders.
    #     Returns the count of successfully created accruals.
    #     """
    #     created_count = 0
    #     for so in sos_list:
    #         try:
    #             result = so.action_create_custom_accrued_revenue(is_override=is_override)
    #             if result:
    #                 created_count += 1
    #         except Exception as e:
    #             _logger.error(f"Failed to create accrual for SO {so.name}: {e}")
    #             continue
        
    #     return created_count

    def action_create_custom_accrued_revenue(self, is_override=False, accrual_date=False, reversal_date=False):
            """Create a new accrued revenue entry for this sale order"""
            self.ensure_one()
    
            # Validate sale order state (skip validation if override is True)
            if not is_override:
                if self.state != 'sale' or self.x_ce_status not in ['signed', 'billable']:
                    _logger.warning(f"SO {self.name} does not meet accrual criteria")
                    return False
    
            # Use default dates if not provided
            if not accrual_date:
                accrual_date = self.env['saatchi.accrued_revenue.wizard']._default_accrual_date()
            if not reversal_date:
                reversal_date = self.env['saatchi.accrued_revenue.wizard']._default_reversal_date()
    
    
            
            # Create the accrued revenue record
            accrued_revenue = self.env['saatchi.accrued_revenue'].create({
                'related_ce_id': self.id,
                'currency_id': self.currency_id.id,
                'date': accrual_date,
                'reversal_date': reversal_date
            })
            
            # Create lines for each sale order line, but only for Agency Charges
            total_eligible_for_accrue = 0
            lines_created = 0
            
            for line in self.order_line:
                # Skip display type lines (section headers, notes, etc.)
                if line.display_type:
                    continue
                
                # Only process lines from Agency Charges category
                if not self._is_agency_charges_category(line.product_template_id):
                    continue
                
                # Calculate accrued quantity (delivered but not invoiced)
                accrued_qty = line.product_uom_qty - line.qty_invoiced
                
                # Skip if nothing to accrue
                if accrued_qty <= 0:
                    continue
                
                # Calculate accrued amount
                accrued_amount = accrued_qty * line.price_unit
                
                # Get analytic distribution from sale order line
                analytic_distribution = line.analytic_distribution or {}
                
                # If no analytic distribution on line, try to get from sale order
                if not analytic_distribution and hasattr(self, 'analytic_distribution') and self.analytic_distribution:
                    analytic_distribution = self.analytic_distribution
                
                # Get income account
                income_account = line.product_id.property_account_income_id or \
                               line.product_id.categ_id.property_account_income_categ_id
                
                if not income_account:
                    _logger.warning(f"No income account found for line {line.name} in SO {self.name}")
                    continue
                
                # Create accrual line
                self.env['saatchi.accrued_revenue_lines'].create({
                    'accrued_revenue_id': accrued_revenue.id,
                    'ce_line_id': line.id,
                    'account_id': income_account.id,
                    'label': f'{self.name} - {line.name}',
                    'credit': accrued_amount,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': analytic_distribution,
                })
                
                total_eligible_for_accrue += accrued_amount
                lines_created += 1
            
            # If no lines were created, delete the accrued revenue and return False
            if lines_created == 0:
                accrued_revenue.unlink()
                _logger.warning(f"No eligible lines found for accrual in SO {self.name}")
                return False
            
            # Create the total line (debit side)
            self.env['saatchi.accrued_revenue_lines'].create({
                'accrued_revenue_id': accrued_revenue.id,
                'label': 'Total Accrued',
                'currency_id': self.currency_id.id,
            })
            
            # Update the original total amount
            accrued_revenue.write({'ce_original_total_amount': total_eligible_for_accrue})
            
            _logger.info(f"Created accrual for SO {self.name} with {lines_created} lines, total: {total_eligible_for_accrue}")
            
            # If override is True, return the accrued revenue ID
            if is_override:
                return accrued_revenue.id
            
            return True

    def _is_agency_charges_category(self, product):
        """Check if product belongs to Agency Charges category or its children"""
        if not product or not product.categ_id:
            return False
        
        # Check current category and all parents
        current_categ = product.categ_id
        while current_categ:
            if current_categ.name.lower() == 'agency charges':
                return True
            current_categ = current_categ.parent_id
        
        return False



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    x_ce_code = fields.Char(string="CE Code")
    x_ce_date = fields.Date(string="CE Date")
    x_remarks = fields.Char(string="Remarks")
    

class AccountMove(models.Model):
    _inherit = "account.move"
    
    related_custom_accrued_record = fields.Many2one(
        'saatchi.accrued_revenue', 
        store=True, 
        readonly=True
    )
    x_remarks = fields.Char(string="Remarks")

    x_accrual_system_generated = fields.Boolean(string="Accrual Revenue / Reversal Generated by system?")


    # sub_currency_id = fields.Many2one(
    #     'res.currency',
    #     string="Foreign Currency",
    #     default=lambda self: self.env.ref('base.USD')
    # )
    
    # custom_exchange_rate = fields.Float(
    #     string="Foreign Currency Exchange Rate",
    #     digits=(12, 2),
    #     help="1 unit of document currency = X sub currency units",
    #     compute="_compute_custom_exchange_rate",
    #     # store=True
    # )
    
    # # @api.depends('currency_id', 'sub_currency_id', 'date')
    # def _compute_custom_exchange_rate(self):
    #     for record in self:
    #         # If no sub_currency_id is set, default to 1.0
    #         if not record.sub_currency_id:
    #             record.custom_exchange_rate = 1.0
    #             continue
                
    #         # If document currency is the same as sub currency, rate is 1.0
    #         if record.currency_id == record.sub_currency_id:
    #             record.custom_exchange_rate = 1.0
    #             continue
                
    #         # Compute exchange rate from document currency to sub_currency_id
    #         try:
    #             date = record.date or fields.Date.today()
    #             company = record.company_id or self.env.company
                
    #             # Convert 1 unit of document currency to sub_currency_id
    #             rate = record.currency_id._convert(
    #                 record.amount_total,
    #                 record.sub_currency_id,
    #                 company,
    #                 date
    #             )
    #             record.custom_exchange_rate = rate
                
    #         except Exception as e:
    #             # Fallback: try manual rate lookup using the rates from currency table
    #             try:
    #                 # In Odoo, base currency (usually USD) has rate = 1.0
    #                 # In Odoo, base currency (usually USD) has rate = 1.0
    #                 # Other currencies have rates relative to base currency
                    
    #                 # Get the rate for document currency (JPY in your case)
    #                 doc_currency_rate = self.env['res.currency.rate'].search([
    #                     ('currency_id', '=', record.currency_id.id),
    #                     ('name', '<=', search_date),
    #                     ('company_id', 'in', [company.id, False])
    #                 ], order='name desc', limit=1)
                    
    #                 # Get the rate for sub currency (PHP in your case)  
    #                 sub_currency_rate = self.env['res.currency.rate'].search([
    #                     ('currency_id', '=', record.sub_currency_id.id),
    #                     ('name', '<=', search_date),
    #                     ('company_id', 'in', [company.id, False])
    #                 ], order='name desc', limit=1)
                    
    #                 if doc_currency_rate and sub_currency_rate:
    #                     # If both currencies have rates, calculate cross rate
    #                     # rate = (1 / doc_rate) * sub_rate
    #                     record.custom_exchange_rate = sub_currency_rate.rate / doc_currency_rate.rate
    #                 elif not doc_currency_rate and sub_currency_rate:
    #                     # Document currency is base currency (rate = 1.0)
    #                     record.custom_exchange_rate = sub_currency_rate.rate
    #                 elif doc_currency_rate and not sub_currency_rate:
    #                     # Sub currency is base currency (rate = 1.0)
    #                     record.custom_exchange_rate = 1.0 / doc_currency_rate.rate
    #                 else:
    #                     record.custom_exchange_rate = 1.0
                        
    #             except Exception:
    #                 record.custom_exchange_rate = 1.0




class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        """ Override to add currency_name field """
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
        
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(group_options, domain=additional_domain, date_scope='strict_range')
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
            account_type = self.env['account.account']._field_to_sql(account_alias, 'account_type')

            query = SQL(
                '''
                SELECT
                    account_move_line.id,
                    account_move_line.date,
                    MIN(account_move_line.date_maturity)    AS date_maturity,
                    MIN(account_move_line.name)             AS name,
                    MIN(account_move_line.ref)              AS ref,
                    MIN(account_move_line.company_id)       AS company_id,
                    MIN(account_move_line.account_id)       AS account_id,
                    MIN(account_move_line.payment_id)       AS payment_id,
                    MIN(account_move_line.partner_id)       AS partner_id,
                    MIN(account_move_line.currency_id)      AS currency_id,
                    MIN(currency.name)                      AS currency_name,
                    SUM(account_move_line.amount_currency)  AS amount_currency,
                    MIN(COALESCE(account_move_line.invoice_date, account_move_line.date)) AS invoice_date,
                    account_move_line.date                  AS date,
                    SUM(%(debit_select)s)                   AS debit,
                    SUM(%(credit_select)s)                  AS credit,
                    SUM(%(balance_select)s)                 AS balance,
                    MIN(move.name)                          AS move_name,
                    MIN(company.currency_id)                AS company_currency_id,
                    MIN(partner.name)                       AS partner_name,
                    MIN(move.move_type)                     AS move_type,
                    MIN(%(account_code)s)                   AS account_code,
                    MIN(%(account_name)s)                   AS account_name,
                    MIN(%(account_type)s)                   AS account_type,
                    MIN(journal.code)                       AS journal_code,
                    MIN(%(journal_name)s)                   AS journal_name,
                    MIN(full_rec.id)                        AS full_rec_name,
                    %(column_group_key)s                    AS column_group_key
                FROM %(table_references)s
                JOIN account_move move                      ON move.id = account_move_line.move_id
                %(currency_table_join)s
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN res_currency currency             ON currency.id = account_move_line.currency_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE %(search_condition)s
                GROUP BY account_move_line.id, account_move_line.date
                ORDER BY account_move_line.date, move_name, account_move_line.id
                ''',
                account_code=account_code,
                account_name=account_name,
                account_type=account_type,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                search_condition=query.where_clause,
            )
            queries.append(query)

        full_query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

        if offset:
            full_query = SQL('%s OFFSET %s ', full_query, offset)
        if limit:
            full_query = SQL('%s LIMIT %s ', full_query, limit)

        return full_query