# -*- coding: utf-8 -*-

from operator import attrgetter
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _

import base64

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

STAGES = ['16th','8th','quarter','semi','third','final']

GROUP4MATCH = {
    'A': [1, 2, 17, 18, 33, 34],
    'B': [3, 4, 19, 20, 35, 36],
    'C': [5, 6, 21, 22, 37, 38],
    'D': [7, 8, 23, 24, 39, 40],
    'E': [9, 10, 25, 26, 41, 42],
    'F': [11, 12, 27, 28, 43, 44],
    'G': [13, 14, 29, 30, 45, 46],
    'H': [15, 16, 31, 32, 47, 48],
    'PO': [49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64],
}

COORD4MATCH = {
    'home_team_id': [(8, 2), (10, 2), (12, 2), (14, 2), (16, 2), (18, 2), (2, 4), (4, 4), (6, 4), (8, 4), (10, 4), (12, 4), (14, 4), (16, 4), (19, 4), (21, 4), (23, 4), (25, 4), (28, 4), (30, 4), (33, 4), (36, 4)],
    'visitor_team_id': [(8, 11), (10, 11), (12, 11), (14, 11), (16, 11), (18, 11), (2, 15), (4, 15), (6, 15), (8, 15), (10, 15), (12, 15), (14, 15), (16, 15), (19, 15), (21, 15), (23, 15), (25, 15), (28, 15), (30, 15), (33, 15), (36, 15)],
    'home_score': [(8, 6), (10, 6), (12, 6), (14, 6), (16, 6), (18, 6), (2, 8), (4, 8), (6, 8), (8, 8), (10, 8), (12, 8), (14, 8), (16, 8), (19, 8), (21, 8), (23, 8), (25, 8), (28, 8), (30, 8), (33, 8), (36, 8)],
    'visitor_score': [(8, 8), (10, 8), (12, 8), (14, 8), (16, 8), (18, 8), (2, 12), (4, 12), (6, 12), (8, 12), (10, 12), (12, 12), (14, 12), (16, 12), (19, 12), (21, 12), (23, 12), (25, 12), (28, 12), (30, 12), (33, 12), (36, 12)],
}

class SportBet(models.Model):
    _name = "sport.bet"
    _description = "Bet"
    _rec_name = "partner_name"
    _order = 'bet_group_id, date'

    @api.multi
    def write(self, vals):
        bet_standing = self.env['sport.bet.standing']
        if 'bet_group_id' not in vals:
            return super(SportBet, self).write(vals)
        # update previous group before change it
        for bet in self:
            bet_standing_id = bet_standing.search(
                [('bet_id', '=', bet.id), ('bet_group_id', '=', bet.bet_group_id)])
            if bet_standing_id:
                bet_standing_id.write({'bet_group_id': vals['bet_group_id']})
                bet_standing_id.bet_group_id.update_ranking()
                bet.bet_group_id.update_ranking()
        return super(SportBet, self).write(vals)

    @api.model
    def create(self, vals):
        bet = super(SportBet, self).create(vals)
        bet_group_id = self.env['sport.bet.group']
        standings = [(0,0, {
            'bet_group_id': bet.bet_group_id.id,
            'bet_id': bet.id,
        })]
        bet_group_id = bet.bet_group_id
        bet_group_id.write({'standing_ids': standings})
        bet_group_id.update_ranking()
        return bet

    name = fields.Char('Name', size=64, required=True, help="This name must be unique to indentify the ticket")
    partner_id = fields.Many2one('res.partner', 'Ticket Owner')
    partner_name = fields.Char(related='partner_id.name', string='Nombre', store=True)
    bet_lines = fields.One2many('sport.bet.line', 'bet_id', 'Matches')
    bet_group_id = fields.Many2one('sport.bet.group', 'Group')
    date = fields.Date('Creation Date', required=True)
    ir_attachment_id = fields.Many2one('ir.attachment', string='Related attachment', required=True, ondelete='cascade')

    @api.model
    def get_team_id_by_name(self, name, sport=None):
        if not sport:
            sport = self.env.ref('sport.sport_sport_football')
        team_id = self.env['sport.team'].search([
            ('name', '=', name.upper()),
            ('sport_id', '=', sport.id)], limit=1)
        return team_id and team_id.id or False

    @api.multi
    def action_import(self):
        self.ensure_one()
        mimetype = 'spreadsheetml.sheet'
        content = base64.b64decode(self.ir_attachment_id.datas)
        book = xlrd.open_workbook(file_contents=content)
        if self.bet_lines:
            return True
        if (not self.ir_attachment_id or
                mimetype not in self.ir_attachment_id.mimetype):
            raise ValidationError(_('Documento Invalido'))
        for i in range(1, 65):
            duplex = [(m, GROUP4MATCH[m].index(i)) for m in GROUP4MATCH if i in GROUP4MATCH[m]]
            letter = duplex[0][0]
            indexx = (duplex[0][1] + 6) if letter == 'PO' else duplex[0][1]
            sheet = book.sheet_by_name(letter)
            line_vals = {
                n: 'team' in n and self.get_team_id_by_name(
                    sheet.cell_value(
                        COORD4MATCH[n][indexx][0],
                        COORD4MATCH[n][indexx][1])) or
                    sheet.cell_value(
                        COORD4MATCH[n][indexx][0],
                        COORD4MATCH[n][indexx][1]) for n in COORD4MATCH}
            line_vals.update({
                'bet_id': self.id,
                'match_id': self.env.ref('sport.russia2018_match_%d' % i).id
            })
            self.env['sport.bet.line'].create(line_vals)
        return True

    @api.multi
    def action_reset(self):
        self.ensure_one()
        self.bet_lines.unlink()
        return True


class SportBetLine(models.Model):
    _name = "sport.bet.line"
    _description = "Bet Line"

    @api.onchange('match_id')
    def onchange_match_id(self):
        if self.match_id:
            self.home_team_id = self.match.home_team_id.id,
            self.visitor_team_id = self.match.visitor_team_id.id

    name = fields.Char('Name', size=64, help="Ticket name")
    bet_id = fields.Many2one('sport.bet', 'Parent')
    tournament_id = fields.Many2one(related='bet_id.bet_group_id.tournament_id', relation='sport.tournament', store=True, readonly='True', string='Tournament')
    match_id = fields.Many2one('sport.match', 'Match')
    home_team_id = fields.Many2one('sport.team', required=True)
    visitor_team_id = fields.Many2one('sport.team', required=True)
    home_score = fields.Integer('Home score', required=True)
    visitor_score = fields.Integer('Visitor score', required=True)


class SportBetRule(models.Model):
    _name = "sport.bet.rule"
    _description = "Bet Rule"

    name = fields.Char('Name', size=64, required=True, help="Ticket name")
    result = fields.Integer('Result points', required=True, help="Points for guess the result (win/tie) ")
    score = fields.Integer('Scoreboard points', required=True, help="Points for guess the scoreboard")
    result_in_ko = fields.Integer('Result points in knockout', required=True, help="Result (win/tie) points in ko stages")
    score_in_ko = fields.Integer('Scoreboard points in knockout', required=True, help="Scoreboard points in ko stages")
    advance_16th = fields.Integer('Advance to 16th', required=True, help="Points for each team that advances to the 16")
    advance_8th = fields.Integer('Advance to 8th', required=True, help="Points for each team that advances to the 8")
    advance_quarter = fields.Integer('Advance to quarter-final', required=True, help="Points for each team that advances to the quarter final")
    advance_semi = fields.Integer('Advance to semi-final', required=True, help="Points for each team that advances to the semifinal")
    advance_third = fields.Integer('Advance to third place match', required=True, help="Points for each team that advances to third place match")
    advance_final = fields.Integer('Advance to final', required=True, help="Points for each team that advances to the final")
    winner_final = fields.Integer('Win the final', required=True, help="Points for guess the tournament champs")


class SportBetGroup(models.Model):
    _name = "sport.bet.group"
    _description = "Bet Group"

    @api.multi
    def load_standings(self):
        self.ensure_one()
        standings = []
        if self.standing_ids:
            raise ValidationError(
                _('Disculpe, ya no puede usar esta opcion'))
        for bet in self.bet_ids:
            standings.append((0,0, {
                'bet_group_id': self.id,
                'bet_id': bet.id,
            }))
        return self.write({'standing_ids': standings})

    @api.multi
    def update_ranking(self):
        self.ensure_one()
        # order standing object by attrs: point
        newlist = sorted(self.standing_ids, key=attrgetter('points'), reverse=True)
        sequence = 1
        for standing in newlist:
            standing.write({'sequence': sequence})
            sequence +=1

    @api.multi
    def _compute_first(self):
        for group in self:
            standing_id = group.standing_ids.filtered(lambda x: x.sequence == 1)
            group.first = standing_id and standing_id.bet_id.id or False

    @api.multi
    def _compute_second(self):
        for group in self:
            standing_id = group.standing_ids.filtered(lambda x: x.sequence == 2)
            group.second = standing_id and standing_id.bet_id.id or False

    @api.multi
    def _compute_third(self):
        for group in self:
            standing_id = group.standing_ids.filtered(lambda x: x.sequence == 3)
            group.third = standing_id and standing_id.bet_id.id or False

    name = fields.Char('Name', size=64, required=True, help="Group Name")
    bet_ids = fields.One2many('sport.bet', 'bet_group_id', 'Bets')
    standing_ids = fields.One2many('sport.bet.standing', 'bet_group_id', 'Standing')
    bet_rule_id = fields.Many2one('sport.bet.rule', 'Rule')
    tournament_id = fields.Many2one('sport.tournament', string='Tournament')
    user_id = fields.Many2one('res.users', 'User Owner')
    first = fields.Many2one('sport.bet', compute='_compute_first', string='1st place')
    second = fields.Many2one('sport.bet', compute='_compute_second', string='2nd place')
    third = fields.Many2one('sport.bet', compute='_compute_third', string='3rd place')
    access = fields.Selection([
        ('private', 'Privado'),
        ('public', 'Público'),
    ], 'Side', default='public')


class SportBetStanding(models.Model):
    _name = "sport.bet.standing"
    _description = "Bet Standing"
    _order = "sequence"

    @api.model
    def _get_classified_teams(self):
        teams = dict(map(lambda x: (x, []), STAGES))
        round_classified = self.env['sport.round.classified']
        # TODO: must be filtered by tournament
        for classified in round_classified.search([]):
            if not classified.round_id.done:
                continue
            advance = classified.round_id.advance
            if advance:
                next_stage = classified.next_round_id.stage
                team_id = classified.team_id.id
                classified.position <= advance and (
                    team_id not in teams[next_stage] and
                    teams[next_stage].append(team_id))
        return teams

    @api.multi
    @api.depends('bet_id.bet_lines.match_id.state')
    def _compute_points(self):
        # fill dict with classified teams
        classified_teams = self._get_classified_teams()
        for standing in self.filtered(lambda x: x.bet_group_id != False):
            points = 0
            rule = standing.bet_group_id.bet_rule_id
            teams = dict(map(lambda x: (x, []), STAGES))

            for line in standing.bet_id.bet_lines:
                match = line.match_id
                stage = match and match.round_id.stage

                # fill dict with teams predicted
                if stage in teams.keys():
                    if line.home_team_id.id not in teams[stage]:
                        teams[stage].append(line.home_team_id.id)
                    if line.visitor_team_id.id not in teams[stage]:
                        teams[stage].append(line.visitor_team_id.id)

                # avoid iteration when not apply points calculation
                if (match.state != 'done' or
                        match.home_team_id != line.home_team_id or
                        match.visitor_team_id != line.visitor_team_id):
                    continue

                # check cases that apply points calculation
                if match.home_score == line.home_score and match.visitor_score == line.visitor_score:
                    points += match.knockout and rule.score_in_ko or rule.score
                elif match.diff > 0 and line.home_score > line.visitor_score:
                    points += match.knockout and rule.result_in_ko or rule.result
                    points += stage == 'final' and rule.winner_final or 0
                elif match.diff < 0 and line.home_score < line.visitor_score:
                    points += match.knockout and rule.result_in_ko or rule.result
                    points += stage == 'final' and rule.winner_final or 0
                elif match.diff == 0 and line.home_score == line.visitor_score:
                    points += match.knockout and rule.result_in_ko or rule.result

            # increase points with teams predicted successfully
            for stage in STAGES:
                teams_success = list(set(classified_teams[stage]).intersection(set(teams[stage]) ) )
                points += len(teams_success) * eval('rule.advance_%s' % stage)
            standing.points = points

    @api.model
    def create(self, vals):
        if 'bet_id' in vals:
            bet_id = vals['bet_id']
            vals.update({'name': self.env['sport.bet'].browse(bet_id).name})
        else:
            raise ValidationError(
                _('Debe haber al menos una apuesta asociada'))
        return super(SportBetStanding, self).create(vals)

    name = fields.Char('Nombre', size=64, required=True)
    bet_id = fields.Many2one('sport.bet', 'Bet')
    partner_id = fields.Many2one(related='bet_id.partner_id', relation='res.partner', store=True, readonly=True, string='Contacto')
    bet_group_id = fields.Many2one(related='bet_id.bet_group_id', relation='sport.bet.group', store=True, readonly=True, string='Group')
    points = fields.Integer(compute='_compute_points', string='Bet points', store='True')
    sequence = fields.Integer('Rank', default=1)
