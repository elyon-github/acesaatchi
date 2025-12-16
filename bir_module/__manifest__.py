# -*- coding: utf-8 -*-
{
    'name': "BIR Compliance",
    'summary': "BIR Compliance Module",
    'description': """
        Long description of module's purpose
    """,
    'author': "Jerome Campana, Elyon Solutions International Inc.",
    'website': "www.elyon-solutions.com",
    'category': 'Accounting',
    'version': '18.0.1.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'web'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/bir_inherit.xml',
        'views/templates.xml',
        'reports/form_2307_transactional.xml',
        'reports/bir_form_2550M.xml',
        'reports/bir_form_2550Q.xml',
        'reports/bir_form_2307.xml',
        'reports/bir_form_2307_preview.xml',
        'reports/bir_form_1601e.xml',
        'reports/paper_format.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            # IMPORTANT: Load jQuery FIRST (before DataTables)
            'https://code.jquery.com/jquery-3.7.1.min.js',

            # Then load DataTables CSS
            'https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css',
            'https://cdn.datatables.net/responsive/2.3.0/css/responsive.bootstrap.min.css',

            # Then load DataTables JS (after jQuery)
            'https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js',

            # Your CSS
            'bir_module/static/src/css/style.css',

            # Load utility functions first
            'bir_module/static/src/js/bir_utils.js',

            # Load all components
            'bir_module/static/src/js/bir_forms.js',
            'bir_module/static/src/js/sawt_report.js',
            'bir_module/static/src/js/map_report.js',
            'bir_module/static/src/js/sls_report.js',
            'bir_module/static/src/js/slp_report.js',
            'bir_module/static/src/js/print_history.js',

            # Load templates
            'bir_module/static/src/xml/bir_forms_templates.xml',
        ],
        'web.assets_qweb': [
            "bir_module/static/src/xml/reports_body.xml",
        ],
    },
    'license': 'LGPL-3',
}
