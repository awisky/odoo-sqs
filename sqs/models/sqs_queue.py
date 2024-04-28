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
    connector_id = fields.Many2one(
        'sqs.connector',
        string='Connector',
        required=True
    )
    queue_url = fields.Char(string='Queue URL', required=True)
    message_body = fields.Text(string='Message Body')
    wait_time_seconds = fields.Integer()
    max_number_of_messages = fields.Integer()
    message_count = fields.Integer(compute='_compute_message_count')

    def _compute_message_count(self):
        for queue in self:
            queue.message_count = self.env['sqs.message'].search_count([('queue_id', '=', queue.id)])

    @api.model
    def receive_message(self):
        """
        Receives messages from the specified SQS queue.
        """
        client = self.connector_id.get_sqs_client()
        response = client.receive_message(QueueUrl=self.queue_url,
                                          MaxNumberOfMessages=10,
                                          WaitTimeSeconds=20)
        return response.get('Messages', [])
    
    def action_send_message(self):
        """
        Sends a message to the specified SQS queue.
        """
        try:
            self.ensure_one()
            if not self.message_body:
                raise UserError(_('Message body is required to send a message.'))
            message_body = self.message_body
            client = self.connector_id.get_sqs_client()
            client.send_message(QueueUrl=self.queue_url, MessageBody=message_body)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Send Message successful!'),
                    'type': 'success',
                    'message': _('Message sent successfully.'),
                    'sticky': False,
                },
            }
        except Exception as e:
            raise UserError(_('Error sending message: %s') % e)

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

        The creation of messages in Odoo will check first if they don't
        already exist. There is a know issue in boto3 lib that even when
        using `MaxNumberOfMessages=10`, it returns only one message
        at a time, specially when the queue has low number of messages
        (details of the issue here: https://github.com/boto/boto3/issues/324)

        On this method messages are kept in the SQS in case other service needs
        to read it. We are handling the deletion of the messages from the queue
        in the `process_message` method of the `sqs.message` model.
        """
        message_obj = self.env['sqs.message']
        count = 0
        for sqs_queue in self:

            client = sqs_queue.connector_id.get_sqs_client()

            messages = client.receive_message(
                QueueUrl=sqs_queue.queue_url,
                MaxNumberOfMessages=sqs_queue.max_number_of_messages or 10,  # Adjust as necessary
                WaitTimeSeconds=self.wait_time_seconds or 20,  # Long polling
                MessageAttributeNames=['All'])
            
            existing_message_ids = message_obj.search([
                ('queue_id', '=', sqs_queue.id),
            ]).mapped('message_id')

            for message in messages.get('Messages', []):
                try:
                    if message['MessageId'] not in existing_message_ids:
                        msg = message_obj.create({
                            'message_id': message['MessageId'],
                            'receipt_handle': message['ReceiptHandle'],
                            'message_body': message['Body'],
                            'queue_id': sqs_queue.id,
                            'state': 'draft'
                        })
                        _logger.info(
                            'Message created from SQS message: %s',
                            msg.message_id
                        )
                        count += 1
                except Exception as e:
                    _logger.error(
                        'Failed to store from SQS message: %s',
                        str(e)
                    )
                    continue
        return {
            'success': f'{count} messages pulled from SQS.'
        }
    
    def action_open_messages(self):
        action = self.env['ir.actions.act_window']._for_xml_id('sqs.action_sqs_message')
        action['domain'] = [('queue_id', 'in', self.ids)]
        return action
