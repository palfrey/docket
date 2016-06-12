from __future__ import absolute_import
import requests
import yaml
from flask import Flask, render_template, url_for, request, session, redirect, flash
import todoist
from todoist.managers.labels import LabelsManager
from flask_sqlalchemy import SQLAlchemy
from .models import build_models
import urlparse
from datetime import datetime, timedelta

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
		user = User(todoist_id, access_token)
		user.update()
		db.session.add(user)
	elif len(existing) > 1:
		raise Exception, ("Weird things", existing)
	db.session.commit()
	session["todoist_id"] = todoist_id
	return redirect(url_for('index'))

@app.route("/beeminder/oauth", methods=["GET"])
def beeminder_oauth():
	existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
	existing.update_beeminder(request.args["access_token"])
	db.session.commit()
	flash("Logged into Beeminder")
	return redirect(url_for('index'))

@app.route("/todoist/update", methods=['POST'])
def todoist_update():
	existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
	api = todoist.api.TodoistAPI(existing.todoist_access_token)
	data = api.sync()
	lm = todoist.managers.labels.LabelsManager(api)
	if "beeminder" not in [x.data['name'] for x in lm.all()]:
		lm.add("beeminder")
		api.commit()
	beeminder_label = [x for x in lm.all() if x.data['name'] == "beeminder"][0].data['id']

	pm = todoist.managers.projects.ProjectsManager(api)
	if "Beeminder" not in [x.data['name'] for x in pm.all()]:
		pm.add("Beeminder")
		api.commit()
	else:
		project = [x for x in data['projects'] if x['name'] == "Beeminder"][0]
		if project['is_deleted'] == 1:
			raise Exception, project
	beeminder_project = [x for x in pm.all() if x.data['name'] == "Beeminder"][0].data['id']

	goals = requests.get("https://www.beeminder.com/api/v1/users/me/goals.json?filter=frontburner&access_token=%s" % existing.beeminder_access_token).json()

	im = todoist.managers.items.ItemsManager(api)
	existing_names = [
		x['content'] for x in data['items']
		if beeminder_label in x['labels']]
	for goal in goals:
		title = goal['title']
		losedate = goal['losedate']
		when = datetime.fromtimestamp(losedate)
		if when.hour < 5: # assume a early morning fail time, and so use previous day
			when = when.date() - timedelta(days = 1)
		else:
			when = when.date()
		if title in existing_names:
			item = [x for x in data['items'] if x['content'] == title][0]
			if item['project_id'] != beeminder_project:
				im.move({item['project_id']:[item['id']]}, beeminder_project)
			im.update(item['id'],
				date_string=when.strftime("%Y/%m/%d"),
				checked=0,
				in_history=0,
				project_id = beeminder_project,
				priority = 4)
		else:
			item = im.add(title, beeminder_project,
				date_string=when.strftime("%Y/%m/%d"),
				labels = [beeminder_label],
				priority = 4)
	api.commit()
	existing.update()
	db.session.commit()
	flash("All goals updated in Todoist")
	return redirect(url_for('index'))

if __name__ == "__main__":
    app.run()
