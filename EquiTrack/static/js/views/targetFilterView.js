/*
* view: targetFilterView
*
* renders rrp5_output items for map filter
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'targetList'
], function($, _, Backbone, targetList) {
  var targetFilterView = Backbone.View.extend({
    initialize: function(args) {
      var self = this;
      this.parent = args.parent;
      this.collection = new targetList();
      this.collection.fetch({
        success: function() {
          self.render();
        }
      });
    },
    template: _.template('\
        <% _.each(data, function(target) { %>\
        <div class="input-group">\
          <span class="input-group-addon">\
            <input type="checkbox" name="<%=target.target_id%>" checked="true">\
          </span>\
          <div title="<%=target.name%>" class="form-control" style="background:#fefefe; font-size:12px;"><%=target.name%></div>\
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
        "type": "target",
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
  return targetFilterView;
});
  