/*
* collection: targetProgressList
*
* Defines collection that holds target progress
* data for the historical bar charts.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'targetProgressModel'
], function($, _, Backbone, targetProgressModel) {
  var targetProgressList = Backbone.Collection.extend({
    initialize: function(attr) {
      this.url = '/pcatracking/api/v1/target_progress/'+attr.target_id+'/'+attr.unit_id;
      this.model = targetProgressModel;
    }
  });
  return targetProgressList;
});
