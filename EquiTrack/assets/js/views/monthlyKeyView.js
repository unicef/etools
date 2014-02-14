/*
* view: montlyKeyView
*
* draws key for monthly chart page
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var monthlyKeyView = Backbone.View.extend({
    initialize: function(arguments) {
      this.key = [
        {
          "color": "#a20000",
          "label": "Programmed number of beneficiaries"
        },
        {
          "color": "#26a200",
          "label": "Current number of beneficiaries"
        },
        {
          "color": "#006ba2",
          "label": "Total number of beneficiaries"
        }
      ];
      this.render();
    },
    template: _.template('\
      <div class="row" style="margin-bottom:10px;">\
        <table class="key-table">\
        <% _.each(data, function(item) { %>\
          <tr>\
            <td style="height:20px; width:20px; background:<%=item.color%>"> </td>\
            <td></td>\
            <td class="key-label"><%=item.label%></td>\
          </tr>\
        <% }) %>\
        </table>\
      </div>\
    ', null, {variable: 'data'}),
    render: function() {
      this.$el.html(this.template(this.key));
    }
  });
  return monthlyKeyView;
});