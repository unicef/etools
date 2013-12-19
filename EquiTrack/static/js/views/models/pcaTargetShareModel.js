/*
* model: pcaTargetShareModel
*
* Defines model for holding PCA data per month.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone, pcaTargetProgressList, targetModel){
  var pcaTargetShareModel = Backbone.Model.extend({
    initialize: function(args) {
      var self = this;
      this.url = '/pcatracking/api/v1/pca_target_progress/'+args.target_id+'/'+args.unit_id+'/'+args.year+'/'+args.month;
      this.parent = args.parent;
      this.on('sync', this._calcProgrammed, this);
      this.programmed = 0;
    },
    _calcProgrammed: function() {
      var p = 0;
      _.each(this.attributes.pcas, function(pca) {
        p += parseInt(pca.total);
      });
      this.programmed = p;
    }
  });
  return pcaTargetShareModel;
});