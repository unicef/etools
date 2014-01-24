/*
* collection: sectorList
*
* Defines collection that holds all sectors
* for the sectors page.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'sectorModel'
], function($, _, Backbone, sectorModel) {
  var sectorList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/sector';
      this.model = sectorModel;
    }
  });
  return sectorList;
});
