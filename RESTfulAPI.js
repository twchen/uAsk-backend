'use strict';

todomvc.factory("RESTfulAPI", ['$resource', function($resource)
{
	var serverURL = 'http://52.74.132.232:5000';
	var baseURL = serverURL + '/api/';

	var api = {};

	api.postResource = $resource(baseURL + "posts/:id",
		{id: "@id"},
		{
			update: {
				method: "PUT",
				isArray: false
			}
		}
	);

	api.replyResource = $resource(baseURL + "replies/:id",
		{id: "@id"},
		{
			update: {
				method: "PUT",
				isArray: false
			}
		}
	);

	api.posts = [];
	api.postQuery = function(params){
		api.posts = api.postResource.query(params, function(){
			api.posts.forEach(function(post){
				post.reply = api.replyResource.query({postId: post._id});
			});
		});
		api.posts.$add = api.addPost;
		api.posts.$save = api.updatePost;
		api.posts.$remove = api.removePost;
		api.posts.$addReply = api.addReply;
		return api.posts;
	};

	api.replyQuery = function(params) {
		return api.replyResource.query(params);
	};

	api.addPost = function(post) {
		api.postResource.save(post, function(post){
			post.reply = [];
			//api.posts.splice(0, 0, post);
		});
	};
	
	api.removePost = function(post) {
		post.reply.forEach(function(reply){
			api.replyResource.remove({id: reply._id});
		});
		api.posts.splice(api.posts.indexOf(post), 1);
		return api.postResource.remove({id: post._id});
	};
	
	api.updatePost = function(post) {
	    // todo: update the post in the local api.posts first
	    // update the post on the server
	    return api.postResource.update({id: post._id}, post);
	};

	api.addReply = function(post, reply) {
		return api.replyResource.save(reply, function(reply){
			post.reply.push(reply);
		});
	};

	api.removeReply = function(post, reply) {
		post.reply.splice(post.reply.IndexOf(reply), 1);
		return api.replyResource.remove({id: reply._id});
	};

	return api;
}]);
