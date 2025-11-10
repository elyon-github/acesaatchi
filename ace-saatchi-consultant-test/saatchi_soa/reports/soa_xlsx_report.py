from odoo import models
import datetime
from xlsxwriter.workbook import Workbook
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import pytz
import logging

_logger = logging.getLogger(__name__)

class SaatchiXLSX(models.AbstractModel):
    _name = 'report.saatchi_soa_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description ='xlsx.report'

    def _define_formats(self, workbook):
        """Define and return format objects."""
        base_font = {'font_name': 'Calibri', 'font_size': 10}
        
        # Company name format
        company_format = workbook.add_format({
            **base_font,
            'bold': True,
            'font_size': 11
        })
        
        # Title format
        title_format = workbook.add_format({
            **base_font,
            'bold': True,
            'font_size': 11
        })
        
        # Date format (for the report date)
        report_date_format = workbook.add_format({
            **base_font,
            'font_size': 10
        })
        
        # Black header format
        black_header_format = workbook.add_format({
            **base_font,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#000000',
            'font_color': 'white',
            'border': 1
        })
        
        # Top label format (no black background, no border)
        top_label_format = workbook.add_format({
            **base_font,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Normal cell format
        normal_format = workbook.add_format({
            **base_font,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Centered cell format
        centered_format = workbook.add_format({
            **base_font,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Date cell format
        date_format = workbook.add_format({
            **base_font,
            'num_format': 'mm/dd/yyyy',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Total row format (black background)
        total_format = workbook.add_format({
            **base_font,
            'bold': True,
            'bg_color': '#000000',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        return {
            'company': company_format,
            'title': title_format,
            'report_date': report_date_format,
            'black_header': black_header_format,
            'top_label': top_label_format,
            'normal': normal_format,
            'centered': centered_format,
            'date': date_format,
            'total': total_format
        }

    def _get_aging_months(self):
        """Generate list of 5 aging buckets (last 4 months + over 120 days)."""
        today = datetime.date.today()
        months = []
        
        # Get last 4 months
        for i in range(4):
            month_date = today - relativedelta(months=i)
            month_str = month_date.strftime('%B %Y').upper()
            months.append({
                'label': month_str,
                'start_date': month_date.replace(day=1),
                'end_date': (month_date.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)
            })
        
        # Add "Over 120 Days" bucket
        over_120_date = today - relativedelta(days=120)
        months.append({
            'label': 'OVER 120 DAYS',
            'start_date': None,
            'end_date': over_120_date
        })
        
        return months

    def _get_month_bucket(self, inv_date, aging_months):
        """Determine which aging bucket the invoice falls into."""
        if not inv_date:
            return None
        
        for i, month in enumerate(aging_months):
            if month['label'] == 'OVER 120 DAYS':
                # Last bucket catches everything older
                if inv_date <= month['end_date']:
                    return i
            else:
                if month['start_date'] <= inv_date <= month['end_date']:
                    return i
        
        return None

    def _create_currency_format(self, workbook, currency_symbol, base_font):
        """Create currency format with symbol."""
        return workbook.add_format({
            **base_font,
            'num_format': f'{currency_symbol}#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1
        })
    
    def _create_total_currency_format(self, workbook, currency_symbol, base_font):
        """Create total currency format with symbol."""
        return workbook.add_format({
            **base_font,
            'bold': True,
            'num_format': f'{currency_symbol}#,##0.00',
            'bg_color': '#000000',
            'font_color': 'white',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1
        })

    def generate_header(self, sheet, company_name, report_date, formats):
        """Generate report header."""
        sheet.write(0, 0, company_name, formats['company'])
        sheet.write(1, 0, 'Statement of Account', formats['title'])
        sheet.write(2, 0, report_date, formats['report_date'])

    def generate_table_header(self, sheet, row, aging_months, currency_code, formats):
        """Generate table column headers with dynamic months."""
        # Currency label row
        sheet.write(row, 0, f'CURRENCY: {currency_code}', formats['top_label'])
        for i in range(1, 7 + len(aging_months)):
            sheet.write(row, i, '', formats['top_label'])
        
        # Row 1: Client and METROBANK labels (no black background)
        row += 1
        sheet.write(row, 0, '', formats['top_label'])
        sheet.write(row, 1, 'Client', formats['top_label'])
        sheet.write(row, 2, '', formats['top_label'])
        sheet.write(row, 3, 'METROBANK', formats['top_label'])
        sheet.write(row, 4, '', formats['top_label'])
        sheet.write(row, 5, '', formats['top_label'])
        sheet.write(row, 6, '', formats['top_label'])
        
        # Month headers
        for i, month in enumerate(aging_months):
            sheet.write(row, 7 + i, '', formats['top_label'])
        
        # Row 2: Actual column headers (with black background)
        row += 1
        sheet.write(row, 0, 'PO#', formats['black_header'])
        sheet.write(row, 1, 'CE#', formats['black_header'])
        sheet.write(row, 2, '', formats['black_header'])
        sheet.write(row, 3, 'Project Title', formats['black_header'])
        sheet.write(row, 4, 'Invoice #', formats['black_header'])
        sheet.write(row, 5, 'Date', formats['black_header'])
        sheet.write(row, 6, 'Total', formats['black_header'])
        
        # Dynamic month columns
        for i, month in enumerate(aging_months):
            sheet.write(row, 7 + i, month['label'], formats['black_header'])
        
        sheet.set_row(row - 2, 18)
        sheet.set_row(row - 1, 18)
        sheet.set_row(row, 18)
        
        return row

    def generate_summary(self, sheet, row, totals, aging_months, currency_code, formats):
        """Generate summary totals."""
        sheet.merge_range(row, 0, row, 1, f'TOTAL {currency_code}', formats['total'])
        sheet.write(row, 2, '', formats['total'])
        sheet.write(row, 3, '', formats['total'])
        sheet.write(row, 4, '', formats['total'])
        sheet.write(row, 5, '', formats['total'])
        sheet.write(row, 6, totals['total'], formats['total_currency'])
        
        # Dynamic month totals
        for i in range(len(aging_months)):
            sheet.write(row, 7 + i, totals['months'][i], formats['total_currency'])
        
        sheet.set_row(row, 18)
        
        return row

    def generate_xlsx_report(self, workbook, data, lines):
        """Main report generation method."""
        formats = self._define_formats(workbook)
        aging_months = self._get_aging_months()
        base_font = {'font_name': 'Calibri', 'font_size': 10}
        
        # Group invoices by partner and currency
        by_partner = {}
        company_name = None
        
        for move in lines:
            if move.move_type in ['out_invoice', 'out_refund'] and move.state == 'posted':
                # Get company name from first move
                if not company_name and move.company_id:
                    company_name = move.company_id.name
                    
                partner_name = move.partner_id.name or 'Unknown'
                currency = move.currency_id
                currency_key = f"{currency.name}_{currency.id}" if currency else 'NO_CURRENCY'
                
                if partner_name not in by_partner:
                    by_partner[partner_name] = {}
                if currency_key not in by_partner[partner_name]:
                    by_partner[partner_name][currency_key] = {
                        'currency': currency,
                        'moves': []
                    }
                    
                by_partner[partner_name][currency_key]['moves'].append(move)
        
        # Get current date for report
        report_date = datetime.datetime.now().strftime('%B %d, %Y').upper()
        
        # Fallback company name if not found
        if not company_name:
            company_name = 'Company Name'
        
        # Generate a sheet per partner
        for partner_name, currencies in by_partner.items():
            # Create sheet (max 31 chars for sheet name)
            sheet = workbook.add_worksheet(partner_name[:31])
            
            # Set column widths
            sheet.set_column(0, 0, 18)   # PO#
            sheet.set_column(1, 1, 12)   # CE#
            sheet.set_column(2, 2, 15)   # METROBANK ref
            sheet.set_column(3, 3, 40)   # Project Title
            sheet.set_column(4, 4, 15)   # Invoice #
            sheet.set_column(5, 5, 12)   # Date
            sheet.set_column(6, 6, 15)   # Total
            
            # Dynamic month columns
            for i in range(len(aging_months)):
                sheet.set_column(7 + i, 7 + i, 15)
            
            # Generate header
            self.generate_header(sheet, company_name, report_date, formats)
            
            # Starting row for tables
            current_row = 3
            
            # Generate a table for each currency
            for currency_key, currency_data in currencies.items():
                currency = currency_data['currency']
                moves = currency_data['moves']
                
                # Get currency code and symbol from Odoo currency model
                currency_code = currency.name if currency else 'N/A'
                currency_symbol = currency.symbol if currency else ''
                
                # Create currency-specific formats
                currency_format = self._create_currency_format(workbook, currency_symbol, base_font)
                total_currency_format = self._create_total_currency_format(workbook, currency_symbol, base_font)
                
                # Generate table header
                header_end_row = self.generate_table_header(sheet, current_row, aging_months, currency_code, formats)
                
                # Sort moves by due date
                moves_sorted = sorted(moves, key=lambda x: x.invoice_date_due or x.invoice_date or x.date)
                
                # Initialize totals
                totals = {
                    'total': 0,
                    'months': [0] * len(aging_months)
                }
                
                # Write data rows
                row = header_end_row + 1
                
                for move in moves_sorted:
                    amount = move.amount_total if move.move_type == 'out_invoice' else -move.amount_total
                    totals['total'] += amount
                    
                    # Determine which month bucket this invoice belongs to based on due date
                    due_date = move.invoice_date_due or move.invoice_date or move.date
                    bucket_index = self._get_month_bucket(due_date, aging_months)
                    
                    if bucket_index is not None:
                        totals['months'][bucket_index] += amount
                    
                    # Invoice date for display
                    inv_date = move.invoice_date or move.date
                    
                    # Write row data
                    sheet.write(row, 0, move.ref, formats['normal'])  # PO# - blank for now
                    sheet.write(row, 1, '', formats['normal'])  # CE# - blank for now
                    sheet.write(row, 2, move.partner_id.ref or '', formats['normal'])  # METROBANK
                    sheet.write(row, 3, move.invoice_origin or move.ref or '', formats['centered'])  # Project Title
                    sheet.write(row, 4, move.name or '', formats['centered'])  # Invoice #
                    sheet.write(row, 5, inv_date, formats['date'])  # Date
                    sheet.write(row, 6, amount, currency_format)  # Total with currency
                    
                    # Month columns - only populate the matching bucket
                    for i in range(len(aging_months)):
                        if i == bucket_index:
                            sheet.write(row, 7 + i, amount, currency_format)
                        else:
                            sheet.write(row, 7 + i, '-', formats['centered'])
                    
                    sheet.set_row(row, 20)
                    row += 1
                
                # Generate summary with currency-specific format
                formats_with_currency = {**formats, 'total_currency': total_currency_format}
                current_row = self.generate_summary(sheet, row, totals, aging_months, currency_code, formats_with_currency)
                
                # Add spacing before next currency table
                current_row += 2
        
        return True