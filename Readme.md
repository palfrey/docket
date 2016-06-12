Docket
======
[![Build Status](https://travis-ci.org/palfrey/docket.svg?branch=master)](https://travis-ci.org/palfrey/docket)

Docket allows users of both [Beeminder](https://www.beeminder.com/) and [Todoist](https://en.todoist.com/) to get a merged view of both by adding synchronised tasks in Todoist for your Beeminder "last day to do this thing" days.

Local Setup
-----------
1. Copy `config.yaml.example` to `config.yaml` and fill in the values there as we go through the later steps
2. Register app at https://developer.todoist.com/appconsole.html and get the OAuth Client/Secret for `config.yaml`
    * OAuth Redirect URL there to "<host>/todoist/oauth" (http://localhost:5000/todoist/oauth for local setup)
3. Register app at https://www.beeminder.com/apps/new and again get the OAuth values for `config.yaml`
    * Redirect URL should be "<host>/todoist/oauth" (http://localhost:5000/todoist/oauth for local setup)
    * Post deauthorisation URL isn't set
4. If you've already got [Bower](https://bower.io/) installed, just run `bower install`. Otherwise, install [Node.js](https://nodejs.org/en/) and run `npm install`, which will install and run Bower.
5. `pip install -r requirements.txt` (preferably within a [Virtualenv](https://virtualenv.pypa.io/en/stable/) because that's just sensible)
5. `./debug-run.sh`

You've now got a running version of the app at http://localhost:5000. Running `python docket.py` will synchronise all registered users.

Heroku Setup
------------

There's a running instance of this at https://docket-heroku.herokuapp.com/ but here's how I did that.

1. Get a [Heroku](https://www.heroku.com/) account. Free ones work fine.
2. Install the [Heroku toolbelt](https://toolbelt.heroku.com/)
3. Goto your [dashboard](https://dashboard.heroku.com/apps/) and make a new app. Mine was called "docket-heroku" but you'll need to use another name for yours, and replace anywhere I use that.
4. `heroku git:remote --app docket-heroku` to make it possible to push to deploy to your new app.
5. We're using multiple buildpacks, both the Python (backend) and Node.js (assets). Just doing `heroku buildpacks:add --index 1 heroku/nodejs` should get you configured correctly, but for reference the result of `heroku buildpacks` should say (and if it doesn't, read [the docs](https://devcenter.heroku.com/articles/using-multiple-buildpacks-for-an-app))
   1. heroku/nodejs
   2. heroku/python
6. Add the [PostgreSQL addon](https://elements.heroku.com/addons/heroku-postgresql)
7. Go into the settings for your app and set the following config variables:
   * BEEMINDER_CLIENT_ID/BEEMINDER_CLIENT_SECRET - Beeminder app configured as per above, but with your Heroku URL, not localhost
   * TODOIST_CLIENT_ID/TODOIST_CLIENT_SECRET - Ditto, but for Todoist
   * FLASK_ENCRYPTION_KEY - Something secret for Flask to use for [cookie encryption](http://flask.pocoo.org/docs/0.11/quickstart/#sessions)
8. [`git push heroku master`](https://devcenter.heroku.com/articles/git#deploying-code)
8. At this point, goto your Heroku URL and check everything works. You might have an error page the first time you load it due to clashes between multiple workers all trying to configure the DB. Just refresh and it should fix itself.
9. Add the [Scheduler addon](https://elements.heroku.com/addons/scheduler) and configure the update command (`python docket.py`) to run every so often.
