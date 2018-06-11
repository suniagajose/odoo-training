# -*- coding: utf-8 -*-
from operator import attrgetter
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _

STAGES = ['16th','8th','quarter','semi','third','final']


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
    bet_rule_id = fields.Many2one('sport.bet.rule', 'Rule')
    bet_group_id = fields.Many2one('sport.bet.group', 'Group')
    date = fields.Date('Creation Date', required=True)


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
    tournament_id = fields.Many2one('sport.tournament', 'Tournament')
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
    user_id = fields.Many2one('res.users', 'User Owner')
    first = fields.Many2one(compute='_compute_first', relation='sport.bet', string='1st place')
    second = fields.Many2one(compute='_compute_second', relation='sport.bet', string='2nd place')
    third = fields.Many2one(compute='_compute_third', relation='sport.bet', string='3rd place')
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
            rule = standing.bet_id.bet_rule_id
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
    partner_id = fields.Many2one(related='bet_id.partner_id', relation='res.partner', store=True, string='Contacto')
    bet_group_id = fields.Many2one('sport.bet.group', 'Group')
    points = fields.Integer(compute='_compute_points', string='Bet points', store='True')
    sequence = fields.Integer('Rank', default=1)
