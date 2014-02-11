/*
* view: targetProgressView
*
* Defines view for displaying historical 
* bar chart data for targets.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'targetProgressList',
  'targetModel',
  'monthlyTargetView',
  'monthlyKeyView'
], function($, _, Backbone, targetProgressList, targetModel, monthlyTargetView, monthlyKeyView) {
  var targetProgressView = Backbone.View.extend({
    initialize: function(arguments) {
      var self = this;
      this.target_id = arguments.target_id;
      this.unit_id = arguments.unit_id
      this.collection = new targetProgressList({
        "target_id": this.target_id,
        "unit_id": this.unit_id
      });
      this.collection.fetch({
        success: function() {
          self.render();
          self.targetModel = new targetModel({id: self.target_id});
          self.targetModel.fetch({
            success: function() {
              self.renderHeader();
            }
          });
        }
      });
    },
    template: _.template('\
      <div class="row target-grey">\
        <div id="target-progress-header" class="col-md-12">\
          <div class="row">\
            <div id="target-progress-headline" class="col-md-8"></div>\
            <div id="target-progress-key" class="col-md-4"></div>\
          </div>\
        </div>\
        <div id="target-progress-container" class="col-md-12" style="overflow:auto; overflow-y:hidden; -ms-overflow-y: hidden;"></div>\
      </div>\
    '),
    renderHeader: function() {
      var self = this;
      if (!$('#target-progress-headline').length) {
        setTimeout(function() { self.renderHeader(); },10); // if the element is not yet rendered wait and retry
        return;
      }

      // render header
      $('#target-progress-headline').html('<h1>'+this.targetModel.attributes.name+'</h1>');
      this.monthlyKeyView = new monthlyKeyView({
        el: $('#target-progress-key')
      });

    },
    render: function() {
      var self = this;
      this.$el.html(this.template(this));

      /* 
      * Loop through collection to append views and subviews together
      * to form the bar chart data.
      */
      var bars_container = $('#target-progress-container');
      bars_container.empty();
      var month_with_maximum_total = _.max(this.collection.toJSON(), function(item) { return item.total; }); // get maximum value inside collection
      _.each(this.collection.toJSON(), function(target_progress) {

        // create wrapper container for bar chart's hover effect
        // this is to be passed to monthlyTargetView as its $el
        var element_id = _.uniqueId("target-month-hover-container-");
        bars_container.append('<div id="'+element_id+'" class="target-month-block-hoverer"></div>');


        // create monthly target bar
        var target_view = new monthlyTargetView({
          model: target_progress,
          el: $('#'+element_id),
          max: month_with_maximum_total.total
        });
        bars_container.append(target_view.$el);
      });
    }
  });
  return targetProgressView;
});