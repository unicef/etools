/*
* model: gatewayModel
*
* Defines model for individual gateway.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var gatewayModel = Backbone.Model.extend({
    urlRoot: '/pcatracking/api/v1/gateway',
    defaults: {
      gateway_id: null,
      name: null
    }
  });
  return gatewayModel;
});
