/*
* model: locationModel
*
* Defines model for individual sector.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var locationModel = Backbone.Model.extend({
    urlRoot: '/pcatracking/api/v1/location',
    defaults: {
      location_id: null
    }
  });
  return locationModel;
});
