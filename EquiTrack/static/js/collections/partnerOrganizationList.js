/*
* collection: partnerOrganizationList
*
* Defines collection that holds all sectors
* for the sectors page.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'partnerOrganizationModel'
], function($, _, Backbone, partnerOrganizationModel) {
  var partnerOrganizationList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/partner';
      this.model = partnerOrganizationModel;
    }
  });
  return partnerOrganizationList;
});
