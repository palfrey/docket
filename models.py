def build_models(db):
    class User(db.Model):
        todoist_id = db.Column(db.Integer, primary_key=True)
        todoist = db.Column(db.PickleType, unique=True)
        access_token = db.Column(db.String(40), unique=True)

        def __init__(self, todoist_id, todoist, access_token):
            self.todoist_id = todoist_id
            self.todoist = todoist
            self.access_token = access_token

        def __repr__(self):
            return '<User %r>' % self.todoist_id

    db.create_all()
    return {"User": User}
