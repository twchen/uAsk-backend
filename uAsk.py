from flask import Flask, request, abort, jsonify
from flask.ext.restful import Api, Resource, reqparse
from flask.ext.pymongo import PyMongo
from flask.ext.cors import CORS
from bson.objectid import ObjectId

from flask import make_response
import json_util

app = Flask(__name__)
api = Api(app)


# allow CORS for all domains on all routes.
CORS(app)

# customized json dumper for mongodb objects
def output_json(obj, code, headers=None):
	"""
	This is needed because we need to use a custom JSON converter
	that knows how to translate MongoDB types to JSON.
	"""
	resp = make_response(json_util.dumps(obj), code)
	# not needed any more. CORS will take care of these headers
	# resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
	# resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
	# resp.headers['Access-Control-Allow-Origin'] = '*'
	resp.headers.extend(headers or {})
	return resp
DEFAULT_REPRESENTATIONS = {'application/json': output_json}
api.representations = DEFAULT_REPRESENTATIONS

# use MongoDB
app.config['MONGO_DBNAME'] = 'questionroom'
mongo = PyMongo(app)

class UserAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('username', type=str, required=True, location='json')
		self.reqparse.add_argument('password', type=str, required=True, location='json')
		super(UserAPI, self).__init__()

	def post(self):
		args = self.reqparse.parse_args() # check whether json has valid object, no _id, only username and password, not less than, more will be deleted
		username = args['username'] #args is what I get
		passwd = args['password']

		option = request.args.get('option', 'login')
		if option == 'signup':#qy send a login json, I have to check and tell him whether the username exists already. If exist, return false; Else, insert and return true.
			cursor = mongo.db.users.find_one({'username':username})
			if cursor:
				return jsonify({'result': False})#username already exists
			else:
				mongo.db.users.insert(args)
				return jsonify({'result': True})

		elif option == 'login':#qy send a login json, I have to check and tell him whether login successfully
			cursor = mongo.db.users.find_one({'username':username , 'password' :passwd})
			if cursor:
				return jsonify({'result': True})#login success
			else:
				return jsonify({'result': False})

class BasePostAPI(Resource):
	def __init__(self, required):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('roomName', type=str, required=required, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=required, location='json')
		self.reqparse.add_argument('head', type=str, required=required, location='json')
		self.reqparse.add_argument('headLastChar', type=str, required=required, location='json')
		self.reqparse.add_argument('desc', type=str, required=required, location='json')
		self.reqparse.add_argument('timestamp', type=int, required=required, location='json')
		self.reqparse.add_argument('username', type=str, default='Anonymous', location='json')
		self.reqparse.add_argument('anonymous', type=bool, default=False, location='json')
		self.reqparse.add_argument('linkedDesc', type=str, default='', location='json')
		self.reqparse.add_argument('completed', type=bool, default=False, location='json')
		self.reqparse.add_argument('tags', type=str, default='', location='json')
		self.reqparse.add_argument('echo', type=int, default=0, location='json')
		self.reqparse.add_argument('hate', type=int, default=0, location='json')
		self.reqparse.add_argument('preMsg', type=str, default='<pre> </pre>', location='json')
		self.reqparse.add_argument('new_reply', type=str, default='', location='json')
		self.reqparse.add_argument('order', type=int, default=0, location='json')
		self.reqparse.add_argument('image', type=str, default='', location='json')
		super(BasePostAPI, self).__init__()

class PostListAPI(BasePostAPI):
	def __init__(self):
		super(PostListAPI, self).__init__(True)

	# get all posts 
	def get(self):
		# get roomName from the parameter list, default 'all'
		roomName = request.args.get('roomName', 'all')
		sortBy = request.args.getlist('sortBy', type=str)
		order = request.args.getlist('order', type=int)
		sortList = list(zip(sortBy, order))
		if not sortList:
			sortList = [('order', 1)]
		limit = request.args.get('limit', 10000, type=int)
		startTime = request.args.get('startTime', type=int)
		endTime = request.args.get('endTime', type=int)
		searchContent = request.args.get('content', type=str)
		username = request.args.get('username', type=str)
		query = []
		if roomName != 'all':
			query.append({'roomName': roomName})
		if startTime:
			query.append({'timestamp': {'$gte': startTime}})
		if endTime:
			query.append({'timestamp': {'$lte': endTime}})
		if searchContent:
			query.append({'wholeMsg': {'$regex': '.*' + searchContent + '.*'}})
		if username:
			query.append({'username': username})
		query = {'$and': query} if query else {}
		cursor = mongo.db.posts.find(query).sort(sortList).limit(limit)
		posts = list(cursor)
		for post in posts:
			post['reply'] = mongo.db.replies.find({'postId': post['_id']}).sort([('timestamp', 1)])
		return make_response(json_util.dumps(posts), 200)

	# create a new post
	def post(self):
		# check whether the data is valid
		args = self.reqparse.parse_args() # exclude args not in the parser
		#args = request.get_json(force=True) # allow all args
		mongo.db.posts.insert(args)
		# if inserted successfully, return last inserted document
		post = mongo.db.posts.find().sort([('_id', -1)]).limit(1)[0]
		post['reply'] = []
		return post

# operations on one post
class PostAPI(BasePostAPI):
	def __init__(self):
		super(PostAPI, self).__init__(False)

	# get post with id
	def get(self, id):
		post = mongo.db.posts.find_one({'_id': id})
		if not post:
			abort(404)
		post['reply'] = mongo.db.replies.find({'postId': post['_id']}).sort([('timestamp', 1)])
		return post

	# update post with id
	def put(self, id):
		username = request.args.get('username')
		if not username:
			return make_response(jsonify({"error": "login required"}), 401)
		post = mongo.db.posts.find_one({'_id': id, 'username': username})
		if not post:
			abort(404)
		args = self.reqparse.parse_args()
		for k, v in args.iteritems():
			if v != None:
				post[k] = v
		mongo.db.posts.update_one({'_id': id}, {'$set': post})
		post['reply'] = mongo.db.replies.find({'postId': post['_id']}).sort([('timestamp', 1)])
		return post

	# delete post with id
	def delete(self, id):
		username = request.args.get('username')
		if not username:
			return make_response(jsonify({"error": "login required"}), 401)
		ret = mongo.db.posts.remove({'_id': id, 'username': username})
		if ret['ok'] == 1 and ret['n'] == 1:
			mongo.db.replies.remove({'postId': id})
			return jsonify({"result": True})
		else:
			return jsonify({"result": False})

class ReplyListAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('postId', type=ObjectId, required=True, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=int, required=True, location='json')
		self.reqparse.add_argument('username', type=str, default='Anonymous', location='json')
		self.reqparse.add_argument('anonymous', type=bool, default=False, location='json')
		super(ReplyListAPI, self).__init__()

	def get(self):
		postId = request.args.get('postId', type=ObjectId)
		username = request.args.get('username', type=str)
		# allow null postId, i.e. get all replies
		query = {}
		if postId:
			query['postId'] = postId
		if username:
			query['username'] = username
		cursor = mongo.db.replies.find(query).sort([('timestamp', 1)])
		return cursor

	def post(self):
		args = self.reqparse.parse_args()
		mongo.db.replies.insert(args)
		cursor = mongo.db.replies.find().sort([('_id', -1)]).limit(1)
		return cursor[0]

class ReplyAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('postId', type=ObjectId, required=False, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=False, location='json')
		super(ReplyAPI, self).__init__()

	def get(self, id):
		reply = mongo.db.replies.find_one({'_id': id})
		if not reply:
			abort(404)
		else:
			return reply

	def put(self, id):
		username = request.args.get('username')
		if not username:
			return make_response(jsonify({"error": "login required"}), 401)
		args = self.reqparse.parse_args()
		reply = mongo.db.replies.find_one({'_id': id, 'username': username})
		if not reply:
			abort(404)
		for k, v in args.iteritems():
			if v != None:
				reply[k] = v
		mongo.db.replies.update_one({'_id': id}, {'$set': reply})
		return reply

	def delete(self, id):
		username = request.args.get('username')
		if not username:
			return make_response(jsonify({"error": "login required"}), 401)
		ret = mongo.db.replies.remove({'_id': id, 'username': username})
		if ret['ok'] == 1 and ret['n'] == 1:
			return jsonify({"result": True})
		else:
			return jsonify({"result": False})

api.add_resource(PostListAPI, '/api/posts', endpoint='posts')
api.add_resource(PostAPI, '/api/posts/<ObjectId:id>', endpoint='post')
api.add_resource(ReplyListAPI, '/api/replies', endpoint='replies')
api.add_resource(ReplyAPI, '/api/replies/<ObjectId:id>', endpoint='reply')
api.add_resource(UserAPI, '/api/users', endpoint='users')

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=5000)
	#socketio.run(app, host='0.0.0.0')

