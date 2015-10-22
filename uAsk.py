from flask import Flask, request, abort
from flask.ext.restful import Api, Resource, reqparse
from flask.ext.pymongo import PyMongo
from bson.objectid import ObjectId

from flask import make_response
from bson import json_util

app = Flask(__name__)
api = Api(app)

# customized json dumper for mongodb objects
def output_json(obj, code, headers=None):
	"""
	This is needed because we need to use a custom JSON converter
	that knows how to translate MongoDB types to JSON.
	"""
	resp = make_response(json_util.dumps(obj), code)
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
		self.reqparse.add_argument('completed', type=bool, required=required, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=required, location='json')
		self.reqparse.add_argument('tags', type=list, default=[], location='json')
		self.reqparse.add_argument('echo', type=int, required=required, location='json')
		self.reqparse.add_argument('dislike', type=int, required=required, location='json')
		#super(self.__class__, self).__init__()

class PostListAPI(BasePostAPI):
	def __init__(self):
		super(self.__class__, self).__init__(True)

	# get all posts 
	def get(self):
		# get roomName from the parameter list, default 'all'
		roomName = request.args.get('roomName', 'all')
		sortBy = request.args.get('sortBy', 'echo') # echo means numOfLikes
		order = request.args.get('order', 1, type=int)
		limit = request.args.get('limit', 10000, type=int)
		query = {} if roomName == 'all' else {'roomName': roomName}
		cursor = mongo.db.post.find(query).sort([(sortBy, order)]).limit(limit)
		return cursor

	# create a new post
	def post(self):
		# check whether the data is valid
		args = self.reqparse.parse_args()
		mongo.db.post.insert(args)
		# if inserted successfully, return last inserted document
		cursor = mongo.db.post.find().sort([('_id', -1)]).limit(1)
		return cursor[0]

# operations on one post
class PostAPI(BasePostAPI):
	def __init__(self):
		super(self.__class__, self).__init__(required=False)

	# get post with id
	def get(self, id):
		post = mongo.db.post.find_one({'_id': id})
		if not post:
			abort(404)
		return post

	# update post with id
	def put(self, id):
		post = mongo.db.post.find_one({'_id': id})
		if not post:
			abort(404)
		args = self.reqparse.parse_args()
		for k, v in args.iteritems():
			if v != None:
				post[k] = v
		mongo.db.post.update_one({'_id': post['_id']}, {'$set': post})
		return post

	# delete post with id
	def delete(self, id):
		ret = mongo.db.post.remove({'_id': id})
		return ret

class ReplyListAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('postID', type=ObjectId, required=True, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=True, location='json')
		super(self.__class__, self).__init__()

	def get(self):
		postId = request.args.get('postId', type=str)
		postId = ObjectId(postId)
		cursor = mongo.db.reply.find({'postId': postId}).sort([('timestamp', 1)])
		return cursor

	def post(self):
		args = self.reqparse.parse_args()
		mongo.db.reply.insert(args)
		cursor = mongo.db.reply.find().sort([('_id', -1)]).limit(1)
		return cursor[0]

class ReplyAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('postID', type=ObjectId, required=True, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=False, location='json')
		super(self.__class__, self).__init__()

	def get(self, id):
		reply = mongo.db.reply.find_one({'_id': id})
		if not reply:
			abort(404)
		else:
			return reply

	def put(self, id):
		args = self.reqparse.parse_args()
		reply = mongo.db.reply.find_one({'_id': id})
		if not reply:
			abort(404)
		for k, v in args.iteritems():
			if v != None:
				reply[k] = v
		mongo.db.reply.update_one({'_id': reply['_id']}, {'$set': reply})
		return reply

	def delete(self, id):
		reply = mongo.db.reply.find({'_id': id})
		if not reply:
			abort(404)
		ret = mongo.db.reply.remove({'_id': id})
		return ret

api.add_resource(PostListAPI, '/api/posts', endpoint='posts')
api.add_resource(PostAPI, '/api/post/<ObjectId:id>', endpoint='post')
api.add_resource(ReplyListAPI, '/api/replies', endpoint='replies')
api.add_resource(ReplyAPI, '/api/reply/<ObjectId:id>', endpoint='reply')

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')
