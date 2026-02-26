# -*- coding: utf-8 -*-
{
    'name': "Saatchi XLSX Reports",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Mark Angelo S. Templanza / Elyon IT Consultant",
    'website': "https://www.elyon-solutions.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'report_xlsx', 'account', 'saatchi_customized_accrued_revenue'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/accrued_revenue_wizard_view.xml',
        'views/revenue_report_wizard_view.xml',
        'reports/saatchi_xlsx_reports.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'saatchi_soa/static/src/js/accrued_revenue_list_controller.js',
            'saatchi_soa/static/src/xml/accrued_revenue_list_buttons.xml',
        ],
    },
}
