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


# simple sql queries
s_query = Template("SELECT * FROM {{ent}} WHERE name_{{ent[0:2]}} LIKE '%{{find.strip(' ')}}%' ORDER BY {{order}}")
# advanced sql queries
q_query = Template("SELECT name_{{ent[0:2]}} FROM {{ent}} NATURAL JOIN {{rel}} WHERE {{want}}")

@app.route('/simple/find/', methods = ['GET','POST'])
def simple_find():
  entity = request.form['entity']
  name = request.form['name']
  orderby = "name_"+entity[0:2]
  q = s_query.render(ent=entity, find=name, order=orderby)
  things = querylist(q)
  headers = getcolumns(entity)
  things = [headers]+things
  rows = dict(results = things)

  return render_template('results.html', **rows)

@app.route('/advanced/find/name')
def advance_find():
  entity = request.form['entity']
  relations = request.form['relations[]']
  wants = request.form['want[]']
  headers = getcolumns(entity)
  all_results = []
  for n in range(len(relations)):
    q = a_query.render(ent=entity,rel=relations[n],want=wants[n])
    all_results.append(querylist(q))
  things = []
  for each in all_results:
    if all_results.count(each) == len(wants) and each not in things:
      things.append(each)
  rows = dict(results = things)

  return render_template('results.html', **rows)

trelated = Template("SELECT table_name FROM w4111.information_schema.columns WHERE column_name LIKE 'name_{{ent[0:2}}' AND table_name NOT LIKE '{{ent}}'")
def related(entlist = ['pokemon','moves','location','items','characters']):
  rel = {}
  for e in entlist:
    q = trelated.render(ent = e)
    rel[e] = querylist(q)

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

@app.route('/simple/find/<option>/', methods = ['GET','POST'])
def s_reorder():
    reordered = dict()
    return render_template('simfind.html', **reordered)

@app.route('/advanced/find/<option>/', methods = ['GET','POST'])
def a_reorder():
    reordered = dict()
    return render_template('advfind.html', **reordered)

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
