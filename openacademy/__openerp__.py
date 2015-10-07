# -*- coding: utf-8 -*-
{
    'name': "Open Academy",

    'summary': """Manage trainings""",

    'description': """
        Open Academy module for managing trainings:
        - training courses
        - training sessions
        - attendees registration
    """,

    'author': "vauxoo",
    'website': "http://www.vauxoo.com",

    # Categories can be used to filter modules in modules listing
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'board'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'view/openacademy_course_view.xml',
        'view/openacademy_session_view.xml',
        'view/partner_view.xml',
        'view/partner_category_view.xml',
        'data/partner_category_data.xml',
        'workflow/openacademy_session_workflow.xml',
        'wizard/openacademy_wizard_view.xml',
        'report/openacademy_session_report.xml',
        'view/openacademy_session_board.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/openacademy_course_demo.xml',
    ],
    'installable': True,
}
