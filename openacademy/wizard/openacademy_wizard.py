from openerp import api, fields, models

class Wizard(models.TransientModel):
    _name = 'openacademy.wizard'


    def _default_session(self):
        session_obj = self.env['openacademy.session']
        return session_obj.browse(self._context.get('active_ids'))

    session_wz_ids = fields.Many2many('openacademy.session',
        string="Session", required=True, default=_default_session)
    attendee_wz_ids = fields.Many2many('res.partner', string="Attendees")

    @api.multi
    def subscribe(self):
        for session_wz_id in self.session_wz_ids:
            session_wz_id.attendee_ids |= self.attendee_wz_ids
            # previous line is equal to: session_obj.write(
            # session_wz_id,{'attendee_ids':[(6,0,self.attendee_wz_ids)]} )
        return {}

