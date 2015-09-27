from openerp import fields, models


class Course(models.Model):
    '''
    This class create a model of Course
    '''

    _name = 'openacademy.course'

    name = fields.Char(string='Title', required=True) # Field reserverd to identified record alias
    description = fields.Text(string='Description')
    responsible_id = fields.Many2one('res.users',
                                     ondelete='set null',
                                     String='Responsible',index=True)
    session_ids = fields.One2many('openacademy.session', 'course_id', 
                                  string="Sessions")

    _sql_constraints = [
        ('name_description_check',
         'CHECK(name != description)',
         "The title of the course should not be the description"),

        ('name_unique',
         'UNIQUE(name)',
         "The course title must be unique"),
    ]

