/*
* collection: locationList
*
* Defines collection that holds locations
* for the map page.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'locationModel'
], function($, _, Backbone, locationModel) {
  var locationList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/partners/location';
      this.model = locationModel;
    }
  });
  return locationList;
});
