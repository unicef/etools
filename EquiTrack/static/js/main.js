requirejs.config({
  urlArgs: "nocache=" + (new Date()).getTime(),
  paths: {
    // external libraries
    "jquery":                         "lib/jquery.min",
    "underscore":                     "lib/underscore.min",
    "backbone":                       "lib/backbone.min",
    "bootstrap":                      "lib/bootstrap.min",
    "raphael":                        "lib/raphael.min",
    "graphael":                       "lib/g.raphael.min",
    "gbar":                           "lib/g.bar.min",
    "gline":                          "lib/g.line.min",
    "gpie":                           "lib/g.pie.min",
    "leaflet":                        "lib/leaflet.min", 
    "lclusterer":                     "lib/leaflet.markerclusterer.min",

    // utilities
    "utils":                          "lib/utils",
    
    // models
    "goalModel":                      "models/goalModel",
    "sectorModel":                    "models/sectorModel",
    "targetModel":                    "models/targetModel",
    "targetProgressModel":            "models/targetProgressModel",
    "pcaTargetShareModel":            "models/pcaTargetShareModel",
    "locationModel":                  "models/locationModel",
    "gatewayModel":                   "models/gatewayModel",
    "rrp5OutputModel":                "models/rrp5OutputModel",
    "partnerOrganizationModel":       "models/partnerOrganizationModel",
    
    // views
    "goalLinkView":                   "views/goalLinkView",
    "goalView":                       "views/goalView",
    "sectorsView":                    "views/sectorsView",
    "sectorView":                     "views/sectorView",
    "cumulativeTargetView":           "views/cumulativeTargetView",
    "monthlyTargetView":              "views/monthlyTargetView",
    "targetProgressView":             "views/targetProgressView",
    "pcaTargetShareView":             "views/pcaTargetShareView",
    "mapFilterView":                  "views/mapFilterView",
    "mapView":                        "views/mapView",
    "sectorFilterView":               "views/sectorFilterView",
    "rrp5OutputFilterView":           "views/rrp5OutputFilterView",
    "targetFilterView":               "views/targetFilterView",
    "partnerOrganizationFilterView":  "views/partnerOrganizationFilterView",
    "monthlyKeyView":                 "views/monthlyKeyView",
    "cumulativeKeyView":              "views/cumulativeKeyView",

    // collections
    "sectorList":                     "collections/sectorList",
    "targetProgressList":             "collections/targetProgressList",
    "locationList":                   "collections/locationList",
    "gatewayList":                    "collections/gatewayList",
    "rrp5OutputList":                 "collections/rrp5OutputList",
    "targetList":                     "collections/targetList",
    "partnerOrganizationList":        "collections/partnerOrganizationList",
    
    // router
    "router":                         "dashboard/router",

    // main application
    "dashboard":                      "dashboard/dashboard"
  },
  shim: {
    bootstrap: {
      deps: ["jquery"]
    },
    underscore: {
      exports: '_'
    },
    backbone: {
      deps: ["underscore", "jquery"],
      exports: "Backbone"
    },
    graphael: {
      deps: ["raphael"],
      exports: "gRaphael"
    },
    gbar: {
      deps: ["graphael"],
      exports: "gBar"
    },
    gline: {
      deps: ["graphael"],
      exports: "gLine"
    },
    gpie: {
      deps: ["graphael"],
      exports: "gPie"
    },
    lclusterer: {
      deps: ["leaflet"]
    }
  }
});

require([
  'dashboard'
], function(Dashboard){
  Dashboard.initialize();
});
