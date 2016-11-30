from flask import Flask, request, abort
from flask.ext.restful import Api, Resource, reqparse
from flask.ext.pymongo import PyMongo
from flask.ext.cors import CORS
from bson.objectid import ObjectId

from flask.ext.socketio import SocketIO, join_room, leave_room

from flask import make_response
import json_util

app = Flask(__name__)
api = Api(app)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

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

class BasePostAPI(Resource):
	def __init__(self, required):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('roomName', type=str, required=required, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=required, location='json')
		self.reqparse.add_argument('head', type=str, required=required, location='json')
		self.reqparse.add_argument('headLastChar', type=str, required=required, location='json')
		self.reqparse.add_argument('desc', type=str, required=required, location='json')
		self.reqparse.add_argument('linkedDesc', type=str, default='', location='json')
		self.reqparse.add_argument('completed', type=bool, default=False, location='json')
		self.reqparse.add_argument('timestamp', type=int, required=required, location='json')
		#self.reqparse.add_argument('tags', type=list, default=[], location='json')
		self.reqparse.add_argument('tags', type=str, default='', location='json')
		self.reqparse.add_argument('echo', type=int, default=0, location='json')
		self.reqparse.add_argument('hate', type=int, default=0, location='json')
		self.reqparse.add_argument('preMsg', type=str, default='<pre> </pre>', location='json')
		self.reqparse.add_argument('new_reply', type=str, default='', location='json')
		self.reqparse.add_argument('order', type=int, default=0, location='json')
		#self.reqparse.add_argument('dislike', type=int, required=required, location='json')
		self.reqparse.add_argument('image', type=str, default='', location='json')
		super(BasePostAPI, self).__init__()

class PostListAPI(BasePostAPI):
	def __init__(self):
		super(PostListAPI, self).__init__(True)

	# get all posts 
	def get(self):
		# get roomName from the parameter list, default 'all'
		roomName = request.args.get('roomName', 'all')
		sortBy = request.args.get('sortBy', 'echo') # echo means numOfLikes
		order = request.args.get('order', 1, type=int)
		limit = request.args.get('limit', 10000, type=int)
		startTime = request.args.get('startTime', type=int)
		endTime = request.args.get('endTime', type=int)
		searchContent = request.args.get('content', type=str)
		query = []
		if roomName != 'all':
			query.append({'roomName': roomName})
		if startTime:
			query.append({'timestamp': {'$gte': startTime}})
		if endTime:
			query.append({'timestamp': {'$lte': endTime}})
		if searchContent:
			query.append({'wholeMsg': {'$regex': '.*' + searchContent + '.*'}})
			print searchContent
		cursor = mongo.db.posts.find({'$and': query}).sort([(sortBy, order)]).limit(limit)
		return cursor

	# create a new post
	def post(self):
		# check whether the data is valid
		args = self.reqparse.parse_args() # exclude args not in the parser
		#args = request.get_json(force=True) # allow all args
		mongo.db.posts.insert(args)
		# if inserted successfully, return last inserted document
		cursor = mongo.db.posts.find().sort([('_id', -1)]).limit(1)
		socketio.emit('new post', json_util.dumps(cursor[0]), room=cursor[0]['roomName'])
		return cursor[0]

# operations on one post
class PostAPI(BasePostAPI):
	def __init__(self):
		super(PostAPI, self).__init__(False)

	# get post with id
	def get(self, id):
		post = mongo.db.posts.find_one({'_id': id})
		if not post:
			abort(404)
		return post

	# update post with id
	def put(self, id):
		post = mongo.db.posts.find_one({'_id': id})
		if not post:
			abort(404)
		args = self.reqparse.parse_args()
		for k, v in args.iteritems():
			if v != None:
				post[k] = v
		mongo.db.posts.update_one({'_id': id}, {'$set': post})
		return post

	# delete post with id
	def delete(self, id):
		ret = mongo.db.posts.remove({'_id': id})
		return ret

class ReplyListAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('postId', type=ObjectId, required=True, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=int, required=True, location='json')
		super(ReplyListAPI, self).__init__()

	def get(self):
		postId = request.args.get('postId', type=ObjectId)
		# allow null postId, i.e. get all replies
		query = {} if not postId else {'postId': postId}
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
		args = self.reqparse.parse_args()
		reply = mongo.db.replies.find_one({'_id': id})
		if not reply:
			abort(404)
		for k, v in args.iteritems():
			if v != None:
				reply[k] = v
		mongo.db.replies.update_one({'_id': id}, {'$set': reply})
		return reply

	def delete(self, id):
		reply = mongo.db.replies.find({'_id': id})
		if not reply:
			abort(404)
		ret = mongo.db.replies.remove({'_id': id})
		return ret

@socketio.on('connect')
def test_connect():
	print 'Client connected'

@socketio.on('join')
def on_join(data):
	room = data['room']
	join_room(room)
	print 'Client joined room ' + room; 

@socketio.on('leave')
def on_leave(data):
	room = data['room']
	leave_room(room)
	print 'Client left room ' + room

@socketio.on('del post')
def on_del_post(data):
	socketio.emit('del post', data['id'], room=data['room'])

@socketio.on('like post')
def on_like_post(data):
	id = ObjectId(data['id'])
	post = mongo.db.posts.find_one({'_id': id})
	if post:
		post['echo'] = post['echo'] + 1
		post['order'] = post['order'] +1
		mongo.db.posts.update_one({'_id': id}, {'$set': post})
		socketio.emit('like post', {
				'id': data['id'],
				'like': post['echo'],
				'order': post['order']
			}, room=data['room'])
	else:
		print "liked post not found"

@socketio.on('dislike post')
def on_dislike_post(data):
	id = ObjectId(data['id'])
	post = mongo.db.posts.find_one({'_id': id})
	if post:
		post['hate'] = post['hate'] + 1
		post['order'] = post['order'] -1
		mongo.db.posts.update_one({'_id': id}, {'$set': post})
		socketio.emit('dislike post', {
				'id': data['id'],
				'dislike': post['hate'],
				'order': post['order']
			}, room=data['room'])
	else:
		print "disliked post not found"

api.add_resource(PostListAPI, '/api/posts', endpoint='posts')
api.add_resource(PostAPI, '/api/posts/<ObjectId:id>', endpoint='post')
api.add_resource(ReplyListAPI, '/api/replies', endpoint='replies')
api.add_resource(ReplyAPI, '/api/replies/<ObjectId:id>', endpoint='reply')

if __name__ == '__main__':
	#app.run(debug=True, host='0.0.0.0')
	socketio.run(app, host='0.0.0.0')

