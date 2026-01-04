# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo import models, _

class InheritUsers(models.Model):
    _inherit = 'res.users'

    x_client_assignment_ids = fields.One2many(
        'base_customization.user_client_assignment',
        'user_id',
        string="Client Assignments"
    )

    # Computed fields for backward compatibility and easy filtering
    x_client_ids = fields.Many2many(
        'res.partner',
        compute='_compute_assigned_clients_products',
        string="Assigned Clients"
    )

    x_product_ids = fields.Many2many(
        'product.template',
        compute='_compute_assigned_clients_products',
        string="Assigned Products"
    )

    @api.depends('x_client_assignment_ids.x_partner_id', 'x_client_assignment_ids.x_product_ids')
    def _compute_assigned_clients_products(self):
        """Compute flattened lists for easier domain usage"""
        for user in self:
            user.x_client_ids = user.x_client_assignment_ids.mapped(
                'x_partner_id')
            user.x_product_ids = user.x_client_assignment_ids.mapped(
                'x_product_ids')


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_id = fields.Many2one(
        'res.partner',
        domain=lambda self: [('id', 'in', self.env.user.x_client_ids.ids)]
        if self.env.user.employee_id and
        self.env.user.employee_id.department_id and
        self.env.user.employee_id.department_id.name == 'ACCOUNTS'
        else [('id', '!=', False)]  # This returns no records
    )

    x_client_product_ce_code_domain = fields.Char(
        compute='_compute_x_client_product_ce_code_domain'
    )

    x_client_product_ce_code = fields.Many2one(
        'base_customization.client_product_ce_co_line',
        string="Client - Product CE Code",
        domain="x_client_product_ce_code_domain"
    )

    @api.depends('partner_id')
    def _compute_x_client_product_ce_code_domain(self):
        for record in self:
            
            if self.env.user.id != 2:
                domain = [
                    ('x_client_product_ce_co_id.x_partner_id', '=', record.partner_id.id),
                    ('x_product_id', 'in', self.env.user.x_product_ids.ids)
                ]
            else:
                domain = [
                   ('x_client_product_ce_co_id.x_partner_id', '=', record.partner_id.id),
                ]
            record.x_client_product_ce_code_domain = str(domain)

    x_job_description = fields.Char('Job Description')
    x_ce_code = fields.Char(compute="_compute_x_ce_code",
                            string="Client CE Code", store=True)

    x_alt_currency_amount = fields.Float(
        string="Alt Total Amount",
        digits=(12, 2),
        help="Alternative currency total computed from order lines",
        compute="_compute_alt_currency_amount",
        store=True,  # set to True if you need it stored
    )

    x_alt_currency_id = fields.Many2one(
        'res.currency',
        string="Alt Currency",
        default=lambda self: self._default_alt_currency_id(),
    )

    x_remarks = fields.Char(string="Remarks", tracking=True)

    def write(self, vals):
        res = super().write(vals)
        # Only trigger when the alternate currency changes or always on save
        if 'x_alt_currency_id' in vals:
            self._apply_alt_currency_conversion()
        return res

    def _apply_alt_currency_conversion(self):
        """Update all order lines with fx_currency and converted price."""
        for record in self:
            alt_currency = record.x_alt_currency_id
            if not alt_currency:
                continue

            for line in record.order_line:
                line.fx_currency_id = alt_currency
                line.fx_price_unit = line.currency_id._convert(
                    line.price_unit,
                    alt_currency,
                    record.company_id or record.env.company,
                    record.date_order
                )

    # ========== Financial Tracking Fields ==========
    x_ce_approved_estimate_billing = fields.Monetary(
        string="Approved Estimate | Billing",
        currency_field="currency_id",
        store=True,
        compute="_compute_x_ce_amounts",
        help="Total approved estimate for billing (all lines)"
    )

    x_ce_approved_estimate_revenue = fields.Monetary(
        string="Approved Estimate | Revenue",
        currency_field="currency_id",
        store=True,
        compute="_compute_x_ce_amounts",
        help="Total approved estimate for revenue (Agency Charges only)"
    )

    x_ce_invoiced_billing = fields.Monetary(
        string="Invoiced | Billing",
        currency_field="currency_id",
        store=True,
        compute="_compute_x_ce_amounts",
        help="Total invoiced amount for billing (all lines)"
    )

    x_ce_invoiced_revenue = fields.Monetary(
        string="Invoiced | Revenue",
        currency_field="currency_id",
        store=True,
        compute="_compute_x_ce_amounts",
        help="Total invoiced amount for revenue (Agency Charges only)"
    )

    x_ce_variance_billing = fields.Monetary(
        string="Variance | Billing",
        currency_field="currency_id",
        store=True,
        compute="_compute_x_ce_amounts",
        help="Difference between approved estimate and invoiced (billing)"
    )

    x_ce_variance_revenue = fields.Monetary(
        string="Variance | Revenue",
        currency_field="currency_id",
        store=True,
        compute="_compute_x_ce_amounts",
        help="Difference between approved estimate and invoiced (revenue) - eligible for accrual"
    )

    def _default_alt_currency_id(self):
        """Logic:
        1️⃣ If order currency != company currency → use company currency.
        2️⃣ Else if order lines exist with fx_currency_id → use first fx_currency_id.
        3️⃣ Else fallback to USD.
        """
        # self.ensure_one()

        company_currency = self.company_id.currency_id
        order_currency = self.currency_id

        # case 1
        if order_currency and company_currency and order_currency != company_currency:
            return company_currency.id

        # case 2
        fx_currency = self.order_line.filtered(lambda l: l.fx_currency_id)[
            :1].fx_currency_id
        if fx_currency:
            return fx_currency.id

        # case 3
        try:
            usd_currency = self.env.ref('base.USD')
            return usd_currency.id
        except ValueError:
            return company_currency.id or False

    @api.depends('order_line.fx_price_unit', 'x_alt_currency_id', 'date_order')
    def _compute_alt_currency_amount(self):
        """Compute the total alt amount by converting fx_price_unit to alt_currency."""
        for order in self:
            total = 0.0
            alt_currency = order.x_alt_currency_id or order.company_id.currency_id

            for line in order.order_line:
                fx_currency = line.fx_currency_id or order.currency_id
                fx_price = line.fx_price_unit or 0.0

                total += fx_currency._convert(
                    fx_price * line.product_uom_qty,
                    alt_currency,
                    order.company_id,
                    order.date_order or fields.Date.today()
                )
            order.x_alt_currency_amount = total

    @api.depends('x_client_product_ce_code')
    def _compute_x_ce_code(self):
        for record in self:
            if record.x_client_product_ce_code:
                ce_code = f'{record.x_client_product_ce_code.x_ce_product_code}{record.name}'
                record.x_ce_code = ce_code
            else:
                record.x_ce_code = ''

    @api.onchange('partner_id')
    def _onchange_partner_copy_ce_codes(self):
        """Copy CE codes from master when partner changes"""
        if self.partner_id:
            # Find master CE codes for this partner
            master_lines = self.env['base_customization.client_product_ce_co_line'].search([
                ('x_client_product_ce_co_id.x_partner_id', '=', self.partner_id.id)
            ])

            # Create copies for this sale order (command 5 clears, command 0 creates)
            line_vals = []
            for master_line in master_lines:
                line_vals.append((0, 0, {
                    'x_product_id': master_line.x_product_id.id,
                    'x_ce_product_code': master_line.x_ce_product_code,
                }))

            self.x_client_product_ce_code = [
                (5, 0, 0)] + line_vals  # Clear and add new
        else:
            self.x_client_product_ce_code = [(5, 0, 0)]  # Clear all

    # ========== Compute Methods ==========

    @api.depends(
        'order_line.price_subtotal',
        'order_line.qty_invoiced',
        'order_line.price_unit',
    )
    def _compute_x_ce_amounts(self):
        """
        Compute approved estimates, invoiced amounts, and variances

        Logic:
        - BILLING: All lines included
        - REVENUE: Only Agency Charges category lines included
        - VARIANCE: Approved Estimate - Invoiced
        """
        for record in self:
            approved_estimate_billing = 0
            approved_estimate_revenue = 0
            invoiced_billing = 0
            invoiced_revenue = 0

            for line in record.order_line:
                approved_estimate_billing += line.price_subtotal
                invoiced_billing += line.qty_invoiced * line.price_unit

                if record._is_agency_charges_category(line.product_template_id):
                    approved_estimate_revenue += line.price_subtotal
                    invoiced_revenue += line.qty_invoiced * line.price_unit

            record.x_ce_approved_estimate_billing = approved_estimate_billing
            record.x_ce_approved_estimate_revenue = approved_estimate_revenue
            record.x_ce_invoiced_billing = invoiced_billing
            record.x_ce_invoiced_revenue = invoiced_revenue
            record.x_ce_variance_billing = approved_estimate_billing - invoiced_billing
            record.x_ce_variance_revenue = approved_estimate_revenue - invoiced_revenue


class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    fx_currency_id = fields.Many2one(
        'res.currency',
        string="Alt Currency",
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False)
    )
    fx_price_unit = fields.Float(
        string="Alt Unit Price",
        help="Unit price in foreign exchange currency"
    )

    # Hidden field to track which field was last edited
    _last_edited_price_field = fields.Char(store=False)

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-compute fx_price_unit when creating order lines"""
        lines = super(InheritSaleOrderLine, self).create(vals_list)
        for line in lines:
            if line.price_unit and line.fx_currency_id and not line.fx_price_unit:
                company_currency = line.order_id.company_id.currency_id or self.env.company.currency_id
                if company_currency and company_currency != line.fx_currency_id:
                    line.fx_price_unit = company_currency._convert(
                        line.price_unit,
                        line.fx_currency_id,
                        line.order_id.company_id or self.env.company,
                        line.order_id.date_order or fields.Date.today()
                    )
                elif company_currency == line.fx_currency_id:
                    line.fx_price_unit = line.price_unit
        return lines

    @api.onchange('price_unit', 'fx_currency_id')
    def _onchange_price_unit_to_fx(self):
        """Convert price_unit (order line currency) to fx_price_unit"""
        # Mark that price_unit was edited
        self._last_edited_price_field = 'price_unit'

        if self.price_unit and self.fx_currency_id:
            # Use the sale order line's currency_id (typically pricelist currency)
            line_currency = self.currency_id
            if line_currency and line_currency != self.fx_currency_id:
                # Convert from line currency to FX currency
                self.fx_price_unit = line_currency._convert(
                    self.price_unit,
                    self.fx_currency_id,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today()
                )
            elif line_currency == self.fx_currency_id:
                self.fx_price_unit = self.price_unit

    @api.onchange('fx_price_unit')
    def _onchange_fx_price_unit_to_price(self):
        """Convert fx_price_unit to price_unit (order line currency)"""
        # Only convert if fx_price_unit was the last field edited by user
        # This prevents the chain reaction when price_unit triggers fx_price_unit change
        if self._last_edited_price_field == 'price_unit':
            # Reset the flag
            self._last_edited_price_field = None
            return

        # Mark that fx_price_unit was edited
        self._last_edited_price_field = 'fx_price_unit'

        if self.fx_price_unit and self.fx_currency_id:
            # Use the sale order line's currency_id (typically pricelist currency)
            line_currency = self.currency_id
            if line_currency and line_currency != self.fx_currency_id:
                # Convert from FX currency to line currency
                self.price_unit = self.fx_currency_id._convert(
                    self.fx_price_unit,
                    line_currency,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today()
                )
            elif line_currency == self.fx_currency_id:
                self.price_unit = self.fx_price_unit


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_alt_currency_amount = fields.Float(
        string="Alt Total Amount",
        digits=(12, 2),
        help="Alternative currency total computed from order lines",
        compute="_compute_alt_currency_amount",
        store=True,  # set to True if you need it stored
    )

    x_alt_currency_id = fields.Many2one(
        'res.currency',
        string="Alt Currency",
        default=lambda self: self._default_alt_currency_id(),
    )

    def write(self, vals):
        res = super().write(vals)
        # Only trigger when the alternate currency changes or always on save
        if 'x_alt_currency_id' in vals:
            self._apply_alt_currency_conversion()
        return res

    def _apply_alt_currency_conversion(self):
        """Update all order lines with fx_currency and converted price."""
        for record in self:
            alt_currency = record.x_alt_currency_id
            if not alt_currency:
                continue

            for line in record.order_line:
                line.fx_currency_id = alt_currency
                line.fx_price_unit = line.currency_id._convert(
                    line.price_unit,
                    alt_currency,
                    record.company_id or record.env.company,
                    record.date_order
                )

    def _default_alt_currency_id(self):
        """Logic:
        1️⃣ If order currency != company currency → use company currency.
        2️⃣ Else if order lines exist with fx_currency_id → use first fx_currency_id.
        3️⃣ Else fallback to USD.
        """
        # self.ensure_one()

        company_currency = self.company_id.currency_id
        order_currency = self.currency_id

        # case 1
        if order_currency and company_currency and order_currency != company_currency:
            return company_currency.id

        # case 2
        fx_currency = self.order_line.filtered(lambda l: l.fx_currency_id)[
            :1].fx_currency_id
        if fx_currency:
            return fx_currency.id

        # case 3
        try:
            usd_currency = self.env.ref('base.USD')
            return usd_currency.id
        except ValueError:
            return company_currency.id or False

    @api.depends('order_line.fx_price_unit', 'x_alt_currency_id', 'date_order')
    def _compute_alt_currency_amount(self):
        """Compute the total alt amount by converting fx_price_unit to alt_currency."""
        for order in self:
            total = 0.0
            alt_currency = order.x_alt_currency_id or order.company_id.currency_id

            for line in order.order_line:
                fx_currency = line.fx_currency_id or order.currency_id
                fx_price = line.fx_price_unit or 0.0

                total += fx_currency._convert(
                    fx_price * line.product_uom_qty,
                    alt_currency,
                    order.company_id,
                    order.date_order or fields.Date.today()
                )
            order.x_alt_currency_amount = total


class InheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    fx_currency_id = fields.Many2one(
        'res.currency',
        string="Alt Currency",
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False)
    )
    fx_price_unit = fields.Float(
        string="Alt Unit Price",
        help="Unit price in foreign exchange currency"
    )

    # Hidden field to track which field was last edited
    _last_edited_price_field = fields.Char(store=False)

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-compute fx_price_unit when creating order lines"""
        lines = super(InheritPurchaseOrderLine, self).create(vals_list)
        for line in lines:
            if line.price_unit and line.fx_currency_id and not line.fx_price_unit:
                # Use the purchase order line's currency_id
                line_currency = line.currency_id
                if line_currency and line_currency != line.fx_currency_id:
                    line.fx_price_unit = line_currency._convert(
                        line.price_unit,
                        line.fx_currency_id,
                        line.order_id.company_id or self.env.company,
                        line.order_id.date_order or fields.Date.today()
                    )
                elif line_currency == line.fx_currency_id:
                    line.fx_price_unit = line.price_unit
        return lines

    @api.onchange('price_unit', 'fx_currency_id')
    def _onchange_price_unit_to_fx(self):
        """Convert price_unit (order line currency) to fx_price_unit"""
        # Mark that price_unit was edited
        self._last_edited_price_field = 'price_unit'

        if self.price_unit and self.fx_currency_id:
            # Use the purchase order line's currency_id
            line_currency = self.currency_id
            if line_currency and line_currency != self.fx_currency_id:
                # Convert from line currency to FX currency
                self.fx_price_unit = line_currency._convert(
                    self.price_unit,
                    self.fx_currency_id,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today()
                )
            elif line_currency == self.fx_currency_id:
                self.fx_price_unit = self.price_unit

    @api.onchange('fx_price_unit')
    def _onchange_fx_price_unit_to_price(self):
        """Convert fx_price_unit to price_unit (order line currency)"""
        # Only convert if fx_price_unit was the last field edited by user
        # This prevents the chain reaction when price_unit triggers fx_price_unit change
        if self._last_edited_price_field == 'price_unit':
            # Reset the flag
            self._last_edited_price_field = None
            return

        # Mark that fx_price_unit was edited
        self._last_edited_price_field = 'fx_price_unit'

        if self.fx_price_unit and self.fx_currency_id:
            # Use the purchase order line's currency_id
            line_currency = self.currency_id
            if line_currency and line_currency != self.fx_currency_id:
                # Convert from FX currency to line currency
                self.price_unit = self.fx_currency_id._convert(
                    self.fx_price_unit,
                    line_currency,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today()
                )
            elif line_currency == self.fx_currency_id:
                self.price_unit = self.fx_price_unit


class AccountMove(models.Model):
    _inherit = 'account.move'

    currency_display = fields.Char(
        related='currency_id.name',
        string='Currency',
        store=True,
        readonly=True
    )

    x_related_so = fields.Many2one(
        'sale.order', compute="_compute_related_so", store=True)

    x_alt_currency_amount = fields.Float(
        string="Alt Total Amount",
        digits=(12, 2),
        help="Alternative currency total computed from order lines",
        compute="_compute_alt_currency_amount",
        store=True,  # set to True if you need it stored
    )

    x_alt_currency_id = fields.Many2one(
        'res.currency',
        store=True,
        compute="_compute_x_alt_currency_id",
        string="Alt Currency"
    )

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._apply_alt_currency_conversion()
        return record

    @api.depends('invoice_line_ids', 'state')
    def _compute_related_so(self):
        for record in self:
            record.x_related_so = False
            # for line in record.invoice_line_ids:
            #     if line.sale_line_ids:
            sale_order = record.invoice_line_ids.mapped('sale_line_ids.order_id')[
                :1] if record.invoice_line_ids else False
            record.x_related_so = sale_order

    def _apply_alt_currency_conversion(self):
        """Update all order lines with fx_currency and converted price."""
        for record in self:

            # if not alt_currency or not record.x_related_so:
            #     continue
            # raise UserError('eh')
            for line in record.invoice_line_ids:
                line.fx_currency_id = record.x_related_so.x_alt_currency_id.id or line.purchase_order_id.x_alt_currency_id.id
                line.fx_price_unit = line.currency_id._convert(
                    line.price_unit,
                    line.fx_currency_id,
                    record.company_id or record.env.company,
                    record.x_related_so.date_order or line.purchase_order_id.create_date
                )

    @api.depends('name')
    def _compute_x_alt_currency_id(self):
        for record in self:
            if record.invoice_line_ids:
                record.x_alt_currency_id = record.invoice_line_ids[0].fx_currency_id

    @api.depends('invoice_line_ids.fx_price_unit', 'invoice_line_ids.fx_currency_id', 'state')
    def _compute_alt_currency_amount(self):
        """Compute the total alt amount by converting fx_price_unit to alt_currency."""
        for record in self:
            total = 0.0
            alt_currency = record.x_alt_currency_id or record.company_id.currency_id

            if not record.x_alt_currency_id:
                record.x_alt_currency_amount = 0
                continue

            for line in record.invoice_line_ids:
                fx_currency = line.fx_currency_id or record.currency_id
                fx_price = line.fx_price_unit or 0.0

                total += fx_currency._convert(
                    fx_price * line.quantity,
                    alt_currency,
                    record.company_id,
                    record.x_related_so.date_order or fields.Date.today()
                )
            record.x_alt_currency_amount = total



# BIR Report Customizations
    def _search_account_by_code(self, code_suffix):
        """Search account by last 4 digits of code"""
        # Filter accounts by company using the move's company
        domain = [('code', 'ilike', '%' + code_suffix)]
        
        # Try to filter by company if available
        accounts = self.env['account.account'].with_context(
            allowed_company_ids=[self.company_id.id]
        ).search(domain, limit=1)
        
        return accounts[0] if accounts else False

    def _get_billing_summary_debit(self):
        """Calculate debit side of billing summary"""
        self.ensure_one()
        
        # Define account codes (last 4 digits)
        AR_ADVERTISER_CODE = '1202'  # 111202
        INTER_CO_RECV_CODE = '1206'  # 111206
        
        result = {
            'ar_advertiser': 0.0,
            'inter_co_recv': 0.0,
            'sundries_code': '',
            'sundries_amount': 0.0,
            'total': 0.0
        }
        
        # Get accounts
        ar_account = self._search_account_by_code(AR_ADVERTISER_CODE)
        inter_co_account = self._search_account_by_code(INTER_CO_RECV_CODE)
        
        # Process invoice lines (debit entries)
        for line in self.line_ids.filtered(lambda l: l.debit > 0):
            if ar_account and line.account_id == ar_account:
                result['ar_advertiser'] += line.debit
            elif inter_co_account and line.account_id == inter_co_account:
                result['inter_co_recv'] += line.debit
            else:
                # Sundries - other debit accounts
                result['sundries_amount'] += line.debit
                if not result['sundries_code']:
                    # Use only last 4 digits of account code
                    code = line.account_id.code
                    result['sundries_code'] = code[-4:] if len(code) >= 4 else code
        
        result['total'] = result['ar_advertiser'] + result['inter_co_recv'] + result['sundries_amount']
        
        return result

    def _get_billing_summary_credit(self):
        """Calculate credit side of billing summary"""
        self.ensure_one()
        
        # Define account codes (last 4 digits)
        AP_TRADE_CODE = '2101'  # 112101
        OUTPUT_VAT_CODE = '2507'  # 112507
        
        result = {
            'ap_trade': 0.0,
            'income_code': '',
            'income_amount': 0.0,
            'output_vat': 0.0,
            'sundries_code': '',
            'sundries_amount': 0.0,
            'total': 0.0
        }
        
        # Get accounts
        ap_trade_account = self._search_account_by_code(AP_TRADE_CODE)
        output_vat_account = self._search_account_by_code(OUTPUT_VAT_CODE)
        
        # Process invoice lines (credit entries)
        for line in self.line_ids.filtered(lambda l: l.credit > 0):
            if ap_trade_account and line.account_id == ap_trade_account:
                result['ap_trade'] += line.credit
            elif output_vat_account and line.account_id == output_vat_account:
                result['output_vat'] += line.credit
            elif line.account_id.account_type in ['income', 'income_other']:
                # Income accounts
                result['income_amount'] += line.credit
                if not result['income_code']:
                    # Use only last 4 digits of account code
                    code = line.account_id.code
                    result['income_code'] = code[-4:] if len(code) >= 4 else code
            else:
                # Sundries - other credit accounts
                result['sundries_amount'] += line.credit
                if not result['sundries_code']:
                    # Use only last 4 digits of account code
                    code = line.account_id.code
                    result['sundries_code'] = code[-4:] if len(code) >= 4 else code
        
        result['total'] = result['ap_trade'] + result['income_amount'] + result['output_vat'] + result['sundries_amount']
        
        return result
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    currency_display = fields.Char(
        related='currency_id.name',
        string='Currency',
        store=True,
        readonly=True
    )

    fx_currency_id = fields.Many2one(
        'res.currency',
        string="Alt Currency",
        # related='move_id.x_alt_currency_id'
    )
    fx_price_unit = fields.Float(
        string="Alt Unit Price",
        help="Unit price in foreign exchange currency"
    )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def get_button_approvers(self):
        """
        Returns the approvers configured in Studio approval button
        :return: recordset of res.users
        """
        self.ensure_one()

        approvers = self.env['res.users']

        # Method 1: Get from approval entries (if approval process has started)
        try:
            entries = self.env['studio.approval.entry'].search([
                ('res_id', '=', self.id),
                ('model', '=', 'purchase.order')
            ])
            if entries:
                approvers = entries.mapped('user_id')
                if approvers:
                    return approvers
        except:
            pass

        # Method 2: Get from approval rules configuration
        try:
            # Get the model record for purchase.order
            model_rec = self.env['ir.model'].search([
                ('model', '=', 'purchase.order')
            ], limit=1)

            if model_rec:
                # Find applicable approval rules
                rules = self.env['studio.approval.rule'].search([
                    ('model_id', '=', model_rec.id),
                    ('active', '=', True)
                ])

                for rule in rules:
                    # Check if rule applies to this record based on domain
                    if rule.domain:
                        try:
                            from odoo.tools.safe_eval import safe_eval
                            domain = safe_eval(rule.domain)
                            # Check if this record matches the domain
                            matching = self.search(
                                domain + [('id', '=', self.id)])
                            if not matching:
                                continue
                        except Exception as e:
                            _logger.warning(
                                f"Error evaluating domain for rule {rule.id}: {e}")
                            continue

                    # Get approvers from the rule via studio.approval.rule.approver
                    rule_approvers = self.env['studio.approval.rule.approver'].search([
                        ('rule_id', '=', rule.id)
                    ])

                    for rule_approver in rule_approvers:
                        if rule_approver.user_id:
                            approvers |= rule_approver.user_id
                        if hasattr(rule_approver, 'group_id') and rule_approver.group_id:
                            approvers |= rule_approver.group_id.users

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Could not fetch approval rules: {e}")

        return approvers


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    employer_approver_only_on_days = fields.Integer(
        string="Manager-Only Approval Threshold (Days)",
        help="If leave days are less than or equal to this value, only manager approval is required (HR approval is skipped)."
    )


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # @api.model
    # def create(self, vals):

    #     raise UserError(self.validation_type)
    #     # Call the parent create method
    #     res = super(HrLeave, self).create(vals)

    #     return res

    # TODO: Dynamic Approval in SL Type if self.duration_display > 3 days then the self.validation_type becomes 'both' else 'manager' only. - Done
    # TODO: Change Second Approval in State Color Purple
    # TODO: INV00001 FORMAT OF INVOICES IN FORMS PDF REPORT - Assigned to Justin
    #  - INV000001 (Billing - Invoice Format)
    #  - BIL000001 - Vendor Bill
    #  - JVN000001 - JV
    #  - SO000001 - CE
    #  - PON000001 - Purchase Order No.
    #  - ORN000001 - Official Receipt
    #

    # IT Team Client Training
    # Discuss General Settings:
    # XLSX Export  / Import Feature
    # Discuss Studio:
    # Discuss Approval Studio:
    # Discuss Access Rights:
    # Discuss Record Rules:
    # Discuss Client and Product Assignments:
    # Discuss Installation of Applications:

    def _get_responsible_for_approval(self):
        self.ensure_one()
        responsible = self.env['res.users']

        leave_type = self.holiday_status_id
        threshold = leave_type.employer_approver_only_on_days
        is_short_leave = threshold and self.number_of_days <= threshold
        is_dual_validation = self.validation_type == 'both'

        # Determine the effective validation type without modifying the record
        effective_validation_type = self.validation_type

        # If the leave duration is within the configured short-leave threshold
        # and the leave type normally requires both manager and HR approval,
        # downgrade the approval flow to employer/manager-only.
        if is_dual_validation and is_short_leave and threshold:
            effective_validation_type = 'manager'

        # SWAP: HR OFFICER FIRST (confirm state)
        if effective_validation_type == 'hr' or (effective_validation_type == 'both' and self.state == 'confirm'):
            if self.holiday_status_id.responsible_ids:
                responsible = self.holiday_status_id.responsible_ids

        # SWAP: MANAGER SECOND (validate1 state)
        elif effective_validation_type == 'manager' or (effective_validation_type == 'both' and self.state == 'validate1'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
            elif self.employee_id.parent_id.user_id:
                responsible = self.employee_id.parent_id.user_id

        return responsible

    # Disable Probationary Leave Restriction
    # @api.model
    # def create(self, vals):
    #     # Check if employee_id and holiday_status_id are in vals
    #     if vals.get('employee_id') and vals.get('holiday_status_id') == 5:
    #         # Get the employee record
    #         employee = self.env['hr.employee'].sudo().browse(
    #             vals.get('employee_id'))

    #         # Check if employment start date is set
    #         if employee.x_studio_employment_start_date:
    #             # Get the request date from vals
    #             request_date = fields.Date.from_string(
    #                 vals.get('request_date_from'))
    #             employment_start = employee.x_studio_employment_start_date
    #             delta = relativedelta(request_date, employment_start)

    #             # Calculate when 6 months will be completed
    #             six_months_date = employment_start + relativedelta(months=6)
    #             remaining_delta = relativedelta(six_months_date, request_date)

    #             # If less than 6 months at the time of request, raise error with details
    #             if delta.months < 6 and delta.years == 0:
    #                 raise UserError(
    #                     f'You are still in probationary period.\n\n'
    #                     f'Employment Start Date: {employment_start.strftime("%B %d, %Y")}\n'
    #                     f'Requested Leave Date: {request_date.strftime("%B %d, %Y")}\n'
    #                     f'Time Employed by Request Date: {delta.months} month(s) and {delta.days} day(s)\n'
    #                     f'Remaining Time: {remaining_delta.months} month(s) and {remaining_delta.days} day(s)\n'
    #                     f'This time off type can be used starting {six_months_date.strftime("%B %d, %Y")}.'
    #                 )

    #     # Call the parent create method
    #     res = super(HrLeave, self).create(vals)

    #     return res


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    x_has_cash_advance_line_ids = fields.Boolean(
        string="Has Cash Advance Lines", compute="_compute_x_has_cash_advance_line_ids", store=True)

    @api.depends('expense_line_ids.x_studio_cash_advance_series')
    def _compute_x_has_cash_advance_line_ids(self):
        for record in self:
            record.x_has_cash_advance_line_ids = any(
                line.x_studio_cash_advance_series for line in record.expense_line_ids
            )

class JournalReportCustomHandler(models.AbstractModel):
    _inherit = "account.journal.report.handler"
    
    
    def _get_columns_for_journal(self, journal, export_type='pdf'):
        """
        Creates a columns list that will be used in this journal for the pdf report

        :return: A list of the columns as dict each having:
            - name (mandatory):     A string that will be displayed
            - label (mandatory):    A string used to link lines with the column
            - class (optional):     A string with css classes that need to be applied to all that column
        """
        columns = [
            {'name': _('Document'), 'label': 'document'},
        ]

        # We have different columns regarding we are exporting to a PDF file or an XLSX document
        if export_type == 'pdf':
            columns.append({'name': _('Account'), 'label': 'account_label'})
        else:
            columns.extend([
                {'name': _('Account Code'), 'label': 'account_code'},
                {'name': _('Account Label'), 'label': 'account_label'}
            ])

        columns.extend([
            {'name': _('Name'), 'label': 'name'},
            {'name': _('Debit'), 'label': 'debit', 'class': 'o_right_alignment '},
            {'name': _('Credit'), 'label': 'credit', 'class': 'o_right_alignment '},
        ])
        # HERE TAXES COLUMN ARE DISABLED FOR NOW MARKIE
        # if journal.get('tax_summary'):
        #     columns.append(
        #         {'name': _('Taxes'), 'label': 'taxes'},
        #     )
        #     if journal['tax_summary'].get('tax_grid_summary_lines'):
        #         columns.append({'name': _('Tax Grids'), 'label': 'tax_grids'})

        if self._should_use_bank_journal_export(journal):
            columns.append({
                'name': _('Balance'),
                'label': 'balance',
                'class': 'o_right_alignment '
            })

            if journal.get('multicurrency_column'):
                columns.append({
                    'name': _('Amount Currency'),
                    'label': 'amount_currency',
                    'class': 'o_right_alignment '
                })

        return columns