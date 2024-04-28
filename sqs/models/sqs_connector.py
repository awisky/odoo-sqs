# © 2024 Mountrix (<https://mountrix.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import boto3


class SQSConnector(models.Model):
    _name = 'sqs.connector'
    _description = 'Connector for AWS SQS'

    name = fields.Char(
        string='Name',
        help='Descriptive name for the connector',
        required=True,
    )
    access_key_id = fields.Char(string='AWS Access Key ID', required=True)
    secret_access_key = fields.Char(string='AWS Secret Access Key', required=True)
    region_name = fields.Char(string='AWS Region', required=True)

    def get_sqs_client(self):
        """
        Initializes and returns an SQS client using the stored credentials.
        """
        return boto3.client('sqs',
                            aws_access_key_id=self.access_key_id,
                            aws_secret_access_key=self.secret_access_key,
                            region_name=self.region_name)

    def test_connection(self):
        """
        Tests the connection to AWS SQS by attempting to list SQS queues,
        and creates sqs.queue records for each found queue.
        """
        try:
            client = self.get_sqs_client()
            response = client.list_queues()
            queues = response.get('QueueUrls', [])
            existing_queues = self.env['sqs.queue'].search(
                []
            ).mapped('queue_url')
            new_queues = []

            for queue_url in queues:
                if queue_url not in existing_queues:
                    new_queue = self.env['sqs.queue'].create({
                        'name':
                        queue_url.split('/')
                        [-1],  # Assuming the name is the last segment of the URL
                        'queue_url':
                        queue_url,
                        'connector_id':
                        self.id
                    })
                    new_queues.append(new_queue.name)

            message = _(
                'Connection successful! Found %s queues. ' % (len(queues))
            )
            if new_queues:
                message += _(
                    'Created new queues: %s' % (', '.join(new_queues))
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('SQS connection test successful!'),
                    'type': 'success',
                    'message': message,
                    'sticky': False,
                },
            }

        except Exception as e:
            raise UserError(_('Failed to connect to AWS SQS: %s' % e))
