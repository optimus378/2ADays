from flask import Flask, render_template,request, redirect, url_for, flash, abort, send_file,abort, Response
from flask_dance.contrib.azure import azure, make_azure_blueprint
import datetime
import sharepy
import twoaday
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField, HiddenField,TextAreaField, StringField, FileField, BooleanField
from wtforms.validators import InputRequired, Email, Length, NumberRange
import json
from werkzeug.utils import secure_filename
import os
from oauthlib.oauth2.rfc6749.errors import InvalidClientIdError
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
app = Flask(__name__)
app.config['SECRET_KEY'] = 'asdfaioasdfkjhasdfkljh349856@#$^@#&@$%UDFHSDFH@#$589234y6oiapdfhgna9088q34258'
UPLOAD_FOLDER = 'static/temp/'
ALLOWED_EXTENSIONS = set(['csv'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

blueprint = make_azure_blueprint(
    client_id="A Thing",
    client_secret="A Secret",
    tenant='A Tentant',)

app.register_blueprint(blueprint, url_prefix="/login")



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Interaction(FlaskForm):
    interaction = SelectField('Interaction', choices = [('Voicemail', 'Voicemail'),('Talked','Talked'),('Other','Other'),('None','None')])
    comment = TextAreaField('Comment')
    agentid= HiddenField()
    staffname = HiddenField()

class uploadTop20(FlaskForm):
    top20 = FileField()

class EditStaff(FlaskForm):
    staffname = StringField()

@app.errorhandler(TokenExpiredError)
def token_expired(_):
    del app.blueprints['azure'].token
    return redirect(url_for('index'))
    
@app.route('/',methods=['GET','POST'])
def index():
    if not azure.authorized:
        return redirect(url_for("azure.login"))
    resp = azure.get("/v1.0/me")
    assert resp.ok
    staff = twoaday.listStaff()
    date = datetime.datetime.now()
    agentcount = twoaday.agentcol.count()
    return render_template("index.html", staff = staff, date =date, agentcount = agentcount)
    

@app.route('/admin/<staffmember>')
def stafflist(staffmember):
    agentlist = twoaday.getagentlist(staffmember)
    return render_template ('agentlist.html', staffmember = staffmember, agentlist = agentlist)

@app.route('/editstaff', methods=['GET','POST'])
def editstaff(TL=None,staffname = None):
    staff = twoaday.listStaff()
    form = EditStaff()
    if form.validate_on_submit():
        staffname=form.staffname.data
        twoaday.addStaff(staffname)
   # if request.args['TL'] =='True':
    #    twoaday.addTL(request.args['staffname'])
     #   flash('TL Designation added to ' + staffname, success)
  #  if request.args['TL'] == 'False':
   #     twoaday.removeTL(request.arg['staffname'])
    #    flash('TL Designation Removed From ' + staffname)
    if request.args.get('delete') =='yes':
        twoaday.delStaff(request.args['staffname'])
    return render_template('/editstaff.html', staff = staff ,form = form)

@app.route('/startnewmonth', methods=['GET','POST'])
def startnewmonth(sync=None, scramble=None):
    form = uploadTop20()
    agentcount = twoaday.agentcol.count()
    if form.validate_on_submit():
        file= request.files['top20']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        archived = twoaday.importTop20(UPLOAD_FOLDER+filename)
        archivedAgents= str(archived)
        flash("Success, The following Agents Have been archived. " + archivedAgents)
        return render_template("startnewmonth.html", agentcount = agentcount, form = form)
    if request.args.get('sync'):
        twoaday.syncSPList()
        flash ('Successfully Synced List with Agent Management','success')
        return render_template("startnewmonth.html", agentcount = agentcount, form = form)
    if request.args.get('scramble'):
         twoaday.splitlist()
         flash ('Successfully Scrambled List for New Month','success')
         return render_template("startnewmonth.html", agentcount = agentcount, form = form)
    return render_template("startnewmonth.html", agentcount = agentcount, form = form)

@app.route('/agentpage/<agentid>/',  methods =['GET','POST'])
def agentpage(agentid):
    agent = twoaday.agentcol.find_one({'_id':agentid})
    try: 
        agent['currentInteraction']
        form = Interaction(interaction = agent['currentInteraction'] )
    except:
        form = Interaction()
    if form.validate_on_submit():
        comment = form.comment.data
        agentid = form.agentid.data
        staffname = form.staffname.data
        interaction = form.interaction.data
        twoaday.updateagent(comment,agentid,interaction)
        flash('Agent Updated.', 'success' )
        return redirect('/admin/'+staffname)
    return render_template('agentpage.html' , agent=agent, form = form)

if __name__ == '__main__':
    app.run(debug=True, host='localhost')
