/*
* view: partnerOrganizationFilterView
*
* renders partner_organization items for map filter
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'partnerOrganizationList'
], function($, _, Backbone, partnerOrganizationList) {
  var partnerOrganizationFilterView = Backbone.View.extend({
    initialize: function(args) {
      var self = this;
      this.parent = args.parent;
      this.collection = new partnerOrganizationList();
      this.collection.fetch({
        success: function() {
          self.render();
        }
      });
    },
    template: _.template('\
        <% _.each(data, function(partner_organization) { %>\
        <div class="input-group">\
          <span class="input-group-addon">\
            <input type="checkbox" name="<%=partner_organization.partner_id%>" checked="true">\
          </span>\
          <div class="form-control" style="background:#fefefe; font-size:12px;"><%=partner_organization.name%></div>\
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
        "type": "partner",
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
  return partnerOrganizationFilterView;
});
  