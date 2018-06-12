# -*- coding: utf-8 -*-

import itertools
from datetime import datetime
from operator import attrgetter
from odoo.exceptions import ValidationError
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
    def load_matches(self):
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
    def load_standings(self):
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
    def update_standings(self):
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

    @api.multi
    @api.depends('match_ids.state')
    def _compute_done(self):
        for round in self:
            round.done = all([m.state == 'done' for m in round.match_ids])

    name = fields.Char('Name', size=64, required=True)
    tournament_id = fields.Many2one('sport.tournament', 'Tournament')
    team_ids = fields.Many2many('sport.team', 'sport_round_team_rel', 'round_id', 'team_id', 'Teams by Round')
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
    ], 'Stage')
    done = fields.Boolean('Finished round', compute='_compute_done')


class SportRoundClassified(models.Model):
    _name = "sport.round.classified"
    _description = "Runner Up"

    @api.multi
    @api.depends('position', 'round_id.standing_ids.sequence')
    def _compute_team_id(self):
        for classified in self:
            standing = classified.round_id.standing_ids.filtered(
                lambda std: std.sequence == classified.position)
            classified.team_id = standing[0].team_id if standing else False

    @api.multi
    @api.depends('position', 'round_id.name')
    def _compute_name(self):
        for classified in self:
            round_name = classified.round_id.name
            classified.name = str(classified.position) + u'° ' + round_name

    name = fields.Char('Name', compute='_compute_name', store=True)
    round_id = fields.Many2one('sport.round', 'Round')
    next_round_id = fields.Many2one('sport.round', 'Next Round')
    team_id = fields.Many2one('sport.team', compute='_compute_team_id', string='RunnerUp Team', store=True)
    side = fields.Selection([
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
                    against += match.visitor_score
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    against += match.home_score
            standing.against = against

    @api.multi
    def _compute_wins(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            wins = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and
                        standing.team_id.id == match.home_team_id.id):
                    wins += match.diff > 0 and 1 or 0
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    wins += match.diff < 0 and 1 or 0
            standing.wins = wins

    @api.multi
    def _compute_losses(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            losses = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and
                        standing.team_id.id == match.home_team_id.id):
                    losses += match.diff < 0 and 1 or 0
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    losses += match.diff > 0 and 1 or 0
            standing.losses = losses

    @api.multi
    def _compute_ties(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            ties = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and (
                        standing.team_id.id == match.home_team_id.id or
                        standing.team_id.id == match.visitor_team_id.id)):
                    ties += match.diff == 0 and 1 or 0
            standing.ties = ties

    @api.multi
    def _compute_points(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            points = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and
                        standing.team_id.id == match.home_team_id.id):
                    points += (
                        match.diff > 0 and 3 or match.diff == 0 and 1 or 0)
                elif (match.state in ['started', 'done'] and
                        standing.team_id.id == match.visitor_team_id.id):
                    points += (
                        match.diff < 0 and 3 or match.diff == 0 and 1 or 0)
            standing.points = points

    def _compute_played(self):
        for standing in self.filtered(lambda x: x.round_id != False):
            played = 0
            for match in standing.round_id.match_ids:
                if (match.state in ['started', 'done'] and (
                        standing.team_id.id == match.home_team_id.id or
                        standing.team_id.id == match.visitor_team_id.id)):
                    played += 1

            standing.played = played

    def _compute_diff(self):
        for standing in self:
            standing.diff = standing.favour - standing.against

    @api.model
    def create(self, vals):
        if 'team_id' in vals:
            team_id = vals['team_id']
            vals.update({'name': self.env['sport.team'].browse(team_id).name})
        else:
            raise ValidationError(_('Debes seleccionar un equipo'))
        return super(SportStanding, self).create(vals)

    name = fields.Char('Name', size=64, required=True)
    tournament_id = fields.Many2one('sport.tournament', 'Tournament')
    round_id = fields.Many2one('sport.round', 'Round')
    team_id = fields.Many2one('sport.team', 'Team')
    wins = fields.Integer(compute='_compute_wins')
    ties = fields.Integer(compute='_compute_ties')
    losses = fields.Integer(compute='_compute_losses')
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

    @api.multi
    @api.depends('sequence', 'round_id.name')
    def name_get(self):
        result = []
        for match in self:
            name = _('Game %s: %s') % (match.sequence, match.round_id.name)
            result.append((match.id, name))
        return result

    @api.depends('home_team_id', 'visitor_team_id', 'state')
    def _compute_name(self):
        for match in self:
            match.name = _('None vs. None')
            if not match.home_team_id or not match.visitor_team_id:
               continue
            home_team_name = match.home_team_id.name
            visitor_team_name = match.visitor_team_id.name
            name = '%s vs. %s' % (home_team_name, visitor_team_name)
            if (match.state == 'done' and
                    (match.home_score - match.visitor_score == 0) and
                    match.knockout):
                name = '%s %d(%d) - %d(%d) %s' % (
                    home_team_name,
                    match.home_score,
                    match.home_ot_score,
                    match.visitor_score,
                    match.visitor_ot_score,
                    visitor_team_name)
            elif match.state in ['done', 'started']:
                name = '%s %d - %d %s%s' % (
                    home_team_name,
                    match.home_score,
                    match.visitor_score,
                    visitor_team_name,
                    match.state == 'started' and _(', en curso') or '')

            # next_round = round_classified.search([('next_round_id','=', match.round_id.id)])
            # if next_round and (home_team_name in [False, None] or visitor_team_name in [False, None]):
            #     side = {}
            #     for nxt_id in next_round:
            #         if nxt_brw.side == 'home':
            #             side.update({'home': nxt_brw.name})
            #         else:
            #             side.update({'visitor': nxt_brw.name})
            #     if 'home' in side and 'visitor' in side:
            #         name = '%s vs. %s'%(home_team_name in [False,None] and \
            #         side['home'] or home_team_name, \
            #         visitor_team_name in [False,None] and \
            #         side['visitor'] or visitor_team_name)
            if match.date:
                try:
                    d = datetime.strptime(match.date, '%Y-%m-%d %H:%M')
                    name = name + ', ' + d.strftime('%d %b')
                except:
                    pass
            match.name = name

    @api.multi
    @api.depends('home_score', 'home_ot_score', 'visitor_score',
                 'visitor_ot_score')
    def _compute_diff(self):
        for match in self:
            total_home_score = match.home_score + match.home_ot_score
            total_visitor_score = match.visitor_score + match.visitor_ot_score
            match.diff = total_home_score - total_visitor_score

    @api.multi
    @api.depends('round_id.stage')
    def _compute_knockout(self):
        stages = ['16th','8th','quarter','semi','third','final']
        for match in self:
            match.knockout = match.round_id.stage in stages

    name = fields.Char(compute='_compute_name', store=True)
    sequence = fields.Integer('Match number', required=True)
    tournament_id = fields.Many2one('sport.tournament', 'Tournament', related='round_id.tournament_id', store=True)
    round_id = fields.Many2one('sport.round', 'Round/Division', required=True)
    home_team_id = fields.Many2one('sport.team', 'Home Team')
    visitor_team_id = fields.Many2one('sport.team', 'Visitor Team')
    home_score = fields.Integer('Home score')
    visitor_score = fields.Integer('Visitor score')
    home_ot_score = fields.Integer('Home overtime score')
    visitor_ot_score = fields.Integer('Visitor overtime score')
    date = fields.Datetime('Begin Date')
    state = fields.Selection([
        ('scheduled', 'Has not started'),
        ('started', 'Already started'),
        ('postponed', 'Will be rescheduled'),
        ('delayed', 'Will begin delayed'),
        ('done', 'Finished'),
    ], 'Status', default='scheduled')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    #~ 'playoff = fields.boolean('Playoff game'),
    knockout = fields.Boolean(compute='_compute_knockout', string='Knockout game')
    venue = fields.Char('Venue', size=64)
    diff = fields.Integer(compute='_compute_diff', string='Score difference')
    #~ 'date_end = fields.boolean('Active', help="By unchecking the active field, you may hide an INCOTERM without deleting it."),

    @api.multi
    def switch_teams(self):
        self.ensure_one()
        res = self.write({
            'home_team_id': self.visitor_team_id.id,
            'visitor_team_id': self.home_team_id.id,
            'home_score': self.visitor_score,
            'visitor_score': self.home_score,
            'home_ot_score': self.visitor_ot_score,
            'visitor_ot_score': self.home_ot_score,
        })
        return res

    @api.multi
    def write(self, vals):
        res = super(SportMatch, self).write(vals)
        # bet_group = self.env['sport.bet.group']
        for match in self:
            # order standing object by attrs: point, diff desc
            match.round_id.update_standings()
            # order group of bets object by attr: point desc
            # bet_group.search([]).update_ranking()
            if match.round_id.done:
                # assign classified teams to matches automatically
                for classified in match.round_id.classified_ids:
                    key = '%s_team_id' % (classified.side)
                    team_id = classified.team_id
                    next_round = classified.next_round_id
                    # update match teams for next round
                    # TODO: change that for next round with +1 matches
                    if next_round.matches == 1:
                        next_match = next_round.match_ids
                        next_match.write({key: team_id.id})
                        next_round.write({'team_ids': [(4,team_id.id)]})
        return res
