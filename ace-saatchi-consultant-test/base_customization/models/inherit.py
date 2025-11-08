# -*- coding: utf-8 -*-
from odoo import models, fields, api

class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'
    
    x_client_product_ce_code = fields.One2many(
        'base_customization.sale_order_ce_line',  # Use the NEW separate model
        'sale_order_id',
        string="Client - Product CE Code"
    )


    
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
            
            self.x_client_product_ce_code = [(5, 0, 0)] + line_vals  # Clear and add new
        else:
            self.x_client_product_ce_code = [(5, 0, 0)]  # Clear all

class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    fx_currency_id = fields.Many2one(
        'res.currency', 
        string="FX Currency",
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False)
    )
    fx_price_unit = fields.Float(
        string="FX Unit Price",
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
    
    @api.onchange('price_unit')
    def _onchange_price_unit_to_fx(self):
        """Convert price_unit (company currency) to fx_price_unit"""
        # Mark that price_unit was edited
        self._last_edited_price_field = 'price_unit'
        
        if self.price_unit and self.fx_currency_id:
            company_currency = self.order_id.company_id.currency_id or self.env.company.currency_id
            if company_currency and company_currency != self.fx_currency_id:
                # Convert from company currency to FX currency
                self.fx_price_unit = company_currency._convert(
                    self.price_unit,
                    self.fx_currency_id,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today()
                )
            elif company_currency == self.fx_currency_id:
                self.fx_price_unit = self.price_unit
    
    @api.onchange('fx_price_unit')
    def _onchange_fx_price_unit_to_price(self):
        """Convert fx_price_unit to price_unit (company currency)"""
        # Only convert if fx_price_unit was the last field edited by user
        # This prevents the chain reaction when price_unit triggers fx_price_unit change
        if self._last_edited_price_field == 'price_unit':
            # Reset the flag
            self._last_edited_price_field = None
            return
        
        # Mark that fx_price_unit was edited
        self._last_edited_price_field = 'fx_price_unit'
        
        if self.fx_price_unit and self.fx_currency_id:
            company_currency = self.order_id.company_id.currency_id or self.env.company.currency_id
            if company_currency and company_currency != self.fx_currency_id:
                # Convert from FX currency to company currency
                self.price_unit = self.fx_currency_id._convert(
                    self.fx_price_unit,
                    company_currency,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today()
                )
            elif company_currency == self.fx_currency_id:
                self.price_unit = self.fx_price_unit