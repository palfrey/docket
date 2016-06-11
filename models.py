import datetime
import humanize

def build_models(db):
    class User(db.Model):
        todoist_id = db.Column(db.Integer, primary_key=True)
        todoist = db.Column(db.PickleType)
        todoist_access_token = db.Column(db.String(40), unique=True)
        todoist_last_update = db.Column(db.DateTime)

        beeminder_access_token = db.Column(db.String(25), unique=True)
        beeminder_goals = db.Column(db.PickleType)
        beeminder_last_update = db.Column(db.DateTime)

        def __init__(self, todoist_id, todoist, todoist_access_token):
            self.todoist_id = todoist_id
            self.todoist = todoist
            self.todoist_access_token = todoist_access_token
            self.todoist_last_update = datetime.datetime.now()

        def todoist_pretty_update(self):
            return humanize.naturaltime(datetime.datetime.now() - self.todoist_last_update)

        def update_todoist(self, todoist, todoist_access_token):
            self.todoist = todoist
            self.todoist_access_token = todoist_access_token
            self.todoist_last_update = datetime.datetime.now()

        def beeminder_pretty_update(self):
            return humanize.naturaltime(datetime.datetime.now() - self.beeminder_last_update)

        def update_beeminder(self, beeminder_goals, beeminder_access_token):
            self.beeminder_goals = beeminder_goals
            self.beeminder_access_token = beeminder_access_token
            self.beeminder_last_update = datetime.datetime.now()

        def __repr__(self):
            return '<User %r>' % self.todoist_id

    db.create_all()
    return {"User": User}
