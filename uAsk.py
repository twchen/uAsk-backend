from flask import Flask, request
from flask.ext.restful import Api, Resource, reqparse
from flask.ext.pymongo import PyMongo

app = Flask(__name__)
api = Api(app)

# use MongoDB
app.config['MONGO_DBNAME'] = 'questionroom'
mongo = PyMongo(app)

class BasePostAPI(Resource):
	def __init__(self, required):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('room_name', type=str, required=required, location='json')
		self.reqparse.add_argument('wholeMsg', type=str, required=required, location='json')
		self.reqparse.add_argument('head', type=str, required=required, location='json')
		self.reqparse.add_argument('headLastChar', type=str, required=required, location='json')
		self.reqparse.add_argument('desc', type=str, required=required, location='json')
		self.reqparse.add_argument('completed', type=bool, required=required, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=required, location='json')
		self.reqparse.add_argument('tags', type=list, default=[], location='json')
		self.reqparse.add_argument('echo', type=int, required=required, location='json')
		self.reqparse.add_argument('dislike', type=int, required=required, location='json')
		self.reqparse.add_argument('replies', type=list, default=[], location='json')
		super(self.__class__, self).__init__()

# operation on all posts
class PostListAPI(BasePostAPI):
	def __init__(self):
		super(self.__class__, self).__init(required=True)

	# get all posts 
	def get(self):
		# get room_name from the parameter list, default 'all'
		room_name = request.args.get('room_name', 'all')
		sort_by = request.args.get('sort_by', 'echo') # echo means numOfLikes
		order = request.args.get('order', 1, type=int)
		limit = request.args.get('limit', 10000, type=int)
		return mongo.db.post.find(
			{
				$query: {'room_name': room_name},
				$orderby: {sort_by: order}
			}
		).limit(limit)

	# create new post
	def post(self):
		args = self.reqparse.parse_args()
		mongo.db.post.insert(args)
		# if inserted successfully, return last inserted document
		return mongo.db.post.find().sort({'_id': -1}).limit(1)

# operations on one post
class PostAPI(BasePostAPI):
	def __init__(self):
		super(self.__class__, self).__init(required=False)

	# get post with id
	def get(self, id):
		return mongo.db.post.find({'_id': id})

	# update post with id
	def put(self, id):
		post = mongo.db.post.find({'_id': id})
		if len(post) == 0:
			abort(404)
		post = post[0]
		args = self.reqparse.parse_args()
		for k, v in args.iteritems():
			if v != None:
				post[k] = v
		mongo.db.post.insert(post)
		return post

	# delete post with id
	def delete(self, id):
		ret = mongo.db.post.remove({'_id': id})
		if len(ret) == 1: # delete successfully
			return {}
		else
			return {'delete_result': 'failed'}

class ReplyListAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=True, location='json')
		super(self.__class__, self).__init__()

	def get(self, post_id):
		return mongo.db.post.find({'_id': post_id}, {'replies': 1})

	def post(self, post_id):
		args = self.reqparse.parse_args()
		post = mongo.db.post.find({'_id': post_id}, {'replies': 1})
		if len(post) < 1:
			abort(400)
		post = post[0]
		post['replies'].append(args)
		return args

class ReplyAPI(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('wholeMsg', type=str, required=True, location='json')
		self.reqparse.add_argument('timestamp', type=str, required=True, location='json')
		super(self.__class__, self).__init__()

	def get(self, post_id, reply_id):
		post = mongo.db.post.find({'_id': post_id}, {'replies': 1})
		if len(post) < 0:
			abort(404)
		post = post[0]
		for reply in post['replies']:
			if reply['timestamp'] == reply_id:
				return reply
		abort(404)

	def put(self, post_id, reply_id):
		reqparser = reqparse.RequestParser()
		reqparser.add_argument('wholeMsg', type=str, required=True, location='json')
		args = reqparser.parse_args()
		post = mongo.db.post.find({'_id': post_id}, {'replies': 1})
		if len(post) < 0:
			abort(404)
		post = post[0]
		for reply in post['replies']:
			if reply['timestamp'] == reply_id:
				reply['wholeMsg'] = args['wholeMsg']
			return reply
		abort(404)

	def delete(self, post_id, reply_id):
		post = mongo.db.post.find({'_id': post_id}, {'replies': 1})
		if len(post) < 0:
			abort(404)
		post = post[0]
		for i in xrange(0, len(post['replies'])):
			if post['replies']['timestamp'] = reply_id:
				post['replies'].pop(i)
				return {}
		abort(404)

api.add_resource(PostListAPI, '/api/posts', endpoint='posts')
api.add_resource(PostAPI, '/api/post/<int:id>', endpoint='post')
api.add_resource(ReplyListAPI, '/api/post/<int:post_id>/replies', endpoint='replies')
api.add_resource(ReplyAPI, '/api/post/<int:post_id>/reply/<int:reply_id>', endpoint='reply')

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')
