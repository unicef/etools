/*
* utility functions
*/
define([
  'jquery',
  'underscore'
], function($, _){
  var utils = {

    // trims content of an HTML element and returns boolean
    // on the basis of it being empty or not
    isEmpty: function(el){
      return !$.trim(el.html())
    },
    getMonth: function(mon) {
      var months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "June",
        "July",
        "Aug",
        "Sept",
        "Oct",
        "Nov",
        "Dec"
      ];
      return months[mon];
    },
    formatNumber: function(num) {
      var o = num.toFixed();
      var n = "";
      while (o.length > 0) {
        n = (o.length > 3) ? ","+o.slice(-3)+n : o.slice(-3)+n;
        o = o.slice(0,-3);
      }
      return n;
    }
  };
  return utils;
});