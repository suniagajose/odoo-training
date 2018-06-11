{
    'name' : 'Sports Management',
    'version' : '11.0.0.0.1',
    'author' : 'Jose Suniaga [Vauxoo] <josemiguel@vauxoo.com>',
    'summary': 'Managing sports events and bets',
    'website' : 'http://www.vauxoo.com',
    'description' : """
All about sports (Basketball, baseball, football, etc)
==================================
Details coming soon.
""",
    'depends' : [
        'base',
    ],
    'data' : [
        # Data
        'data/sport_sport_data.xml',
        'data/sport_tournament_data.xml',
        'data/sport_team_data.xml',
        'data/sport_round_data.xml',
        'data/sport_match_data.xml',

        # Views
        'views/sport_views.xml',
        'views/sport_bet_views.xml',
    ],
    'installable' : True,
    'application' : True,
}
