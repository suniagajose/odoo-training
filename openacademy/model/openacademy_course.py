from openerp import fields, models, api


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

    @api.one # api.one send defaults params: cr, uid, id, context
    def copy(self, default=None):
        default = dict(default or {})
        copied_count = self.search_count(
            [('name', '=like', u"Copy of {}%".format(self.name))])
        if not copied_count:
            new_name = u"Copy of {}".format(self.name)
        else:
            new_name = u"Copy of {} ({})".format(self.name, copied_count)
        default['name'] = new_name
        return super(Course, self).copy(default)
