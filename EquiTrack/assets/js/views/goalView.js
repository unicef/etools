/*
* view: goalView
*
* Defines the view rendering a goal using
* Bootstrap Modal box
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'router',
  'goalModel',
  'cumulativeTargetView',
  'utils',
  'cumulativeKeyView',
  'bootstrap'
], function($, _, Backbone, router, goalModel, cumulativeTargetView, utils, cumulativeKeyView){
  var goalView = Backbone.View.extend({
    initialize: function(arguments) {
      var self = this;
      this.goal_id = arguments.id;
      this.model = new goalModel({
        id: this.goal_id
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
              <h4 id="modal-title" class="modal-title">Modal title</h4>\
              <hr />\
              <div id="cumulative-key"></div>\
            </div>\
            <div id="modal-body" class="modal-body"></div>\
            <div class="modal-footer">\
              <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>\
            </div>\
          </div>\
        </div>\
      </div>\
    '),
    render: function() {
      var self = this

      // write modal into container      
      $('body').append(this.template());
          
      // loop through goal.targets and create appropriate views
      _.each(self.model.attributes.targets, function(target) {

        // create element and assign it as cumulativeTargetView.el
        var element_id = _.uniqueId("sector-block-container-"); // get new unique element id for our div
        $('#modal-body').append('<div id="'+element_id+'" class="sector-block-container"></div>'); // create element and append to modal-body
      
        // create cumulativeTargetView and assign its corresponding db id
        // and newly created div as its el
        new cumulativeTargetView({
          "parent": self,
          "target": target,
          "el": $('#'+element_id)
        });
      });

      // if there were no targets, print message to modal window
      if (utils.isEmpty($('#modal-body'))) {
        $('#modal-body').html('<p>This goal currently has no targets in the system!</p>');
      }

      // print model name to modal title
      $('#modal-title').html(this.model.attributes.name);

      this.cumulativeKeyView = new cumulativeKeyView({
        el: $('#cumulative-key')
      });

      // show modal window
      $('#modal-window').modal();

      // ensure that modal and its events are removed when closed
      $('#modal-window').on('hidden.bs.modal', function() {
        $(this).off();
        $(this).remove();
      });

      // attach event handler for closing modal
      $('#modal-window').bind('hide.bs.modal', function(e) { 
        self.handleModalClose('/sectors'); 
      });
    }
  });
  return goalView;
});