/*
* view: goalLinkView
*
* Defines the view rendering a single goal
* link for a sector.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'router'
], function($, _, Backbone, router){
  var goalLinkView = Backbone.View.extend({
    initialize: function() {
      this.render();
    },
    template: _.template('\
      <li>\
        <a href="#"><%= data.name%></a>\
      </li>\
    ', null, {variable: 'data'}),
    events: {
      "click a": "clickHandler",
    },
    clickHandler: function(e) {
      Backbone.history.navigate('/goal/'+this.model.goal_id, {trigger: true});
      e.preventDefault();
    },
    render: function() {
      this.$el.html(this.template(this.model));
      return this;
    }
  });
  return goalLinkView;

});
