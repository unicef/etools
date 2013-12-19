/*
* view: rrp5OutputFilterView
*
* renders rrp5_output items for map filter
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'rrp5OutputList'
], function($, _, Backbone, rrp5OutputList) {
  var rrp5OutputFilterView = Backbone.View.extend({
    initialize: function(args) {
      var self = this;
      this.parent = args.parent;
      this.collection = new rrp5OutputList();
      this.collection.fetch({
        success: function() {
          self.render();
        }
      });
    },
    template: _.template('\
        <% _.each(data, function(rrp5_output) { %>\
        <div class="input-group">\
          <span class="input-group-addon">\
            <input type="checkbox" name="<%=rrp5_output.rrp5_output_id%>" checked="true">\
          </span>\
          <div class="form-control" style="background:#fefefe; font-size:12px;"><%=rrp5_output.name%></div>\
        </div>\
        <% }); %>\
    ', null, {variable: 'data'}),
    events: {
      "click input": "clickHandler",
    },
    clickHandler: function(e) {
      var ele = $(e.target);
      var checked = ele.prop('checked') ? true : false;
      var name = ele.attr('name');
      this.parent.filterCollection({
        "type": "rrp5_output",
        "id": name,
        "checked": checked
      });
      this.parent.map.render();
    },
    render: function() {
      var self = this;
      this.$el.html(this.template(this.collection.toJSON()));
    }
  });
  return rrp5OutputFilterView;
});
  