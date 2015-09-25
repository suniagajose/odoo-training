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
