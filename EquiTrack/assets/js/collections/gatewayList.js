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
  'gatewayModel'
], function($, _, Backbone, gatewayModel) {
  var gatewayList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/pcatracking/api/v1/gateways';
      this.model = gatewayModel;
    }
  });
  return gatewayList;
});
