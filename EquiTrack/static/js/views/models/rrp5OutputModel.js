/*
* model: rrp5OutputModel
*
* Defines model for individual rrp5_output.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var rrp5OutputModel = Backbone.Model.extend({
    urlRoot: '/pcatracking/api/v1/rrp5_output',
    defaults: {
      rrp5_output_id: null,
      sector_id: null,
      code: null,
      name: null
    }
  });
  return rrp5OutputModel;
});
