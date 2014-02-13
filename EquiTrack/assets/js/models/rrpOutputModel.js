/*
* model: RRPOutputModel
*
* Defines model for individual rrp_output.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var rrpOutputModel = Backbone.Model.extend({
    urlRoot: '/output',
    defaults: {
      rrp_output_id: null,
      sector_id: null,
      code: null,
      name: null
    }
  });
  return rrpOutputModel;
});
