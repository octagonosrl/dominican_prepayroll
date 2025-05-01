# -*- coding: utf-8 -*-
{
    'name': "Dominican PrePayroll",

    'summary': """Prenómina Dominicana""",

    'description': """
            Aplicación para habilitar la posibilidad de optener la prenómina
    """,

    'author': "Pablo Mercedes",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Localization/Payroll',
    'version': '14.0.0.1',
    'application': True,
    'installable': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'payroll'],
    'images': ['static/description/icon.png'],

    # always loaded
    'data':
        [
            'security/ir.model.access.csv',
            'security/groups.xml',
            'report/payroll_report.xml',
            'views/prepayroll_view.xml',
            'report/payslip_view.xml',
            'wizards/prepayroll_wizard.xml',
        ]
}
