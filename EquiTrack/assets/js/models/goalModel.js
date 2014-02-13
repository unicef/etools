/*
* model: goalModel
*
* Defines model for holding goalData.
*/
define([
  // These are path alias that we configured in our bootstrap
  'jquery',     // lib/jquery/jquery
  'underscore', // lib/underscore/underscore
  'backbone'    // lib/backbone/backbone
], function($, _, Backbone){
  var goalModel = Backbone.Model.extend({
    urlRoot: '/pcatracking/api/v1/goal',
    defaults: {
      goal_id: null,
      sector_id: null,
      name: null, 
      description: null
    }
  });
  return goalModel;
});
