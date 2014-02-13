/*
* view: sectorView
*
* Defines the view for displaying individual 
* sector on sectors page.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone) {
  var sectorView = Backbone.View.extend({
    initialize: function() {
      this.render();
    },
    template: _.template('\
      <div class="sector-container">\
        <div class="sector-top" style="border-color: #555; background: #555;">\
          <div class="heading"><%= data.name %></div>\
        </div>\
        <div class="sector-bottom" style="border-color: #555;">\
          <div class="content">\
            <ul id="sector-<%= data.sector_id%>-goals">\
            </ul>\
          </div>\
        </div>\
      </div>\
    ', null, {variable: 'data'}),
    render: function() {
      this.$el.html(this.template(this.model));
    }
  });
  return sectorView;
});
