'use strict'
var app = require('express')();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var mongo = require('mongodb').MongoClient;
var ObjectID = require('mongodb').ObjectID;
var assert = require('assert');
var url = 'mongodb://localhost:27017/questionroom';


var findReplies = function(db, postId, callback) {
	db.collection('replies').find({'postId': postId}, function(err, result) {
		assert.equal(err, null);
		callback(result);
	});
};

var findPostById = function(db, id, callback) {
	db.collection('posts').findOne({'_id': id}, function(err, result) {
		assert.equal(err, null);
		callback(result);
	});
};

var updatePost = function(db, post, callback) {
	db.collection('posts').updateOne({_id: post._id}, {$set: post}, function(err, result) {
		assert.equal(err, null);
		callback(result);
	});
};

io.on('connection', function(socket){
	socket.on('join', function(room){
		socket.join(room);
		console.log('client joined room: ' + room);
	});
	socket.on('new post', function(data){
		// new post is only sent to other clients, not including the original emitter
		socket.to(data.room).emit('new post', data.id);
	});
/*
	socket.on('new post', function(data){
		var postId = new ObjectID.createFromHexString(data)
		mongo.connect(url, function(err, db) {
			assert.equal(err, null);
			findPostById(db, postId, function(post) {
				findReplies(db, postId, function(replies) {
					post.reply = replies;
					io.sockets.in(post.roomName).emit('new post', post);
					db.close();
				});
			});
		});
	});
*/
	socket.on('del post', function(data){
		io.sockets.in(data.room).emit('del post', data.id);
	});
	socket.on('like post', function(data){
		var postId = new ObjectID.createFromHexString(data)
		mongo.connect(url, function(err, db) {
			assert.equal(err, null);
			findPostById(db, postId, function(post) {
				post.echo += 1;
				post.order -= 1;
				io.sockets.in(post.roomName).emit('like post', {id: post._id, like: post.echo, order: post.order});
				updatePost(db, post, function() {
					db.close();
				});
			});
		});
	});

	socket.on('dislike post', function(data){
		var postId = new ObjectID.createFromHexString(data)
		mongo.connect(url, function(err, db) {
			assert.equal(err, null);
			findPostById(db, postId, function(post) {
				post.hate += 1;
				post.order += 1;
				io.sockets.in(post.roomName).emit('dislike post', {id: post._id, dislike: post.hate, order: post.order});
				updatePost(db, post, function() {
					db.close();
				});
			});
		});
	});
});


http.listen(3000, function(){
	console.log('listening on localhost:3000');
});
