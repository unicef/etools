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
      this.url = '/pcatracking/api/v1/partner_organizations';
      this.model = partnerOrganizationModel;
    }
  });
  return partnerOrganizationList;
});
