# © 2024 Mountrix (<https://mountrix.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import boto3
import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class SQSQueue(models.Model):
    _name = 'sqs.queue'
    _description = 'SQS Queue Management'

    name = fields.Char(string='Queue Name', required=True)
    connector_id = fields.Many2one('sqs.connector',
                                   string='Connector',
                                   required=True)
    queue_url = fields.Char(string='Queue URL', required=True)

    @api.model
    def receive_message(self):
        """
        Receives messages from the specified SQS queue.
        """
        client = self.connector_id.get_sqs_client()
        response = client.receive_message(QueueUrl=self.queue_url,
                                          MaxNumberOfMessages=1,
                                          WaitTimeSeconds=20)
        return response.get('Messages', [])

    @api.model
    def delete_message(self, receipt_handle):
        """
        Deletes a message from the SQS queue using the receipt handle.
        """
        client = self.connector_id.get_sqs_client()
        client.delete_message(QueueUrl=self.queue_url,
                              ReceiptHandle=receipt_handle)

    def pull_from_sqs(self):
        """
        Pulls messages from SQS, deserializes them, and store it in Odoo.
        """
        message_obj = self.env['sqs.message']
        count = 0
        for sqs_queue in self:

            client = sqs_queue.connector_id.get_sqs_client()

            messages = client.receive_message(
                QueueUrl=sqs_queue.queue_url,
                MaxNumberOfMessages=10,  # Adjust as necessary
                WaitTimeSeconds=20,  # Long polling
                MessageAttributeNames=['All'])

            for message in messages.get('Messages', []):
                try:
                    message_body = json.loads(message['Body'])
                    msg = message_obj.create({
                        'message_id': message['MessageId'],
                        'message_body': message['Body'],
                        'queue_id': sqs_queue.id,
                        'state': 'draft'
                    })
                    client.delete_message(QueueUrl=sqs_queue.queue_url,
                                          ReceiptHandle=message['ReceiptHandle'])
                    _logger.info('Message created from SQS message: %s',
                                 msg.message_id)
                    count += 1
                except Exception as e:
                    _logger.error('Failed to store from SQS message: %s',
                                  str(e))
                    continue

        return {
            'success': f'count messaged pulled from SQS.'
        }
