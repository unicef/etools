/*
* model: targetModel
*
* Defines model for holding targetData.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var targetModel = Backbone.Model.extend({
    urlRoot: '/target',
    defaults: {
      sector_id: null,
      target_id: null,
      name: null,
      total: null,
      unit_type: null,
      unit_id: null
    }
  });
  return targetModel;

});
