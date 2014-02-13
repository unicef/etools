/*
* collection: unitList
*
* Defines collection that holds all sectors
* for the sectors page.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'unitModel'
], function($, _, Backbone, unitModel) {
  var unitList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/pcatracking/api/v1/units';
      this.model = unitModel;
    }
  });
  return unitList;
});
