import datetime
import humanize


def build_models(db):
    class User(db.Model):
        todoist_id = db.Column(db.Integer, primary_key=True)
        todoist_access_token = db.Column(db.String(40), unique=True)
        last_update = db.Column(db.DateTime)
        beeminder_access_token = db.Column(db.String(25), unique=True)

        def __init__(self, todoist_id, todoist_access_token):
            self.todoist_id = todoist_id
            self.todoist_access_token = todoist_access_token
            self.todoist_last_update = datetime.datetime.now()

        def pretty_update(self):
            if self.last_update is None:
                return "Never"
            return humanize.naturaltime(
                datetime.datetime.now() - self.last_update)

        def update(self):
            self.last_update = datetime.datetime.now()

        def update_beeminder(self, beeminder_access_token):
            self.beeminder_access_token = beeminder_access_token

        def __repr__(self):
            return '<User %r>' % self.todoist_id

    try:
        User.query.first()
    except:  # Assume that failure means tables not created
        db.create_all()
    return {"User": User}
