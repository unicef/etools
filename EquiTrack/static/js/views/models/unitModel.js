/*
* model: unitModel
*
* Defines model for individual unit.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var unitModel = Backbone.Model.extend({
    urlRoot: '/pcatracking/api/v1/unit',
    defaults: {
      unit_id: null,
      type: null
    }
  });
  return unitModel;
});
