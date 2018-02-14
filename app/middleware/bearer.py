import hashlib
import random
from datetime import datetime
# custom
from middleware.mongo import mongo_update


def generate_token():
    """
    Generates a bearer token for use by the front-end.
    Not actually secure, but suffices for our uses.
    """
    now = datetime.now()
    now = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
    salt = random.randint(100000, 999999)
    seed = "{0}{1}".format(now, salt)
    token = hashlib.sha1(seed).hexdigest()
    return token


def store(token):
    """
    Stores the bearer token to MongoDB.
    """
    # We should add a check for collision, but it's unlikely we'll see any.
    # Add the account to mongo.
    mongo_update(token, 'active', 'status')
    # Create an empty jobs dictionary for the account.
    mongo_update(token)


def bearer():
    token = generate_token()
    store(token)
    return token
