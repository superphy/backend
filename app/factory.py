'''
this is the app factory
'''

from flask import Flask
from flask_bootstrap import Bootstrap
from . import config
from .main.views import bp as main
from flask_uploads import UploadSet, IMAGES, configure_uploads

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.config.from_envvar('LOCAL_SETTINGS', silent=True)

    # add extensions to app
    Bootstrap(app)

    app.register_blueprint(main)

    return app
