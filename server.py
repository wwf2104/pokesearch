"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
from jinja2 import Template

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DATABASEURI = "postgresql://jj2882:7025@104.196.18.7/w4111"
#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.errorhandler(500)
def error500(error):
  opts = [500] + alldtypes()
  options_dict = dict(results = opts)
  return render_template("dtypes.html", **options_dict)
@app.errorhandler(404)
def error404(error):
  opts = [404]
  options_dict = dict(results = opts)
  return render_template("errors.html", **options_dict)
@app.errorhandler(405)
def error405(error):
  opts = [405]
  options_dict = dict(results = opts)
  return render_template("errors.html", **options_dict)
@app.errorhandler(408)
def error408(error):
    opts = [408]
    options_dict = dict(results = opts)
    return render_template("errors.html", **options_dict)

entities = ['pokemon','moves','location','items','characters']

@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:
  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2
  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """
  # DEBUG: this is debugging code to see what request looks like
  print(request.args)
  options = ['toggle_as()', entities, related()]
  options_dict = dict(opts = options)

  return render_template("index.html", **options_dict)

@app.route('/advanced/')
def adv_index():
    print(request.args)
    options = ['toggle_sa()', entities, related()]
    options_dict = dict(opts = options)

    return render_template("index.html", **options_dict)

@app.route('/datatypes/', methods = ['GET', 'POST'])
def dtypes():
  dtype_list = dict(results = alldtypes())
  return render_template("dtypes.html", **dtype_list)

def alldtypes():
  q = "SELECT DISTINCT table_name,column_name, data_type FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema LIKE '%2882' ORDER BY table_name"
  things = querylist(q)
  headers = ('Table Name','Column Name', 'Data Type', 'What to Input')
  things = [headers]+things
  return things

# simple sql queries
s_query = Template("SELECT DISTINCT * FROM {{ent}} WHERE LOWER(name_{{ent[0:2]}}) LIKE LOWER('%{{find}}%')")
# advanced sql queries
a_char_query = Template("SELECT DISTINCT {{heads}} FROM {{ent}} NATURAL JOIN (SELECT name_{{ent[0:2]}} FROM {{rel}} WHERE LOWER({{col}}) LIKE LOWER('%{{want}}%')) AS find")
a_num_query = Template("SELECT DISTINCT {{heads}} FROM {{ent}} NATURAL JOIN (SELECT name_{{ent[0:2]}} FROM {{rel}} WHERE {{col}} >= {{want}}) AS find")
a_bool_query = Template("SELECT DISTINCT {{heads}} FROM {{ent}} NATURAL JOIN (SELECT name_{{ent[0:2]}} FROM {{rel}} WHERE LOWER({{col}}) = LOWER('%{{want}}%')) AS find")
# find intersections
int_query = Template("{{q1}} INTERSECT {{q2}}")

@app.route('/simple/results/', methods = ['GET','POST'])
def simple_find():
  entity = request.form['entity']
  name = request.form['name'].strip().capitalize();
  q = s_query.render(ent=entity, find=name)
  things = querylist(q)
  headers = getcolumns(entity)
  things = [headers]+things
  rows = dict(results = things)

  return render_template('results.html', **rows)

@app.route('/advanced/results/', methods = ['GET','POST'])
def advance_find():
  entity = request.form['entity']
  relations = request.form.getlist('relations')
  cols = request.form.getlist('col')
  wants = request.form.getlist('want')
  headers = getcolumns(entity)
  head = ','.join(headers)

  if len(relations) > 1:
    all_query = []
    for n in range(len(relations)): 
      q = choosequery(head, entity,relations[n],cols[n],wants[n])
      all_query.append(q)
      
    big_query = all_query[0]
    for i in range(1, len(all_query)):
      big_query = int_query.render(q1 = big_query, q2 = all_query[i])
    print(big_query)
    things = querylist(big_query)
    print(things)
    
  else:
    q = choosequery(head, entity, relations[0],cols[0],wants[0])
    things = querylist(q)

  things = [headers]+things
  rows = dict(results = things)

  return render_template('results.html', **rows)

tdtype = Template("SELECT data_type FROM INFORMATION_SCHEMA.COLUMNS WHERE column_name LIKE '{{column}}'")
def getdatatypes(col):
    q = tdtype.render(column=col)
    dtype = querylist(q)[0][0]
    return dtype

char_types = ['character varying', 'text']
num_types = ['integer', 'double precision', 'smallint']
def choosequery(h, e, r, c, w):
  if getdatatypes(c) in char_types:
    q = a_char_query.render(heads = h,ent=e,rel=r,col=c,want=w.strip().capitalize())
  elif getdatatypes(c) in num_types:
    q = a_num_query.render(heads = h,ent=e,rel=r,col=c,want=float(w))
  else: # is boolean
    q = a_bool_query.render(heads = h,ent=e,rel=r,col=c,want=w.strip().capitalize())
  return q

trelated1 = Template("SELECT table_name FROM w4111.information_schema.columns WHERE column_name LIKE 'name_{{ent[0:2]}}'")
trelated2 = Template(" and column_name not like 'name_{{ent[0:2]}}'")

def related(entlist = ['pokemon','moves','location','items','characters']):
  rel = {}
  inner_dict = {}
  for e in entlist:
    q1 = trelated1.render(ent = e)
    q1_list = querylist(q1)
    for r in range(len(q1_list)):
      q2 = tcols.render(table = q1_list[r][0])+trelated2.render(ent=e)
      inner_dict[q1_list[r][0]] = querylist(q2)
    rel[e] = inner_dict.copy()
    inner_dict.clear()

  return rel

tcols = Template("select column_name from w4111.information_schema.columns where table_name like '{{table}}'")
def getcolumns(tname):
    q = tcols.render(table = tname)
    colnames = querylist(q, 'column_name')
    return colnames

def querylist(q, cols = None):
    things = []
    cursor = g.conn.execute(text(q))
    for each in cursor:
        if cols:
            things.append(each[cols])
        else:
            things.append(each)
    cursor.close()
    return things

@app.route('/login')
def login():
  abort(401)
  this_is_never_executed() 

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
