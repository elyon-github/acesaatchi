# -*- coding: utf-8 -*-
{
    'name': 'Account Reports PDF Header Repeat',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Makes PDF report headers repeat on every page',
    'description': 'This module ensures that the company header and column headers repeat on every page in PDF exports of accounting reports.',
    'author': 'Custom',
    'depends': ['account_reports'],
    'data': [
        'data/pdf_export_templates.xml',
        'data/customer_reports_pdf_export_templates.xml',
    ],
    'assets': {
        'account_reports.assets_pdf_export': [
            'static/src/scss/account_pdf_export_template.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
}
