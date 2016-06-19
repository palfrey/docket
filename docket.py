from __future__ import print_function
import requests
import yaml
from flask import (Flask, render_template, url_for,
                   request, session, redirect, flash)
import todoist
from flask_sqlalchemy import SQLAlchemy
from models import build_models
import urlparse
from datetime import datetime, timedelta
import os

app = Flask(__name__)
if "DYNO" in os.environ:
    app.logger.info(
        "Found DYNO environment variable, so assuming we're in Heroku")
    config = {
        "app": {
            "database_uri": os.environ["DATABASE_URL"]
        },
        "todoist": {
            "client_id": os.environ["TODOIST_CLIENT_ID"],
            "client_secret": os.environ["TODOIST_CLIENT_SECRET"]
        },
        "beeminder": {
            "client_id": os.environ["BEEMINDER_CLIENT_ID"],
            "client_secret": os.environ["BEEMINDER_CLIENT_SECRET"]
        },
        "flask": {
            "secret_key": os.environ["FLASK_ENCRYPTION_KEY"]
        }
    }
else:
    config = yaml.safe_load(open('config.yaml', 'r'))

app.secret_key = config["flask"]["secret_key"]
app.config['SQLALCHEMY_DATABASE_URI'] = config["app"]["database_uri"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
models = build_models(db)
User = models["User"]


@app.route("/")
def index():
    if "todoist_id" in session:
        config["beeminder_url"] = urlparse.urljoin(
            request.url_root, url_for('beeminder_oauth'))
        existing = User.query.filter_by(
            todoist_id=session["todoist_id"]).first()
        if existing is None:
            del session["todoist_id"]
            return redirect(url_for("index"))
        return render_template('index.html', data=existing, **config)
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
        raise Exception(ret)
    access_token = ret["access_token"]
    flash("Logged into Todoist")
    api = todoist.api.TodoistAPI(access_token)
    data = api.sync()
    todoist_id = data["user"]["id"]
    existing = User.query.filter_by(todoist_id=todoist_id).all()
    if len(existing) == 0:
        user = User(todoist_id, access_token)
        db.session.add(user)
    elif len(existing) > 1:
        raise Exception(("Weird things", existing))
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


# From http://stackoverflow.com/a/25097622/320546
def nsf(num, n=1):
    """n-Significant Figures"""
    if num >= 10 ** n:
        return int(num)  # All available in the pre-decimal bits
    numstr = ("{0:.%ie}" % (n-1)).format(num)
    return float(numstr)


def update_tasks(user):
    api = todoist.api.TodoistAPI(user.todoist_access_token)
    data = api.sync()
    lm = todoist.managers.labels.LabelsManager(api)
    if "beeminder" not in [x.data['name'] for x in lm.all()]:
        lm.add("beeminder")
        api.commit()
    beeminder_label = [x for x in lm.all()
                       if x.data['name'] == "beeminder"][0].data['id']

    pm = todoist.managers.projects.ProjectsManager(api)
    if "Beeminder" not in [x.data['name'] for x in pm.all()]:
        pm.add("Beeminder")
        api.commit()
    else:
        project = [x for x in data['projects'] if x['name'] == "Beeminder"][0]
        if project['is_deleted'] == 1:
            raise Exception(project)
    beeminder_project = [x for x in pm.all()
                         if x.data['name'] == "Beeminder"][0].data['id']

    goals = requests.get(
        "https://www.beeminder.com/api/v1/users/me/goals.json" +
        ("?filter=frontburner&access_token=%s"
         % user.beeminder_access_token)).json()

    im = todoist.managers.items.ItemsManager(api)
    existing_names = [
        x['content'] for x in data['items']
        if beeminder_label in x['labels']]
    for goal in goals:
        title = goal['title']
        losedate = goal['losedate']
        when = datetime.fromtimestamp(losedate)
        if when.hour < 5:
            # assume a early morning fail time, and so use previous day
            when = when.date() - timedelta(days=1)
        else:
            when = when.date()
        longtitle = "%s (%s)" % (
            title, nsf(goal["safebump"]-goal["curval"], 2))
        if title in [x[:len(title)] for x in existing_names]:
            item = [x for x in data['items']
                    if x['content'][:len(title)] == title][0]
            if item['project_id'] != beeminder_project:
                im.move({item['project_id']: [item['id']]}, beeminder_project)
            im.update(item['id'],
                      content=longtitle,
                      date_string=when.strftime("%Y/%m/%d"),
                      checked=0,
                      in_history=0,
                      project_id=beeminder_project,
                      priority=4)
        else:
            item = im.add(longtitle, beeminder_project,
                          date_string=when.strftime("%Y/%m/%d"),
                          labels=[beeminder_label],
                          priority=4)
    api.commit()
    user.update()


@app.route("/todoist/update", methods=['POST'])
def todoist_update():
    existing = User.query.filter_by(todoist_id=session["todoist_id"]).first()
    update_tasks(existing)
    db.session.commit()
    flash("All goals updated in Todoist")
    return redirect(url_for('index'))

if __name__ == "__main__":
    users = User.query.all()
    for user in users:
        if user.beeminder_access_token is None:
            print("Skipping %s because no beeminder token" % user)
            continue
        print("Updating", user)
        update_tasks(user)
    db.session.commit()
