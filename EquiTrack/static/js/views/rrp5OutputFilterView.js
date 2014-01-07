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
      this.sector_ids = null;
      if (!_.isUndefined(args.unselected_sector_ids)) { // process sector_ids if any
        this.setSectorIDs(args.unselected_sector_ids);
      }
      this.collection = new rrp5OutputList();
      this.collection.fetch({
        success: function() {
          self.collection = self.collection.toJSON();
          self.collection_original = self.collection;
          self.render();
        }
      });
    },
    setSectorIDs: function(sector_ids) {
      this.sector_ids = _.map(sector_ids, function(id) { return parseInt(id); }) 
    },
    template: _.template('\
        <% _.each(data, function(rrp5_output) { %>\
        <div class="input-group">\
          <span class="input-group-addon">\
            <input type="checkbox" name="<%=rrp5_output.rrp5_output_id%>" checked="true" class="rrp5-box">\
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
      if (this.sector_ids != null) {
        this.collection = _.filter(this.collection_original, function(item) {
          return _.indexOf(self.sector_ids, parseInt(item.sector_id)) == -1;
        })
      }
      this.$el.html(this.template(this.collection));
    }
  });
  return rrp5OutputFilterView;
});
  