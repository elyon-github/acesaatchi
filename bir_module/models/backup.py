def get_bir_quarter(self, value):
        quarter = 0
        month = int(value.month)

        if month <= 4: quarter = 1
        elif month <= 8 and month > 4: quarter = 2
        elif month <= 12 and month > 8: quarter = 3
        else: quarter = 1

        return str(quarter)

    def get_monthly_sales_vat(self, value, const, q_index):
        query = "SELECT D.name,D.amount,B.price_subtotal,F.name FROM account_move A "
        query += "LEFT JOIN account_move_line B ON B.move_id = A.id AND B.exclude_from_invoice_tab = 'false' "
        query += "INNER JOIN account_move_line_account_tax_rel C ON C.account_move_line_id = B.id "
        query += "LEFT JOIN account_tax D ON D.id = C.account_tax_id "
        query += "LEFT JOIN res_partner E ON E.id = A.partner_id "
        query += "LEFT JOIN res_partner_industry F ON F.id = E.industry_id "
        if const == 'quar':
            if q_index == 1:
                query += "WHERE (EXTRACT(MONTH FROM A.date) = '1' OR EXTRACT(MONTH FROM A.date) = '2' OR EXTRACT(MONTH FROM A.date) = '3' OR EXTRACT(MONTH FROM A.date) = '4') AND EXTRACT(YEAR FROM A.date) = '"+str(value.year)+"' AND A.move_type = 'out_invoice' AND a.state = 'posted'"
            elif q_index == 2:
                query += "WHERE (EXTRACT(MONTH FROM A.date) = '5' OR EXTRACT(MONTH FROM A.date) = '6' OR EXTRACT(MONTH FROM A.date) = '7' OR EXTRACT(MONTH FROM A.date) = '8') AND EXTRACT(YEAR FROM A.date) = '"+str(value.year)+"' AND A.move_type = 'out_invoice' AND a.state = 'posted'"
            else:
                query += "WHERE (EXTRACT(MONTH FROM A.date) = '9' OR EXTRACT(MONTH FROM A.date) = '10' OR EXTRACT(MONTH FROM A.date) = '11' OR EXTRACT(MONTH FROM A.date) = '12') AND EXTRACT(YEAR FROM A.date) = '"+str(value.year)+"' AND A.move_type = 'out_invoice' AND a.state = 'posted'"
        else:
            query += "WHERE EXTRACT(MONTH FROM A.date) = '" + str(value.month) + "' AND EXTRACT(YEAR FROM A.date) = '"+str(value.year)+"' AND A.move_type = 'out_invoice' AND a.state = 'posted'"

        self._cr.execute(query)
        val = self._cr.fetchall()

        zero_rated = 0
        vat_private,private_sub,vat_govt,govt_sub = 0,0,0,0
        sub_total,vat_total = 0,0
        # private_sub = 0
        # vat_govt = 0
        # govt_sub = 0
        ret = []
        for sub in val:
            if sub[1] == 0:
                zero_rated += sub[2]
            else:
                if sub[3] != 'Government':
                    vat_private += ((sub[1]/100)*sub[2])
                    private_sub += sub[2]
                else:
                    vat_govt += ((sub[1]/100)*sub[2])
                    govt_sub += sub[2]
        sub_total = private_sub + govt_sub
        vat_total = vat_private + vat_govt
        return [round(vat_private,2),round(private_sub,2),round(vat_govt,2),round(govt_sub,2),round(zero_rated,2),round(sub_total,2),round(vat_total,2)]

    def get_form_purchase_vat(self, value, form):
        sub = {'Local Goods' : 0, 'Foreign Goods': 0, 'Local Services': 0, 'Foreign Services': 0, 'Tax excempt': 0}
        tax = {'Local Goods' : 0, 'Foreign Goods': 0, 'Local Services': 0, 'Foreign Services': 0}

        query = "SELECT T3.name, T3.amount, T3.tax_scope, T1.price_subtotal, T0.name "
        query += "FROM account_move T0 "
        query += "LEFT JOIN account_move_line T1 ON T0.id = T1.move_id AND T1.exclude_from_invoice_tab = 'false' "
        query += "LEFT JOIN account_move_line_account_tax_rel T2 ON T2.account_move_line_id = T1.id "
        query += "LEFT JOIN account_tax T3 ON T3.id = T2.account_tax_id "

        if form == '2550M':
            query += "WHERE EXTRACT(MONTH FROM T0.date) = '" + str(value.month) + "' AND EXTRACT(YEAR FROM T0.date) = '"+str(value.year)+"' "
        else:
            quarter_month = self.get_quarter_months(float(value.month))
            query += "WHERE EXTRACT(MONTH FROM T0.date) >= '"+quarter_month[0]+"' AND EXTRACT(MONTH FROM T0.date) <= '"+quarter_month[1]+"' AND EXTRACT(YEAR FROM T0.date) = '"+str(value.year)+"' "
        query += " AND T0.move_type = 'in_invoice' AND T0.state = 'posted'"

        self._cr.execute(query)
        val = self._cr.fetchall()

        for dat in val:
            if dat[0] == "" or dat[1] == 0 or dat[0] == None:
                sub['Tax excempt'] += float(dat[3])
            elif str(dat[2]) == 'consu' or 'Goods' in str(dat[1]):
                if 'Local' in str(dat[0]):
                    sub['Local Goods'] += float(dat[3])
                    tax['Local Goods'] += (float(dat[3]) * (float(dat[1]) / 100))
                else:
                    sub['Foreign Goods'] += float(dat[3])
                    tax['Foreign Goods'] += (float(dat[3]) * (float(dat[1]) / 100))
            else:
                if 'Local' in str(dat[0]):
                    sub['Local Services'] += float(dat[3])
                    tax['Local Services'] += (float(dat[3]) * (float(dat[1]) / 100))
                else:
                    sub['Foreign Services'] += float(dat[3])
                    tax['Local Services'] += (float(dat[3]) * (float(dat[1]) / 100))

        return sub, tax

    def get_quarter_months(self, month):
        val = []
        if month >= 1 and month <= 3:
            val = ['1', '3']
        elif month >= 4 and month <= 6:
            val = ['4', '6']
        elif month >= 7 and month <= 9:
            val = ['7', '9']
        else:
            val = ['10', '12']

        return val

    def month_or_quarter(self, value):
        val = []
        if value.month == 4:
            val = self.get_monthly_sales_vat(value, 'quar', 1)
        elif value.month == 8:
            val = self.get_monthly_sales_vat(value, 'quar', 2)
        elif value.month == 12:
            val = self.get_monthly_sales_vat(value, 'quar', 3)
        else:
            val = self.get_monthly_sales_vat(value, 'mos', 0)

        return val

    def get_2307_vals(self, date, id_num):
        lineitems = self.get_2307_lineitems(id_num)
        landedcost = self.get_2307_landedcost(id_num)
        return lineitems, landedcost

    def get_2307_lineitems(self, id_num):
        query = "SELECT T0.price_subtotal, T2.name, T2.amount, T2.tax_scope, T4.landed_cost_ok, T4.name "
        query += "FROM account_move_line T0 "
        query += "LEFT JOIN account_move_line_account_tax_rel T1 ON T1.account_move_line_id = T0.id "
        query += "LEFT JOIN account_tax T2 ON T2.id = T1.account_tax_id "
        query += "LEFT JOIN product_product T3 ON T3.id = T0.product_id "
        query += "LEFT JOIN product_template T4 ON T4.id = T3.product_tmpl_id "
        query += "WHERE T0.move_id = '"+str(id_num)+"' AND T0.exclude_from_invoice_tab = 'false' AND (T0.is_landed_costs_line = 'false' OR T0.is_landed_costs_line IS NULL) "

        self._cr.execute(query)
        val = self._cr.fetchall()

        return self.extract_ewt(val)

    def get_2307_landedcost(self, id_num):
        query = "SELECT T0.price_subtotal, T2.name, T2.amount, T2.tax_scope, T4.landed_cost_ok, T4.name "
        query += "FROM account_move_line T0 "
        query += "LEFT JOIN account_move_line_account_tax_rel T1 ON T1.account_move_line_id = T0.id "
        query += "LEFT JOIN account_tax T2 ON T2.id = T1.account_tax_id "
        query += "LEFT JOIN product_product T3 ON T3.id = T0.product_id "
        query += "LEFT JOIN product_template T4 ON T4.id = T3.product_tmpl_id "
        query += "LEFT JOIN product_supplierinfo T5 ON T5.product_tmpl_id = T3.id "
        query += "LEFT JOIN res_partner T6 ON T6.id = T5.name "
        query += "WHERE T0.move_id = '"+str(id_num)+"' AND T0.exclude_from_invoice_tab = 'false' AND T0.is_landed_costs_line = 'true' "

        self._cr.execute(query)
        val = self._cr.fetchall()

        return self.extract_ewt(val)

    def extract_ewt(self, val):
        new_val = []
        for ewt in val:
            ewt_amt = float(ewt[0]) * (abs(float(ewt[2])) / 100)
            if "EWT" in ewt[1]:
                new_val.append((ewt[0], ewt_amt, abs(float(ewt[2])), ewt[1], ewt[3], ewt[4], ewt[5]))

        return new_val