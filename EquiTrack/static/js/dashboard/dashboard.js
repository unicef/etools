/*
* Dashboard application main
*
* This initializes and boots up 
* the application.
*/
define([
  'jquery', 
  'underscore', 
  'backbone',
  'router'
], function($, _, Backbone, Router){
  var initialize = function(){
    Router.initialize();
  };
  return { 
    initialize: initialize
  };
});

// handle highlighting in the main navigation
//$('.main-navigation-item').on('click',function(e) {
//  $(this).parent().parent().children().removeClass('active');
//  $(this).parent().addClass('active');
//});

