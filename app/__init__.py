import os
import re

from flask import Flask, request, redirect, session, abort
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError


import dmapiclient
import dmcontent.govuk_frontend
from dmutils import init_app
from dmutils.user import User
from dmutils.external import external as external_blueprint
from govuk_frontend_jinja.flask_ext import init_govuk_frontend

from config import configs


data_api_client = dmapiclient.DataAPIClient()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name):
    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    # allow using govuk-frontend Nunjucks templates
    init_govuk_frontend(application)

    init_app(
        application,
        configs[config_name],
        data_api_client=data_api_client,
        login_manager=login_manager,
    )

    from .main import main as main_blueprint
    from .main import public as public_blueprint
    from .status import status as status_blueprint
    from .metrics import metrics as metrics_blueprint, gds_metrics
    from .healthcheck import healthcheck as healthcheck_blueprint

    application.register_blueprint(status_blueprint, url_prefix='/suppliers/opportunities')
    application.register_blueprint(metrics_blueprint, url_prefix='/suppliers/opportunities')
    application.register_blueprint(main_blueprint, url_prefix='/suppliers/opportunities')
    application.register_blueprint(public_blueprint, url_prefix='/suppliers/opportunities')
    application.register_blueprint(healthcheck_blueprint, url_prefix='/healthcheck')

    # Must be registered last so that any routes declared in the app are registered first (i.e. take precedence over
    # the external NotImplemented routes in the dm-utils external blueprint).
    application.register_blueprint(external_blueprint)

    login_manager.login_message = None  # don't flash message to user
    # In native AWS we need to stipulate the absolute login URL as per:
    # https://flask-login.readthedocs.io/en/latest/#flask_login.LoginManager.login_view
    login_manager.login_view = os.getenv('DM_LOGIN_URL', 'external.render_login')
    main_blueprint.config = application.config.copy()

    # Metrics initialisation is required to be above CSRF initialisation. See
    # https://github.com/alphagov/gds_metrics_python/issues/4
    gds_metrics.init_app(application)
    csrf.init_app(application)

    # We want to be able to access this function from within all templates
    application.jinja_env.globals["render_question"] = (
        dmcontent.govuk_frontend.render_question
    )

    @application.before_request
    def remove_trailing_slash():
        if request.path.endswith('/'):
            return redirect(request.path[:-1], code=301)

    @application.before_request
    def refresh_session():
        session.permanent = True
        session.modified = True

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)


def config_attrs(config):
    """Returns config attributes from a Config object"""
    p = re.compile('^[A-Z_]+$')
    return filter(lambda attr: bool(p.match(attr)), dir(config))
