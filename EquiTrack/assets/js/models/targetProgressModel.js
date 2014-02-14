/*
* model: targetProgressModel
*
* Defines model for holding data per month fetched
* at collection level by targetProgressList.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var targetProgressModel = Backbone.Model.extend({
    defaults: {
      unit_id: null,
      unit_type: null,
      target_id: null,
      total: null, 
      current: null, 
      programmed: null, 
      year: null,
      month: null
    }
  });
  return targetProgressModel;
});
