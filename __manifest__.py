{
    'name': 'Approval system',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Manage purchase approvals',
    'description': """
        This module adds an approval workflow for purchase orders.
    """,
    'sequence': -300,
    'author': 'Jafar',
    'website': 'https://www.example.com',
    'depends': ['base','stock','purchase'],
    'data': [
        'security/ir.model.access.csv',
        'view/approval_system.xml',
        'view/purchase_submit_button.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}