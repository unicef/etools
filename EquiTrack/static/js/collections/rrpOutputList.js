/*
* collection: rrpOutputList
*
* Defines collection that holds all sectors
* for the sectors page.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'rrpOutputModel'
], function($, _, Backbone, rrpOutputModel) {
  var rrpOutputList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/output';
      this.model = rrpOutputModel;
    }
  });
  return rrpOutputList;
});
