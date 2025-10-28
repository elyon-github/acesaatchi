from odoo import models
import datetime
from xlsxwriter.workbook import Workbook
from odoo.exceptions import ValidationError, UserError
import pytz
import logging

_logger = logging.getLogger(__name__)

class SaatchiXLSX(models.AbstractModel):
    _name = 'report.saatchi_soa_xlsx'
    _inherit = 'report.report_xlsx.abstract'

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
        
        # Normal cell format
        normal_format = workbook.add_format({
            **base_font,
            'align': 'left',
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
        
        # Currency format
        currency_format = workbook.add_format({
            **base_font,
            'num_format': '#,##0.00',
            'align': 'right',
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
        
        # Total currency format
        total_currency_format = workbook.add_format({
            **base_font,
            'bold': True,
            'num_format': '#,##0.00',
            'bg_color': '#000000',
            'font_color': 'white',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1
        })
        
        return {
            'company': company_format,
            'title': title_format,
            'report_date': report_date_format,
            'black_header': black_header_format,
            'normal': normal_format,
            'date': date_format,
            'currency': currency_format,
            'total': total_format,
            'total_currency': total_currency_format
        }

    def generate_header(self, sheet, partner_name, report_date, formats):
        """Generate report header."""
        sheet.write(0, 0, partner_name, formats['company'])
        sheet.write(1, 0, 'Statement of Account', formats['title'])
        sheet.write(2, 0, report_date, formats['report_date'])

    def generate_table_header(self, sheet, row, formats):
        """Generate table column headers."""
        # Column headers with months
        headers = [
            ('', 3),  # Client (3 columns merged)
            ('METROBANK', 1),
            ('Project Title', 1),
            ('Invoice #', 1),
            ('Date', 1),
            ('Total', 1),
            ('JUNE 2025', 1),
            ('MAY 2025', 1),
            ('APRIL 2025', 1),
            ('MARCH 2025', 1),
            ('FEBRUARY 2025', 1)
        ]
        
        col = 0
        for header, span in headers:
            if span > 1:
                sheet.merge_range(row, col, row, col + span - 1, header, formats['black_header'])
            else:
                sheet.write(row, col, header, formats['black_header'])
            col += span
        
        sheet.set_row(row, 25)

    def generate_summary(self, sheet, row, totals, formats):
        """Generate summary totals."""
        sheet.merge_range(row, 0, row, 2, 'TOTAL', formats['total'])
        sheet.write(row, 3, '', formats['total'])
        sheet.write(row, 4, '', formats['total'])
        sheet.write(row, 5, '', formats['total'])
        sheet.write(row, 6, '', formats['total'])
        sheet.write(row, 7, totals['total'], formats['total_currency'])
        sheet.write(row, 8, totals['june'], formats['total_currency'])
        sheet.write(row, 9, totals['may'], formats['total_currency'])
        sheet.write(row, 10, totals['april'], formats['total_currency'])
        sheet.write(row, 11, totals['march'], formats['total_currency'])
        sheet.write(row, 12, totals['february'], formats['total_currency'])
        
        sheet.set_row(row, 25)

    def generate_xlsx_report(self, workbook, data, lines):
        """Main report generation method."""
        formats = self._define_formats(workbook)
        
        # Group invoices by partner
        by_partner = {}
        for move in lines:
            if move.move_type in ['out_invoice', 'out_refund'] and move.state == 'posted':
                partner_name = move.partner_id.name or 'Unknown'
                by_partner.setdefault(partner_name, []).append(move)
        
        # Get current date for report
        report_date = datetime.datetime.now().strftime('%B %d, %Y').upper()
        
        # Generate a sheet per partner
        for partner_name, moves in by_partner.items():
            # Create sheet (max 31 chars for sheet name)
            sheet = workbook.add_worksheet(partner_name[:31])
            
            # Set column widths
            sheet.set_column(0, 0, 18)   # PO# (blank for now)
            sheet.set_column(1, 1, 12)   # CE# (blank for now)
            sheet.set_column(2, 2, 25)   # Client (blank for now)
            sheet.set_column(3, 3, 15)   # METROBANK
            sheet.set_column(4, 4, 40)   # Project Title
            sheet.set_column(5, 5, 15)   # Invoice #
            sheet.set_column(6, 6, 12)   # Date
            sheet.set_column(7, 7, 15)   # Total
            sheet.set_column(8, 8, 15)   # JUNE 2025
            sheet.set_column(9, 9, 15)   # MAY 2025
            sheet.set_column(10, 10, 15)  # APRIL 2025
            sheet.set_column(11, 11, 15)  # MARCH 2025
            sheet.set_column(12, 12, 15)  # FEBRUARY 2025
            
            # Generate header
            self.generate_header(sheet, partner_name, report_date, formats)
            
            # Generate table header at row 4 (index 3)
            self.generate_table_header(sheet, 3, formats)
            
            # Sort moves by date
            moves_sorted = sorted(moves, key=lambda x: x.invoice_date or x.date)
            
            # Initialize totals
            totals = {
                'total': 0,
                'june': 0,
                'may': 0,
                'april': 0,
                'march': 0,
                'february': 0
            }
            
            # Write data rows starting at row 5 (index 4)
            row = 4
            
            for move in moves_sorted:
                amount = move.amount_total if move.move_type == 'out_invoice' else -move.amount_total
                totals['total'] += amount
                
                # Determine which month column to populate based on invoice date
                inv_date = move.invoice_date or move.date
                if inv_date:
                    month_year = inv_date.strftime('%B %Y').upper()
                    month_col_amount = amount
                    
                    # Map to correct month column
                    if 'JUNE 2025' in month_year:
                        totals['june'] += month_col_amount
                    elif 'MAY 2025' in month_year:
                        totals['may'] += month_col_amount
                    elif 'APRIL 2025' in month_year:
                        totals['april'] += month_col_amount
                    elif 'MARCH 2025' in month_year:
                        totals['march'] += month_col_amount
                    elif 'FEBRUARY 2025' in month_year:
                        totals['february'] += month_col_amount
                else:
                    month_col_amount = 0
                
                # Write row data
                sheet.write(row, 0, '', formats['normal'])  # PO# - blank
                sheet.write(row, 1, '', formats['normal'])  # CE# - blank
                sheet.write(row, 2, '', formats['normal'])  # Client - blank
                sheet.write(row, 3, move.partner_id.ref or '', formats['normal'])  # METROBANK
                sheet.write(row, 4, move.invoice_origin or move.ref or '', formats['normal'])  # Project Title
                sheet.write(row, 5, move.name or '', formats['normal'])  # Invoice #
                sheet.write(row, 6, inv_date, formats['date'])  # Date
                sheet.write(row, 7, amount, formats['currency'])  # Total
                
                # Month columns - only populate the matching month
                sheet.write(row, 8, month_col_amount if 'JUNE 2025' in month_year else '', formats['currency'])
                sheet.write(row, 9, month_col_amount if 'MAY 2025' in month_year else '', formats['currency'])
                sheet.write(row, 10, month_col_amount if 'APRIL 2025' in month_year else '', formats['currency'])
                sheet.write(row, 11, month_col_amount if 'MARCH 2025' in month_year else '', formats['currency'])
                sheet.write(row, 12, month_col_amount if 'FEBRUARY 2025' in month_year else '', formats['currency'])
                
                sheet.set_row(row, 20)
                row += 1
            
            # Generate summary
            self.generate_summary(sheet, row, totals, formats)
        
        return True