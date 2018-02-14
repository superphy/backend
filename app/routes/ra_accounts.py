from flask import Blueprint
from middleware.bearer import bearer

bp_ra_accounts = Blueprint('reactapp_accounts', __name__)


@bp_ra_accounts.route('/api/v0/accounts')
def create_account():
    token = bearer()
    return token
