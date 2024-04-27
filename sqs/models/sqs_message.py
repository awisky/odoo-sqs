from odoo import models, fields, api
from odoo.exceptions import UserError


class SQSMessage(models.Model):
    _name = 'sqs.message'
    _description = 'SQS Message'
    _rec_name = 'message_id'

    message_body = fields.Text(
        string='Message Body',
        required=True,
        help="The content of the message retrieved from SQS")
    message_id = fields.Char(string='Message ID',
                             required=True,
                             help="The ID of the message from SQS")
    queue_id = fields.Many2one(
        'sqs.queue',
        string='Queue',
        required=True,
        help="The SQS queue from which the message was retrieved")
    state = fields.Selection([('draft', 'Draft'), ('processing', 'Processing'),
                              ('done', 'Done'), ('error', 'Error')],
                             string='state',
                             default='draft',
                             required=True,
                             help="The processing state of the message")

    def process_message(self):
        """ Process the SQS message according to your business logic """
        self.ensure_one()
        try:
            # processing logic, replace with actual processing code
            self.state = 'done'
        except Exception as e:
            self.state = 'error'
            self.error_description = str(e)
            raise UserError(_('Error processing the message: %s') % e)
