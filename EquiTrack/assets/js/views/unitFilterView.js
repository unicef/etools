/*
* view: unitFilterView
*
* renders rrp5_output items for map filter
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'unitList'
], function($, _, Backbone, unitList) {
  var unitFilterView = Backbone.View.extend({
    initialize: function(args) {
      var self = this;
      this.collection = new unitList();
      this.parent = args.parent;
      this.collection.fetch({
        success: function() {
          self.render();
        }
      });
    },
    template: _.template('\
        <% _.each(data, function(unit) { %>\
        <div class="input-group">\
          <span class="input-group-addon">\
            <input type="checkbox" name="<%=unit.unit_id%>" checked="true">\
          </span>\
          <div class="form-control" style="background:#fefefe; font-size:12px;"><%=unit.type%></div>\
        </div>\
        <% }); %>\
    ', null, {variable: 'data'}),
    render: function() {
      var self = this;
      this.$el.html(this.template(this.collection.toJSON()));
    }
  });
  return unitFilterView;
});
  