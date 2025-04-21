# -*- coding: utf-8 -*-
{
    'name': "Dominican PrePayroll",

    'summary': """Prenómina Dominicana""",

    'description': """
            Aplicación para habilitar la posibilidad de optener la prenómina
    """,
    'author': "Pablo Mercedes",
    'category': 'Localization/Payroll',
    'version': '12.0.0.0',
    'application': True,
    'installable': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'om_hr_payroll'],
    'images': ['static/description/icon.png'],

    # always loaded
    'data':
        [
            'security/ir.model.access.csv',
            'security/groups.xml',
            'report/om_hr_payroll_report.xml',
            'views/prepayroll_view.xml',
            'report/om_hr_payslip_view.xml',
            'wizards/prepayroll_wizard.xml',
        ]
}
