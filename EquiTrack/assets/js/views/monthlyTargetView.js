/*
* view: montlyTargetView
*
* Defines view that renders bar chart for monthly
* historical data as per target.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'raphael',
  'utils',
  'graphael',
  'gbar',
  'gline'
], function($, _, Backbone, Raphael, utils){
  var montlyTargetView = Backbone.View.extend({
    initialize: function(arguments) {
      this.max = arguments.max;
      this.render();
    },
    events: {
      "click": "clickHandler",
    },
    clickHandler: function(e) {
      Backbone.history.navigate('target_pca_share/'+this.model.target_id+'/'+this.model.unit_id+'/'+this.model.year+'/'+this.model.month, {trigger: true});
      e.preventDefault();
    },
    render: function() {
      var self = this;

      // get new unique element id
      var element_id = _.uniqueId("raphael-container-");

      // append container for bar chart
      this.$el.append('<div id="'+element_id+'" class="monthly-target-bar"></div>');
      
      // assign element to raphael
      var r = Raphael($('#'+element_id)[0]); // access actual DOM element via [0]

      // draw barchart
      var total_h = Math.round($('#'+element_id).height()*(this.model.total/this.max));
      var height1 = Math.round(this.model.programmed/total_h*100);
      var height2 = Math.round((this.model.current - this.model.programmed)/total_h*100) <= 0 ? 0 : Math.round((this.model.current - this.model.programmed)/total_h*100);
      var height3 = Math.round((this.model.total - height2)/total_h*100);

      // draw bar, starting from a relative point, so that all bars are achored 
      // to the bottom of the respective element
      var chart = r.barchart(0, $('#'+element_id).height()-total_h, 30, total_h, [[height1],[height2],[height3]], {stacked:true, colors: ['#a20000','#26a200','#006ba2']});

      // draw bar part labels. Values stored by the bar object
      // itself are obviously wrong, so have to provide our own
      // data
      var prev_y;
      var values = [
        this.model.programmed,
        this.model.current,
        this.model.total
      ];
      _.each(chart.bars, function(bar, i) {
        var x = bar[0].x+40;
        var y = (Math.abs(bar[0].y-prev_y) < 10) ? bar[0].y+20 : bar[0].y;
        var value = values[i] == 0 ? "" : utils.formatNumber(Number(values[i]));
        r.text(x,y, value).attr("font","12px sans-serif").attr("fill","#000");
        prev_y = bar[0].y;
      });

      // append bar label (month/year)
      this.$el.append('<div class="monthly-target-bar-label">'+utils.getMonth(this.model.month)+'/'+this.model.year+'</div>')
    }
  });
  return montlyTargetView;
});