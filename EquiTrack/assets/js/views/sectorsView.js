/*
* view: sectorsView
*
* Defines view that renders HTML containers for 
* individual sectors on sectors page. Iterates through
* the sector collection to render sectors through sectorView
* and goalLinkView.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'sectorList',
  'sectorView',
  'goalLinkView'
], function($, _, Backbone, sectorList, sectorView, goalLinkView) {
  var sectorsView = Backbone.View.extend({
    initialize: function() {
      var self = this;
      this.collection = new sectorList();
      this.collection.fetch({
        success: function() {
          self.trimCollection();
          self.render();
        }
      });
    },
    template: _.template('\
      <div class="row">\
        <div id="sector-container-1" class="col-md-6"></div>\
        <div id="sector-container-2" class="col-md-6"></div>\
      </div>\
    '),
    trimCollection: function() {
      this.collection = _.select(this.collection.toJSON(), function(sector) { // if there are no goals, remove it from the collection
        return sector.goals.length > 0;
      });
    },
    render: function() {
      var self = this;
      this.$el.html(this.template());
      var col1 = $('#sector-container-1')
      var col2 = $('#sector-container-2')
      col1.empty();
      col2.empty();

      /* 
      * Loop through collection to append views and subviews together
      * to form the sector list view
      */
      var i = 0;
      _.each(this.collection, function(sector) {

        // create new sector view
        var sector_view = new sectorView({model: sector});

        // append sector view
        if (i % 2) {
          col1.append(sector_view.$el);
        } else {
          col2.append(sector_view.$el);
        }
      
        // calculate the container for goal links
        var goal_link = $('#sector-'+sector.sector_id+'-goals');
      
        // generate goal links via goal view
        _.each(sector.goals, function(goal) {
          var goal_link_view = new goalLinkView({
            model: goal
          });
          goal_link.append(goal_link_view.$el);
        });

        i++;
      });
      return this;
    }
  });
  return sectorsView;
});
  