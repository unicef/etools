/*
* view: sectorFilterView
*
* renders sector items for map filter
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'sectorList'
], function($, _, Backbone, sectorList) {
  var sectorFilterView = Backbone.View.extend({
    initialize: function(args) {
      var self = this;
      this.parent = args.parent;
      this.collection = new sectorList();
      this.collection.fetch({
        success: function() {
          self.render();
        }
      });
    },
    template: _.template('\
        <% _.each(data, function(sector) { %>\
        <div class="input-group">\
          <span class="input-group-addon">\
            <input type="checkbox" name="<%=sector.sector_id%>" checked="true" class="sector-box">\
          </span>\
          <div class="form-control" style="background:#fefefe; font-size:12px;"><%=sector.name%></div>\
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
        "type": "sector",
        "id": name,
        "checked": checked
      });
      this.parent.refreshSelectors();
      this.parent.map.render();
    },
    render: function() {
      var self = this;
      this.$el.html(this.template(this.collection.toJSON()));
    }
  });
  return sectorFilterView;
});
  