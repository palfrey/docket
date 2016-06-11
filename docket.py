from __future__ import absolute_import
import requests
import yaml
from flask import Flask, render_template, url_for, request, session, redirect, flash
import todoist
from todoist.managers.labels import LabelsManager
from flask_sqlalchemy import SQLAlchemy
from .models import build_models

config = yaml.safe_load(file('config.yaml', 'r'))
app = Flask(__name__)
app.secret_key = config["flask"]["secret_key"]
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
models = build_models(db)
User = models["User"]

@app.route("/")
def index():
	if "todoist_id" in session:
		existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
		return render_template('index.html', todoist_data = existing, **config)
	else:
		return render_template('index.html', **config)

@app.route("/todoist_oauth", methods=["GET"])
def todoist_oauth():
	payload = {
		'client_id': config["todoist"]["client_id"],
		'client_secret': config["todoist"]["client_secret"],
		'code': request.args["code"],
		'redirect_uri': url_for("index")
	}
	r = requests.post("https://todoist.com/oauth/access_token", data=payload)
	ret = r.json()
	if "error" in ret:
		raise Exception, ret
	access_token = ret["access_token"]
	flash("Logged into Todoist")
	api = todoist.api.TodoistAPI(access_token)
	data = api.sync()
	todoist_id = data["user"]["id"]
	existing = User.query.filter_by(todoist_id=todoist_id).all()
	if len(existing) == 0:
		user = User(todoist_id, data, access_token)
		db.session.add(user)
		db.session.commit()
	elif len(existing) > 1:
		raise Exception, ("Weird things", existing)
	else:
		existing = existing[0]
		existing.data = data
		existing.access_token = access_token
		db.session.commit()
	session["todoist_id"] = todoist_id
	return redirect(url_for('index'))

@app.route("/sync", methods=['POST'])
def sync():
	existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
	api = todoist.api.TodoistAPI(existing.access_token)
	existing.data = api.sync()
	db.session.commit()
	return redirect(url_for('index'))

if __name__ == "__main__":
    app.run()
