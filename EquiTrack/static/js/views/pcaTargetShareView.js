/*
* view: pcaTargetShareView
*
* Defines the view rendering a pie chart
* for visualising PCA share of a programmed 
* target status.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'router',
  'utils',
  'pcaTargetShareModel',
  'bootstrap',
  'gpie'
], function($, _, Backbone, router, utils, pcaTargetShareModel){
  var pcaTargetShareView = Backbone.View.extend({
    initialize: function(arguments) {
      var self = this;
      this.model = new pcaTargetShareModel({
        "target_id": arguments.target_id,
        "unit_id": arguments.unit_id,
        "year": arguments.year,
        "month": arguments.month
      });
      this.model.fetch({
        success: function() {
          self.render();
        }
      });
    },
    handleModalClose: function (route) {
      $('#modal-window').off(); // remove events
      $('#modal-window').on('hidden.bs.modal', function() { // add new event (DUPLICATION!!) to remove modal events after its hidden
        $(this).off();
        $(this).remove();
      });      
      $('#modal-window').modal('hide'); // hide modal
      Backbone.history.navigate(route, {trigger: true});
      this.remove();
    },
    template: _.template('\
      <div class="modal fade" id="modal-window">\
        <div class="modal-dialog">\
          <div class="modal-content">\
            <div class="modal-header">\
              <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>\
              <h4 id="modal-title" class="modal-title"><%= data.target_name%></h4>\
              <p>Spread between PCAs for <%= data.month%> <%= data.year%></p>\
            </div>\
            <div id="modal-body" class="modal-body">\
              <div id="modal-piechart"></div>\
              <div id="modal-info" style="display:none;"></div>\
            </div>\
            <div class="modal-footer">\
              <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>\
            </div>\
          </div>\
        </div>\
      </div>\
    ', null, {variable: 'data'}),
    render: function() {
      var self = this;

      // write modal into container
      var data = {
        "target_name": this.model.attributes.target_name,
        "month": utils.getMonth(this.model.attributes.month),
        "year": this.model.attributes.year
      }
      $('body').append(this.template(data));

      // show modal window
      $('#modal-window').modal();
      
      // ensure that modal and its events are removed when closed
      $('#modal-window').on('hidden.bs.modal', function() {
        $(this).off();
        $(this).remove();
      });

      // attach event handler for closing modal
      $('#modal-window').bind('hide.bs.modal', function(e) { 
        self.handleModalClose('target_progress/'+self.model.attributes.target_id+'/'+self.model.attributes.unit_id);
      });

      this.renderPie();

    },
    renderPie: function() {
      var self = this;
      if (!$('#modal-piechart').width() > 0) {
        setTimeout(function() { self.renderPie() },10);
        return;
      }

      // sort values in pcas array
      var pcas = _.sortBy(this.model.attributes.pcas, function(item) {
        return item.total;
      });
      
      // draw pie chart
      var paper = Raphael($('#modal-piechart')[0]);
      var pie = paper.piechart(
        150, // pie center x coordinate
        150, // pie center y coordinate
        130,  // pie radius
        _.map(_.pluck(pcas, 'total'), function(item) { return parseInt(item); }), // returns a simple array for the pca totals as values
        {
          legend: _.pluck(pcas, 'number')
        }
      );          
      pie.hover(function(e) {
        if (! _.isUndefined(self.timeout)) clearTimeout(self.timeout);
        $('#modal-info').show('fade');
        this.sector.animate({ transform: 's1.1 1.1 ' + this.cx + ' ' + this.cy }, 200, "bounce");
        $('#modal-info').html('\
          <h4>'+this.label[1].attrs["text"]+'</h4>\
          <p>Number of beneficiaries: '+this.value.value+'</p>\
          <p>Percentage share: '+Math.round(parseInt(this.value.value)/self.model.programmed*100)+'%</p>\
        ');
      }, function() {
        self.timeout = setTimeout(function() { $('#modal-info').hide('fade') }, 2000);
        this.sector.animate({ transform: 's1 1 ' + this.cx + ' ' + this.cy }, 200, "bounce");
      });

      // if there were no targets, print message to modal window
      if (pcas.length == 0) {
        $('#modal-body').html('<p>Could not find any PCA data related to this target!</p>');
      }
    }
  });
  return pcaTargetShareView;
});