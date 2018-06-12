# -*- coding: utf-8 -*-

from odoo import api, fields, models

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None


class SportBetImporter(models.TransientModel):
    _name = 'sport.bet.importer'

    name = fields.Char()
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)")
    bet_group_id = fields.Many2one('sport.bet.group', 'Group')
    tournament_id = fields.Many2one('sport.tournament', 'Tournament')

    @api.multi
    def action_import(self):
        self.ensure_one()
        return True
