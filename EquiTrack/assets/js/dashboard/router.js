/*
* application router
*
* Handles all routes, i.e. pages, displaying
* appropriate page, or modal window loading
* data via API.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'sectorsView',
  'goalView',
  'targetProgressView',
  'pcaTargetShareView',
  'mapFilterView'
], function($, _, Backbone, sectorsView, goalView, targetProgressView, pcaTargetShareView, mapFilterView) {

  var AppRouter = Backbone.Router.extend({
    routes: {
      "goal/:id": "goalRoute",
      "map": "mapRoute",
      "sectors": "sectorsRoute",
      "target_progress/:target_id/:unit_id": "targetProgressRoute",
      "target_pca_share/:target_id/:unit_id/:year/:month": "targetPcaShareRoute",
      "*path": "defaultRoute"
    },
    
    // array for storing application views
    views: [],
    
    // method to show the sectors page
    showSectors: function() {
      $('#modal-window').modal('hide');
      var sectors_view = false;
      _.each(this.views, function(view) {
        if (view instanceof sectorsView) {
          sectors_view = view;
          return;
        } else {
//          view.remove();
        }
      });
      if (!sectors_view) {
        this.views.push(new sectorsView({
          el: $('#dashboard-container')
        }));
      } else {
        sectors_view.render();
      }
    },

    // method to display target progress page
    showTargetProgress: function(target_id, unit_id) {
      $('#modal-window').modal('hide');
      var target_progress_view = false;
      _.each(this.views, function(view) {
        if (view instanceof targetProgressView) {
          if (view.targetModel.attributes.target_id == target_id && view.targetModel.attributes.unit_id == unit_id) {
            target_progress_view = view;
            return;
          }
        } else {
//          view.remove();
        }
      });
      if (!target_progress_view) {
        this.views.push(new targetProgressView({
          "el": $('#dashboard-container'),
          "target_id": target_id,
          "unit_id": unit_id
        }));
      } else {
        target_progress_view.render();
        target_progress_view.renderHeader();
      }
    }
    
  });

  var initialize = function() {
    var router = new AppRouter;

    // handler for sectors route
    router.on('route:sectorsRoute', function() {
      // handle nav and containers
      $('#map-container').empty();
      $('#map-link').removeClass('active');
      $('#dashboard-link').addClass('active');
      $('#map-container').hide();
      $('#dashboard-container').show();

      // process route
      router.showSectors();
    });
    
    // handler for sectors route
    router.on('route:targetProgressRoute', function(target_id, unit_id) {
      // handle nav and containers
      $('#map-container').empty();
      $('#map-link').removeClass('active');
      $('#dashboard-link').addClass('active');
      $('#map-container').hide();
      $('#dashboard-container').show();

      // process route
      router.showTargetProgress(target_id, unit_id);
    });

    // handler for pca share
    router.on('route:targetPcaShareRoute', function(target_id, unit_id, year, month) {
      // handle nav and containers
      $('#map-container').empty();
      $('#map-link').removeClass('active');
      $('#dashboard-link').addClass('active');
      $('#map-container').hide();
      $('#dashboard-container').show();

      // clear main container and show target progress info
      $('#dashboard-container').empty();
      router.showTargetProgress(target_id, unit_id);

      // pca share pie chart logic
      var pca_view = false;
      _.each(router.views, function(view) {
        if (view instanceof pcaTargetShareView) {
          if (view.target_id == target_id && view.unit_id == unit_id) {
            pca_view = view;
            return;
          }
        }
      });
      if (!pca_view) {
        var start_d = year+'-'+month+'-01';
        router.views.push(new pcaTargetShareView({
          "target_id": target_id, 
          "unit_id": unit_id,
          "year": year,
          "month": month
        }));
      } else {
        pca_view.render();
      }
    });

    // handler for goal route
    router.on('route:goalRoute', function(goal_id) {
      // handle nav and containers
      $('#map-container').empty();
      $('#map-link').removeClass('active');
      $('#dashboard-link').addClass('active');
      $('#map-container').hide();
      $('#dashboard-container').show();

      // clear main container and show sectors info
      router.showSectors();

      // goal view logic
      var goal_view = false;
      _.each(router.views, function(view) {
        if (view instanceof goalView) {
          if (view.goal_id == goal_id) {
            goal_view = view;
            return;
          }
        }
      });
      if (!goal_view) {
        router.views.push(new goalView({id:goal_id}));
      } else {
        goal_view.render();
      }
    });

    // handler for map route
    router.on('route:mapRoute', function() {
      // handle nav and containers
      $('#dashboard-container').empty();
      $('#map-link').addClass('active');
      $('#dashboard-link').removeClass('active');
      $('#map-container').show();
      $('#dashboard-container').hide();
      
      // goal view logic
      var map_view = false;
      _.each(router.views, function(view) {
        if (view instanceof mapFilterView) {
          map_view = view;
          return;
        }
      });
      if (!map_view) {
        router.views.push(new mapFilterView({
          el: $('#map-container')
        }));
      } else {
        map_view.render();
      }
      
    });

    // default route
    router.on('route:defaultRoute', function(path) {
      router.navigate('/sectors', {trigger: true, replace: true});
    });

    // Start Backbone history a necessary step for bookmarkable URL's
    Backbone.history.start();
  };
  return {
    initialize: initialize
  };
});