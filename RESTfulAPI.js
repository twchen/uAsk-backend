'use strict';

todomvc.factory("RESTfulAPI", ['$resource', function($resource)
{
  var api = {};
  var baseURL = "http://52.74.132.232:5000/api/";

  api.postResource = $resource(baseURL + "post/:id",
    {id: "@id"},
    {
      update: {
        method: "PUT",
        isArray: false
      }
    }
  );

  api.replyResource = $resource(baseURL + "reply/:id",
    {id: "@id"},
    {
      update: {
        method: "PUT",
        isArray: false
      }
    }
  );

  api.posts = [];
  api.postIdIndexMap = {};
  api.postQuery = function(params) {
    api.posts = api.postResource.query(params);
    for(var i=0; i<api.posts.length; ++i) {
      var post = api.posts[i];
      api.postIdIndexMap[post._id] = i;
      post.reply = api.replyQuery({postId: post._id});
    };
    return api.posts;
  };

  api.replyQuery = function(params) {
    return api.ReplyResource.query(params);
  };

  api.savePost = function(post) {
    api.postResource.save(post, function(post){
      api.posts.splice(0, 0, post);
    });
  };

  api.removePost = function(post) {
    api.posts.splice(api.posts.indexOf(post), 1);
    api.postResource.remove({id: post._id});
  };

  api.updatePost = function(post) {
    // todo: update the post in the local api.posts first
    // update the post on the server
    return api.postResource.update(
    {
      id: post._id
    },
    post
    );
  };

  api.saveReply = function(reply) {
    api.replyResource.save(reply, function(reply){
      var postIndex = api.postIdIndexMap[reply.postId];
      var post = api.posts[postIndex];
      post.reply.push(reply);
    });
  };

  api.removeReply = function(reply) {
    var postIndex = postIdIndexMap[reply.postId];
    var post = api.posts[postIndex];
    post.reply.splice(post.reply.IndexOf(reply), 1);
    api.replyResource.remove({id: reply._id});
  };

  

  return api;
}]);
