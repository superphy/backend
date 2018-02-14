from pymongo import MongoClient
from config import MONGO_URI, MONGO_DBNAME, MONGO_ACCOUNTSCOLLECTION

# Connection to MongoDB
client = MongoClient(MONGO_URI, connect=False)
# Access Spfy's DB in MongoDB
db = client[MONGO_DBNAME]
# Access the collection of accounts information from Spfy's DB
collection_accounts = db[MONGO_ACCOUNTSCOLLECTION]


def mongo_update(uid, json=None, key='store'):
    """By default, updates the 'store' document in the accounts collection.
    """
    if json is None:
        json = []
    collection_accounts.update_one({'_id': uid}, {'$set': {key: json}}, upsert=True)


def mongo_find(uid, key='store'):
    doc = collection_accounts.find_one({'_id': uid})
    return doc[key]
