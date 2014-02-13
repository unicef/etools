/*
* view: cumulativeTargetView
*
* Defines view that renders individual target for a goal.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'targetModel',
  'raphael',
  'utils',
  'graphael',
  'gbar'
], function($, _, Backbone, targetModel, Raphael, utils){
  var cumulativeTargetView = Backbone.View.extend({
    initialize: function(arguments) {
      this.parent = arguments.parent;
      this.model = arguments.target;
      this.render();
    },
    events: {
      "click": "clickHandler",
    },
    clickHandler: function(e) {
      this.parent.handleModalClose('target_progress/'+this.model.target_id+'/'+this.model.unit_id);
      e.preventDefault();
      this.remove();
    },
    render: function() {
      var self = this;
      if (!this.$el.width() > 0) {
        setTimeout(function() { self.render() },10);
        return;
      }

      // create container for hover effect
      var element_id = _.uniqueId("sector-hover-container-");
      this.$el.append('<div id="'+element_id+'" class="sector-block-hoverer"></div>');
      var hover_box = $('#'+element_id);

      // create and append element for target name
      hover_box.append('<div class="target-name">'+this.model.name+' - <b>'+this.model.unit_type+'</b></div>');

      // get new unique element id
      element_id = _.uniqueId("raphael-container-");
    
      // append container for bar chart
      hover_box.append('<div id="'+element_id+'" class="target-bar"></div>')

      // assign element to raphael
      var r = Raphael($('#'+element_id)[0]); // access actual DOM element via [0]

      // draw barchart
      var total_w = $('#'+element_id).width();
      var current_w = Math.floor((this.model.current/this.model.total)*total_w);

      // draw barchart
      var chart = r.hbarchart(0, 0, total_w, 30, [[this.model.current],[this.model.total]], {gutter:'-1%', colors: ['#a20000','#26a200','#006ba2']});
      var values = [
        this.model.current,
        this.model.total
      ];
      _.each(chart.bars, function(bar, i) {
        var x = bar[0].x > 70 ? bar[0].x : 70;
        var fill = bar[0].x > 70 ? '#FFFFFF' : "#000000";
        r.text(x-30,bar[0].y, utils.formatNumber(Number(values[i]))).attr("font","12px sans-serif").attr("fill",fill);
      });
    }
  });
  return cumulativeTargetView;
});