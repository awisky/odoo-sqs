# © 2024 Mountrix (<https://mountrix.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "Mountrix SQS",
    'summary': """
        Mountrix SQS
    """,
    'description': """
        Mountrix SQS Connector
    """,
    'author': "Agustin Wisky <agustin.wisky@mountrix.com>",
    'website': "https://mountrix.com",
    'category': 'Generic Modules',
    'version': '1.0',
    'license': 'AGPL-3',
    'depends': [],
    "external_dependencies": {"python": ["boto3"]},
    'data': [
        'security/ir.model.access.csv',
        'views/sqs_connector_views.xml',
        'views/sqs_queue_views.xml',
        'views/sqs_message_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
}
