import functools
import xmlrpclib
HOST = 'localhost'
PORT = 8069
DB = 'odoo_curso'
USER = 'admin'
PASS = 'admin'
ROOT = 'http://%s:%d/xmlrpc/' % (HOST,PORT)

# 1. Login
uid = xmlrpclib.ServerProxy(ROOT + 'common').login(DB,USER,PASS)
print "Logged in as %s (uid:%d)" % (USER,uid)

call = functools.partial(
    xmlrpclib.ServerProxy(ROOT + 'object').execute,
    DB, uid, PASS)

# 2. Read the sessions
model = 'openacademy.session'
domain = []
method_name = 'search_read' 
fields = ['name', 'seats', 'taken_seats']
sessions = call(model, method_name, domain, fields)
for session in sessions:
    print "Session %s (%s seats), taken seats %d" % (session['name'],
session['seats'], session['taken_seats'])

method_name = 'search'
domain = [('name','=','Course 2')]
course_ids = call('openacademy.course',method_name,domain)
course_id = course_ids[0]
print "course_ids",course_ids

method_name = 'create'
responsible_id =  call('res.partner','search',[('name','=','Vauxoo')])[0]
print "responsible_id",responsible_id
new_session =  {
    'name': 'Session from ws',
    'instructor_id': responsible_id,
    'course_id': course_id,
    'attendee_ids': [(4,7),(4,3)]
}
new_session_id = call(model, method_name, new_session)

#new_session = {'name': 'Session from ws', 'course_id': course_id }
#new_session_id = call(model, method_name, new_session )
print "new session_id",new_session_id


