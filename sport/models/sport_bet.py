# -*- coding: utf-8 -*-

import itertools
from datetime import datetime
from operator import itemgetter, attrgetter
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class SportBet(models.Model):
    _name = "sport.bet"
    _description = "Bet"
    _rec_name = "partner_name"
    _order = 'bet_group, date'

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        stand_obj = self.pool.get('sport.bet.standing')
        if 'bet_group' in vals:
            for bet_brw in self.browse(cr, uid, ids):
                bet_id = bet_brw.id or False
                bet_group = bet_brw.bet_group.id or False
                stand_id = stand_obj.search(cr, uid, [('bet_id','=',bet_id),('bet_group','=',bet_group)], context=context)
                if stand_id:
                    stand_id = stand_id[0]
                    stand_brw = stand_obj.browse(cr, uid, stand_id)
                    stand_brw.write({'bet_group': vals['bet_group']})
                    stand_brw.bet_group.update_ranking()
                    bet_group and bet_brw.bet_group.update_ranking()
        return super(sport_bet, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        res = super(sport_bet, self).create(cr, uid, vals, context=context)
        if res:
            group_obj = self.pool.get('sport.bet.group')
            bet_brw = self.browse(cr, uid, res)
            standings = [(0,0,{ 'bet_group': bet_brw.bet_group.id,
                            bet_id': bet_brw.id,
                                    })]
            group_obj.write(cr, uid, bet_brw.bet_group.id, {'standing_ids': standings}, context=context)
            group_obj.update_ranking(cr, uid, bet_brw.bet_group.id, context=context)
        return res

    def _compute_category_ids(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            if record.partner_id:
                result[record.id] = [x.id for x in record.partner_id.category_id]
            else:
                result[record.id] = []

        return result

    _columns = {
    name = fields.Char('Name', size=64, required=True, help="This name must be unique to indentify the ticket"),
    partner_id = fields.Many2one('res.partner', 'Ticket Owner'),
    partner_name = fields.related('partner_id', 'name', type='char', size=64, relation='res.partner', string='Nombre'),
    partner_category_ids = fields.function(_compute_category_ids, type='many2many', relation="res.partner.category", string="Partner Category"),
    bet_lines = fields.One2many('sport.bet.line', 'bet_id', 'Bet by Matches'),
    bet_type = fields.Many2one('sport.bet.type', 'Bet Type'),
    bet_group = fields.Many2one('sport.bet.group', 'Bet Group'),
    date = fields.Date('Creation Date', required=True),
    }

class SportBetLine(models.Model):
    _name = "sport.bet.line"
    _description = "Bet Line"

    def onchange_match(self, cr, uid, ids, match_id):
        value = {}
        if match_id:
            match = self.pool.get('sport.match').browse(cr, uid, match_id)
            value.update({'home_team_id': match.home_team_id.id, 'visitor_team_id': match.visitor_team_id.id })
        return {'value': value}

    _columns = {
    name = fields.Char('Name', size=64, help="Ticket name"),
    bet_id = fields.Many2one('sport.bet', 'Parent'),
    tournament_id = fields.Many2one('sport.tournament', 'Tournament'),
    match_id = fields.Many2one('sport.match', 'Match'),
    home_team_id = fields.Many2one('sport.team', required=True),
    visitor_team_id = fields.Many2one('sport.team', required=True),
    home_score = fields.Integer('Home score', required=True),
    visitor_score = fields.Integer('Visitor score', required=True),


class SportBetType(models.Model):
    _name = "sport.bet.type"
    _description = "Bet type"
    _columns = {
    name = fields.Char('Name', size=64, required=True, help="Ticket name"),
    result = fields.Integer('Result points', required=True, help="Points for guess the result (win/tie) "),
    score = fields.Integer('Scoreboard points', required=True, help="Points for guess the scoreboard"),
    result_in_ko = fields.Integer('Result points in knockout', required=True, help="Result (win/tie) points in ko stages"),
    score_in_ko = fields.Integer('Scoreboard points in knockout', required=True, help="Scoreboard points in ko stages"),
    advance_16th = fields.Integer('Advance to 16th', required=True, help="Points for each team that advances to the 16"),
    advance_8th = fields.Integer('Advance to 8th', required=True, help="Points for each team that advances to the 8"),
    advance_quarter = fields.Integer('Advance to quarter-final', required=True, help="Points for each team that advances to the quarter final"),
    advance_semi = fields.Integer('Advance to semi-final', required=True, help="Points for each team that advances to the semifinal"),
    advance_third = fields.Integer('Advance to third place match', required=True, help="Points for each team that advances to third place match"),
    advance_final = fields.Integer('Advance to final', required=True, help="Points for each team that advances to the final"),
    winner_final = fields.Integer('Win the final', required=True, help="Points for guess the tournament champs"),


class SportBetGroup(models.Model):
    _name = "sport.bet.group"
    _description = "Bet Group"

    def _load_standings(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        standings = []
        for group_brw in self.browse(cr, uid, ids):
            if group_brw.standing_ids:
                raise osv.except_osv(_('Advertencia!'),_('Disculpe, ya no puede usar esta opcion'))
            bets = [bet_brw.id for bet_brw in group_brw.bet_ids]
            for bet in bets:
                standings.append((0,0,{ 'bet_group': group_brw.id,
                                    bet_id': bet,
                                }))
            standings and self.write(cr, uid, group_brw.id, {'standing_ids': standings}, context=None)
        return {}

    def update_ranking(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        stand_obj = self.pool.get('sport.bet.standing')
        brw = self.browse(cr, uid, ids)
        for b in brw:
            # order standing object by attrs: point
            newlist = sorted(b.standing_ids, key=attrgetter('points'), reverse=True)
            sequence = 1
            for std in newlist:
                stand_obj.write(cr, uid, std.id, {'sequence': sequence}, context=context)
                sequence +=1
        return {}

    def _compute_first_place(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for b in self.browse(cr, uid, ids, context=context):
            bet_ids = [std.bet_id.id for std in b.standing_ids if std.sequence == 1]
            result[b.id] = bet_ids and bet_ids[0] or False
        return result

    def _compute_second_place(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for b in self.browse(cr, uid, ids, context=context):
            bet_ids = [std.bet_id.id for std in b.standing_ids if std.sequence == 2]
            result[b.id] = bet_ids and bet_ids[0] or False
        return result

    def _compute_third_place(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for b in self.browse(cr, uid, ids, context=context):
            bet_ids = [std.bet_id.id for std in b.standing_ids if std.sequence == 3]
            result[b.id] = bet_ids and bet_ids[0] or False
        return result

    _columns = {
    name = fields.Char('Name', size=64, required=True, help="Group Name"),
    bet_ids = fields.One2many('sport.bet', 'bet_group', 'Bets'),
    standing_ids = fields.One2many('sport.bet.standing', 'bet_group', 'Standing'),
    user_id = fields.Many2one('res.users', 'User Owner'),
    first = fields.function(_compute_first_place, type='many2one', relation='sport.bet', string='1st place'),
    second = fields.function(_compute_second_place, type='many2one', relation='sport.bet', string='2nd place'),
    third = fields.function(_compute_third_place, type='many2one', relation='sport.bet', string='3rd place'),
    access = fields.selection([
            ('private', 'Privado'),
            ('public', 'Público'),
            ], 'Side',  ),


class SportBetStanding(models.Model):
    _name = "sport.bet.standing"
    _description = "Bet Standing"
    _order = "sequence"

    _stages = ['16th','8th','quarter','semi','third','final']

    def _compute_teams_advancing(self, cr, uid, ids, context=None):
        teams = dict(map(lambda x: (x, []), self._stages))
        clss_obj = self.pool.get('sport.round.classified')
        clss_ids = clss_obj.search(cr, uid, [], context=context)
        for clss_brw in clss_obj.browse(cr, uid, clss_ids, context=context):
            if not clss_brw.round_id.done:
                continue
            advance = clss_brw.round_id.advance
            if advance:
                next_stage = clss_brw.next_round_id.stage
                clss_brw.position <= advance and \
                clss_brw.team_id.id not in teams[next_stage] \
                and teams[next_stage].append(clss_brw.team_id.id)
        return teams

    def _calculate_points(self, cr, uid, ids, field, arg, context=None):
        res = {}
        type_obj = self.pool.get('sport.bet.type')
        clss_obj = self.pool.get('sport.round.classified')
        # fill dict with classified teams
        teams_advancing = self._compute_teams_advancing(cr, uid, ids, context=context)
        brw = self.browse(cr, uid, ids)
        for b in brw:
            type_brw = type_obj.browse(cr, uid, b.bet_id.bet_type.id, context)
            if b.bet_group.id:
                points = 0
                success = {}
                teams_by_stages = dict(map(lambda x: (x, []), self._stages))
                for line in b.bet_id.bet_lines:
                    match_brw = self.pool.get('sport.match').browse(cr, uid, line.match_id.id, context)
                    stage = match_brw and match_brw.round_id.stage
                    if match_brw.state == 'done' and \
                    match_brw.home_team_id.id == line.home_team_id.id \
                    and match_brw.visitor_team_id.id == line.visitor_team_id.id:
                        if match_brw.home_score == line.home_score and match_brw.visitor_score == line.visitor_score:
                            points += match_brw.knockout and type_brw.score_in_ko or type_brw.score
                        elif match_brw.diff > 0 and line.home_score > line.visitor_score:
                            points += match_brw.knockout and type_brw.result_in_ko or type_brw.result
                            points += stage=='final' and type_brw.winner_final or 0
                        elif match_brw.diff < 0 and line.home_score < line.visitor_score:
                            points += match_brw.knockout and type_brw.result_in_ko or type_brw.result
                            points += stage=='final' and type_brw.winner_final or 0
                        elif match_brw.diff == 0 and line.home_score == line.visitor_score:
                            points += match_brw.knockout and type_brw.result_in_ko or type_brw.result

                    # fill dict with teams predicted
                    if stage in teams_by_stages.keys():
                        if line.home_team_id.id not in teams_by_stages[stage]:
                            teams_by_stages[stage].append(line.home_team_id.id)
                        if line.visitor_team_id.id not in teams_by_stages[stage]:
                            teams_by_stages[stage].append(line.visitor_team_id.id)
                # increase points with teams predicted successfully
                for stage in self._stages:
                    teams_success = list( set(teams_advancing[stage]).intersection( set(teams_by_stages[stage]) ) )
                    points += len(teams_success) * eval('type_brw.advance_%s'%stage)
                res[b.id] = points
        return res

    def create(self, cr, uid, vals, context=None):
        if 'bet_id' in vals:
            bet_id = vals['bet_id']
            vals.update({'name': self.pool.get('sport.bet').browse(cr, uid, bet_id).name})
        else:
            raise osv.except_osv(_('Advertencia!'),_('Debe haber al menos una apuesta asociada'))
        return super(sport_bet_standing, self).create(cr, uid, vals, context=context)

    _columns = {
    name = fields.Char('Name', size=64, required=True),
    bet_id = fields.Many2one('sport.bet', 'Bet'),
    partner_id = fields.related('bet_id', 'partner_id', type='many2one', relation='res.partner', string='Nombre'),
    bet_group = fields.Many2one('sport.bet.group', 'Group'),
    points = fields.function(_calculate_points, type='integer', string='Bet points'),
    sequence = fields.Integer('Rank'),
    }
    _defaults = {
    sequence': 1,
    }
