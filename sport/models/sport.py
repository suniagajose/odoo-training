# -*- coding: utf-8 -*-

import itertools
from datetime import datetime
from operator import itemgetter, attrgetter
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class SportTournament(models.Model):
    _name = "sport.tournament"
    _description = "Tournament"

    name = fields.Char('Name', size=64, required=True)
    sport_id = fields.Many2one('sport.sport', 'Sport')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    round_ids = fields.One2many('sport.round', 'tournament_id', 'Rounds/Divisions')
    match_ids = fields.One2many('sport.match', 'tournament_id', 'Matches')
    standing_ids = fields.One2many('sport.standing', 'round_id', 'Standing')
    date_start = fields.Date('Start Date', required=True)
    date_stop = fields.Date('End Date', required=True)


class SportRound(models.Model):
    _name = "sport.round"
    _description = "Round"

    @api.multi
    def _compute_matches(self):
        for round in self:
            round.matches = len(round.match_ids)

    @api.multi
    def _pairing_teams(self, matchup=None):
        self.ensure_one()
        if not matchup:
            matchup = self.matchup
        teams = [team.id for team in self.team_ids]
        l = []
        if matchup > 0:
            if matchup % 2 == 0:
                l = [pair for pair in itertools.permutations(teams, 2)]
                matchup = matchup - 2
            else:
                l = [pair for pair in itertools.combinations(teams, 2)]
                matchup = matchup - 1
            l = matchup > 0 and l + self._pairing_teams(matchup=matchup) or l
        return l

    @api.multi
    def _load_matches(self):
        self.ensure_one()
        matches = []
        seq = 1
        if self.match_ids:
            return False
        for pair in self._pairing_teams():
            home = self.env['sport.team'].browse(pair[0])
            visitor = self.env['sport.team'].browse(pair[1])
            matches += [(0, 0, {
                'sequence': seq,
                'home_team_id': home.id,
                'visitor_team_id': visitor.id,
                'state': 'scheduled',
                'tournament_id': self.tournament_id.id
            })]
            seq += 1
        return self.write({'match_ids': matches})

    @api.multi
    def _load_standings(self):
        self.ensure_one()
        standing_ids = []
        # get teams in round
        round_team_ids = self.team_ids.ids
        # get teams in standing
        standing_team_ids = self.standing_ids.mapped('team_id').ids
        # both lists are subtracted to validate integrity
        diff = list(set(standing_team_ids) - set(round_team_ids))
        # build standing if a team is missing or not standing in round
        if len(diff) or len(standing_team_ids) == 0:
            # any team to be unlinked
            self.standing_ids.filtered(lambda x: x.team_id.id in diff).unlink()
            team_ids = self.team_ids.filtered(
                lambda x: x.id not in standing_team_ids)
            for team in team_ids:
                standing_ids += [(0, 0, {
                    'tournament_id': self.tournament_id.id,
                    'round_id': self.id,
                    'team_id': team.id,
                })]
        return self.write({'standing_ids': standing_ids})

    @api.multi
    def _update_standings(self):
        self.ensure_one()
        # order standing object by attrs: point, diff desc
        newlist = sorted(self.standing_ids, key=attrgetter('points', 'diff', 'favour'), reverse=True)
        sequence = 1
        for standing in newlist:
            standing.write({'sequence': sequence})
            sequence +=1

#     def onchange_teams(self, cr, uid, ids, teams, members):
#         res = {}
#         total = teams and len(teams[0])==3 and len(teams[0][2]) or 0
#         if total > members:
#             warning = { 'title': _('Advertencia !'),
#                     message': _('La cantidad de equipos seleccionados no puede exceder el numero de equipos establecido para el grupo')
#                       }
#             res.update({'warning': warning})
#         return res

#     def write(self, cr, uid, ids, vals, context=None):
#         if isinstance(ids, (int, long)):
#             ids = [ids]
#         for brw in self.browse(cr, uid, ids):
#             total = vals.get('team_ids',False) and \
#                     vals['team_ids'] and \
#                     len(vals['team_ids'][0])==3 and \
#                     len(vals['team_ids'][0][2]) or 0
#             members = brw.members
#             if total > members:
#                 raise osv.except_osv(_('Advertencia!'),_('La cantidad de equipos seleccionados no puede exceder el numero de equipos establecido para el grupo'))
#         return super(sport_round, self).write(cr, uid, ids, vals, context=context)

#     def create(self, cr, uid, vals, context=None):
#         total = vals.get('team_ids',False) and \
#                 vals['team_ids'] and \
#                 len(vals['team_ids'][0])==3 and \
#                 len(vals['team_ids'][0][2]) or 0
#         if 'members' in vals:
#             members = vals['members']
#             if total > members:
#                 raise osv.except_osv(_('Advertencia!'),_('La cantidad de equipos seleccionados no puede exceder el numero de equipos establecido para el grupo'))
#         return super(sport_round, self).create(cr, uid, vals, context=context)

    name = fields.Char('Name', size=64, required=True)
    tournament_id = fields.Many2one('sport.tournament', 'Tournament')
    team_ids = fields.many2many('sport.team', 'sport_round_team_rel', 'round_id', 'team_id', 'Teams by Round')
    members = fields.Integer('Maximun teams', required=True)
    matchup = fields.Integer('Matchup games', required=True, help="Number of games each team faces")
    match_ids = fields.One2many('sport.match', 'round_id', 'Matches')
    matches = fields.Integer(compute='_compute_matches', string='Total games')
    standing_ids = fields.One2many('sport.standing', 'round_id', 'Standing')
    advance = fields.Integer('advance', required=True)
    classified_ids = fields.One2many('sport.round.classified', 'round_id', 'Runner Up')
    stage = fields.Selection([
        ('group', 'Grupo'),
        ('16th ', 'Dieciseisavos'),
        ('8th', 'Octavos'),
        ('quarter', 'Cuartos'),
        ('semi', 'Semifinal'),
        ('third', 'Tercero'),
        ('final', 'Final'),
    ], 'Stage'),
    done = fields.boolean('Finished round'),


class SportRoundClassified(models.Model):
    _name = "sport.round.classified"
    _description = "Runner Up"

    @api.multi
    def _compute_team_id(self):
        for record in self:
            pos = record.position
            team_id = [std.team_id.id for std in record.round_id.standing_ids if std.sequence == pos]
            record.team_id = team_id and team_id[0] or False
        return result

    # def create(self, cr, uid, vals, context=None):
    #     if 'round_id' in vals and 'position' in vals:
    #         round_name = self.pool.get('sport.round').browse(cr, uid, vals['round_id']).name
    #         vals.update({'name': str(vals['position']) + u'° '+ round_name })
    #     res = super(sport_round_classified, self).create(cr, uid, vals, context=context)
    #     return res

    name = fields.Char('Name', size=64)
    round_id = fields.Many2one('sport.round', 'Round')
    next_round_id = fields.Many2one('sport.round', 'Next Round')
    team_id = fields.Many2one('sport.team', compute='_compute_team_id', string='RunnerUp Team')
    side = fields.selection([
        ('home', 'Home'),
        ('visitor', 'Visitor'),
    ], 'Side')
    position = fields.Integer('Team position')


class SportStanding(models.Model):
    _name = "sport.standing"
    _description = "Standing"
    _order = "sequence"

    @api.multi
    def _compute_favour(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            favour = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and
                        standing.team_id.id == match.home_team_id.id):
                    favour += match.home_score
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    favour += match.visitor_score
            standing.favour = favour

    @api.multi
    def _compute_against(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            against = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and
                        standing.team_id.id == match.home_team_id.id):
                    against += m.visitor_score
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    against += m.home_score
            standing.against = against

    @api.multi
    def _compute_points(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            points = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and
                        standing.team_id.id == match.home_team_id.id):
                    points += m.diff > 0 and 3 or m.diff == 0 and 1 or 0
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    points += m.diff < 0 and 3 or m.diff == 0 and 1 or 0
            standing.points = points

    def _compute_played(self):
        brw = self.browse(cr, uid, ids)
        res = {}
        for b in brw:
            teams = {}
            if b.round_id:
                if b.team_id.id not in teams:
                    teams[b.team_id.id] = 0
                for m in b.round_id.match_ids:
                    if m.state in ['started','done'] and \
                       b.team_id.id == m.home_team_id.id:
                        teams[b.team_id.id] += 1
                    elif m.state in ['started','done'] and \
                       b.team_id.id == m.visitor_team_id.id:
                        teams[b.team_id.id] += 1
            elif b.tournament_id:
                pass
            res[b.id] = b.team_id.id in teams and teams[b.team_id.id] or 0
        return res

    def _compute_diff(self):
        brw = self.browse(cr, uid, ids)
        res = {}
        for b in brw:
            res[b.id] = b.favour - b.against
        return res

    def create(self, cr, uid, vals, context=None):
        if 'team_id' in vals:
            team_id = vals['team_id']
            vals.update({'name': self.pool.get('sport.team').browse(cr, uid, team_id).name})
        else:
            raise osv.except_osv(_('Advertencia!'),_('Debe seleccionar un equipo'))
        return super(sport_standing, self).create(cr, uid, vals, context=context)

    name = fields.Char('Name', size=64, required=True)
    tournament_id = fields.Many2one('sport.tournament', 'Tournament')
    round_id = fields.Many2one('sport.round', 'Round')
    team_id = fields.Many2one('sport.team', 'Team')
    favour = fields.Integer(compute='_compute_favour', string='Score Favour')
    against = fields.Integer(compute='_compute_against', string='Score Against')
    points = fields.Integer(compute='_compute_points', string='Team Points')
    played = fields.Integer(compute='_compute_played', string='Games Played')
    sequence = fields.Integer('Team Position', default=1)
    diff = fields.Integer(compute='_compute_diff', string='Score Difference')


class SportSport(models.Model):
    _name = "sport.sport"
    _description = "Sport"

    name = fields.Char('Name', size=64, required=True)


class SportTeam(models.Model):
    _name = "sport.team"
    _description = "Team"

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=3, required=True)
    sport_id = fields.Many2one('sport.sport', 'Sport')
    country_id = fields.Many2one('res.country', 'Country')


class SportMatch(models.Model):
    _name = "sport.match"
    _description = "Match"
    _order = 'tournament_id, sequence'

    def name_get(self, cr, user, ids, context=None):
        res = super(sport_match,self).name_get(cr, user, ids, context=context)
        result = []
        lang_code = self.pool.get('res.users').browse(cr, user, user).lang
        name_pre = lang_code[:2] == 'es' and 'Juego' or 'Game'
        for m in res:
            match = self.browse(cr, user, m[0], context=context)
            name = '%s %s - %s'%(name_pre,match.sequence,match.round_id.name)
            mytuple = (m[0],name)
            result.append(mytuple)
        return result

    def _compute_match_name(self, cr, uid, ids, vals = {}):
        if isinstance(ids, (int, long)):
            ids = [ids]
        src_obj = self.pool.get('sport.round.classified')
        match_brw = ids and self.browse(cr, uid, ids[0]) or False
        date = 'date' in vals and vals['date'] or match_brw and match_brw.date
        # avoid 'False' value for home_team and visitor_team in vals
        home_team_id = vals.get('home_team_id',[]) == False and vals['home_team_id'] or vals.get('home_team_id',[])
        visitor_team_id = vals.get('visitor_team_id',[]) == False and vals['visitor_team_id'] or vals.get('visitor_team_id',[])
        home_team_name = False
        visitor_team_name = False
        #~ print '******* date ******',date
        # empty name
        name = 'None vs. None'
        round_id = 'round_id' in vals and vals['round_id'] or match_brw and match_brw.round_id.id
        next_round = round_id and src_obj.search(cr, uid, [('next_round_id','=',round_id)])
        #~ print '******* next_round ******',next_round
        if home_team_id is not False and visitor_team_id is not False \
            or (match_brw and match_brw.home_team_id.id and match_brw.visitor_team_id.id):
            knockout = match_brw and match_brw.knockout
            home_team_name = 'home_team_id' in vals and self.pool.get('sport.team').browse(cr, uid, vals['home_team_id']).name or match_brw and match_brw.home_team_id.name
            home_score = 'home_score' in vals and vals['home_score'] or match_brw and match_brw.home_score or 0
            home_ot_score = 'home_ot_score' in vals and vals['home_ot_score'] or match_brw and match_brw.home_ot_score or 0
            visitor_team_name = 'visitor_team_id' in vals and self.pool.get('sport.team').browse(cr, uid, vals['visitor_team_id']).name or match_brw and match_brw.visitor_team_id.name
            visitor_score = 'visitor_score' in vals and vals['visitor_score'] or match_brw and match_brw.visitor_score or 0
            visitor_ot_score = 'visitor_ot_score' in vals and vals['visitor_ot_score'] or match_brw and match_brw.visitor_ot_score or 0
            state = 'state' in vals and vals['state'] or match_brw and match_brw.state or 'scheduled'
            name = '%s vs. %s'%(home_team_name,visitor_team_name)
            if state == 'done' and (home_score - visitor_score == 0) and knockout:
                name = '%s %d(%d) - %d(%d) %s'%(home_team_name,\
                                    home_score, \
                                    home_ot_score,\
                                    visitor_score, \
                                    visitor_ot_score, \
                                    visitor_team_name)
            elif state in ['done','started']:
                name = '%s %d - %d %s%s'%(home_team_name,\
                                    home_score, \
                                    visitor_score, \
                                    visitor_team_name,\
                                    state == 'started' and ', en curso' or '')
            #~ print '******* home_team_name ******',home_team_name
            #~ print '******* visitor_team_name ******',visitor_team_name
        if next_round and (home_team_name in [False,None] or visitor_team_name in [False,None]):
            side = {}
            for nxt_id in next_round:
                nxt_brw = src_obj.browse(cr, uid, nxt_id)
                if nxt_brw.side == 'home':
                    side.update({'home': nxt_brw.name})
                else:
                    side.update({'visitor': nxt_brw.name})
            if 'home' in side and 'visitor' in side:
                name = '%s vs. %s'%(home_team_name in [False,None] and \
                side['home'] or home_team_name, \
                visitor_team_name in [False,None] and \
                side['visitor'] or visitor_team_name)
            #~ print '******* next_round ******',next_round
            #~ print '******* side ******',side
        if date:
            #~ lang = self.pool.get('res.users').browse(cr, uid, uid).lang
            #~ print '******* lang ******',lang
            try:
                #~ print '******* date ******',date
                #~ if lang[:2]=='es':
                d = datetime.strptime(date, '%Y-%m-%d %H:%M')
                #~ else:
                    #~ d = datetime.strptime(date, '%d-%m-%Y %H:%M')
                name = name + ', ' + d.strftime('%d %b')
            except:
                #~ print '******* except ******'
                pass
        return name

    def _compute_diff(self):
        brw = self.browse(cr, uid, ids)
        res = {}
        for b in brw:
            res[b.id] = b.home_score + b.home_ot_score - \
                (b.visitor_score + b.visitor_ot_score)
        return res

    def _compute_knockout(self):
        stages = ['16th','8th','quarter','semi','third','final']
        brw = self.browse(cr, uid, ids)
        res = {}
        for b in brw:
            res[b.id] = b.round_id.stage in stages
        return res

    def switch_teams(self, cr, uid, ids, context=None):
        for match_brw in self.browse(cr, uid, ids):
            self.write(cr, uid, match_brw.id, {
                name': self._compute_match_name(cr, uid, ids),
                home_team_id': match_brw.visitor_team_id.id,
                visitor_team_id': match_brw.home_team_id.id,
                home_score': match_brw.visitor_score,
                visitor_score': match_brw.home_score,
                home_ot_score': match_brw.visitor_ot_score,
                visitor_ot_score': match_brw.home_ot_score,
                }, context=None)
        return {}

    def create(self, cr, uid, vals, context=None):
        if 'name' not in vals or not vals['name']:
            vals.update({'name': self._compute_match_name(cr, uid, [], vals) })
        return super(sport_match, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        bet_group_obj = self.pool.get('sport.bet.group')
        for match_id in ids:
            vals.update({'name': self._compute_match_name(cr, uid, match_id, vals) })
        res = super(sport_match, self).write(cr, uid, ids, vals, context=context)
        for brw in self.browse(cr, uid, ids, context=context):
            match_done = [x.id for x in brw.round_id.match_ids if x.state == 'done']
            done = brw.round_id.matches == len(match_done)
            brw.round_id.write({'done': done})
            # order standing object by attrs: point, diff desc
            brw.round_id.update_standings()
            # order group of bets object by attr: point desc
            bet_group_ids = bet_group_obj.search(cr, uid, [])
            bet_group_obj.update_ranking(cr, uid, bet_group_ids, context=context)
            if done:
                # assign classified teams to matches automatically
                for classified in brw.round_id.classified_ids:
                    key = classified.side == 'home' and 'home_team_id' or 'visitor_team_id'
                    team_id = classified.team_id.id
                    next_round = classified.next_round_id
                    # update match teams for next round
                    # TODO: change that for next round with +1 matches
                    if len(next_round.match_ids) == 1:
                        map(lambda m: m.write({key: team_id}), next_round.match_ids)
                        next_round.write({'team_ids': [(4,team_id)]})
        return res

    _columns = {
    name = fields.Char('Name', size=64),
    sequence = fields.Integer('Match number', required=True),
    tournament_id = fields.Many2one('sport.tournament', 'Tournament', required=True),
    round_id = fields.Many2one('sport.round', 'Round/Division', required=True),
    home_team_id = fields.Many2one('sport.team', 'Home Team'),
    visitor_team_id = fields.Many2one('sport.team', 'Visitor Team'),
    home_score = fields.Integer('Home score'),
    visitor_score = fields.Integer('Visitor score'),
    home_ot_score = fields.Integer('Home overtime score'),
    visitor_ot_score = fields.Integer('Visitor overtime score'),
    date = fields.Datetime('Begin Date'),
    state = fields.selection([
            ('scheduled', 'Has not started'),
            ('started', 'Already started'),
            ('postponed', 'Will be rescheduled'),
            ('delayed', 'Will begin delayed'),
            ('done', 'Finished'),
            ], 'Status',  ),
    country_id = fields.Many2one('res.country', 'Country'),
    state_id = fields.Many2one('res.country.state', 'State'),
        #~ 'playoff = fields.boolean('Playoff game'),
    knockout = fields.function(_compute_knockout, type='boolean', string='Knockout game'),
    venue = fields.Char('Venue', size=64),
    diff = fields.function(_compute_diff, type='integer', string='Score difference'),
        #~ 'date_end = fields.boolean('Active', help="By unchecking the active field, you may hide an INCOTERM without deleting it."),
    }

    _defaults = {
        #~ 'playoff' :  False,
    }


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
