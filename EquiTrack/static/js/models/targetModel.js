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
    urlRoot: '/pcatracking/api/v1/target',
    defaults: {
      sector_id: null,
      goal_id: null,
      target_id: null,
      name: null,
      total: null,
      current: null,
      unit_type: null,
      unit_id: null
    }
  });
  return targetModel;

});
