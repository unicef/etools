/*
* collection: rrp5OutputList
*
* Defines collection that holds all sectors
* for the sectors page.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'rrp5OutputModel'
], function($, _, Backbone, rrp5OutputModel) {
  var rrp5OutputList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/pcatracking/api/v1/rrp5_outputs';
      this.model = rrp5OutputModel;
    }
  });
  return rrp5OutputList;
});
