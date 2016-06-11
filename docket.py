from __future__ import absolute_import
import requests
import yaml
from flask import Flask, render_template, url_for, request, session, redirect, flash
import todoist
from todoist.managers.labels import LabelsManager
from flask_sqlalchemy import SQLAlchemy
from .models import build_models
import urlparse

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
		config["beeminder_url"] = urlparse.urljoin(config["app"]['host'], url_for('beeminder_oauth'))
		existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
		if existing == None:
			del session["todoist_id"]
			return redirect(url_for("index"))
		return render_template('index.html', data = existing, **config)
	else:
		return render_template('index.html', **config)

@app.route("/todoist/oauth", methods=["GET"])
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
	elif len(existing) > 1:
		raise Exception, ("Weird things", existing)
	else:
		existing[0].update_todoist(data, access_token)
	db.session.commit()
	session["todoist_id"] = todoist_id
	return redirect(url_for('index'))

@app.route("/beeminder/oauth", methods=["GET"])
def beeminder_oauth():
	existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
	auth_token = request.args["access_token"]
	goals = requests.get("https://www.beeminder.com/api/v1/users/me/goals.json?filter=frontburner&access_token=%s" % auth_token)
	existing.update_beeminder(goals.json(), auth_token)
	db.session.commit()
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
