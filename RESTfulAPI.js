'use strict';

todomvc.factory("RESTfulAPI", ['$resource', 'socketFactory', function($resource, socketFactory)
{
    var serverURL = 'http://54.254.251.203:5000';
    //    var serverURL = 'http://52.76.51.251:5000';
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
	api.idPostMap = {};
	api.socket = socketFactory({ioSocket: io.connect(serverURL)});
	api.socket.on('new post', function(data){
		var post = angular.fromJson(data);
		post.reply = [];
		api.posts.splice(0, 0, post);
		api.idPostMap[post._id] = post;
	});

	api.socket.on('del post', function(id){
		var post = api.idPostMap[id];
		api.posts.splice(api.posts.indexOf(post), 1);
		delete api.idPostMap[id];
	});

	api.socket.on('like post', function(data){
		var post = api.idPostMap[data.id];
		post.echo = data.like;
		post.order = data.order;
	});

	api.socket.on('dislike post', function(data){
		var post = api.idPostMap[data.id];
		post.hate = data.dislike;
		post.order = data.order;
	});

	// api.socket.on('new reply', function(data){
	// 	var reply = angular.fromJson(data);
	// 	var post = api.idPostMap(reply.postId);
	// 	post.reply.push(reply);
	// });

	// api.socket.on('del reply', function(data){
	// 	var post = api.idPostMap(data.postId);
	// 	post.forEach(function(reply){
	// 		if(reply._id == data.replyId){
	// 			post.splice(post.indexOf(reply), 1);
	// 		}
	// 	});
	// });

	api.postQuery = function(params){
		api.posts = api.postResource.query(params, function(){
			api.posts.forEach(function(post){
				post.reply = api.replyResource.query({postId: post._id});
				api.idPostMap[post._id] = post;
			});
		});
		api.socket.emit('join', {room: params.roomName});
		api.posts.$add = api.addPost;
		api.posts.$save = api.updatePost;
		api.posts.$remove = api.removePost;
		api.posts.$addReply = api.addReply;
		api.posts.$like = api.likePost;
		api.posts.$dislike = api.dislikePost;
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
		//api.posts.splice(api.posts.indexOf(post), 1);
		api.socket.emit('del post', {room: post.roomName, id: post._id});
		return api.postResource.remove({id: post._id});
	};
	
	api.updatePost = function(post) {
	    // todo: update the post in the local api.posts first
	    // update the post on the server
	    return api.postResource.update({id: post._id}, post);
	};

	api.likePost = function(post) {
		api.socket.emit('like post', {room: post.roomName, id: post._id});
	};

	api.dislikePost = function(post) {
		api.socket.emit('dislike post', {room: post.roomName, id: post._id});
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
