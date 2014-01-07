/*
* view: mapView
*
* renders map page
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'leaflet',
  'lclusterer'
], function($, _, Backbone, L) {
  var mapView = Backbone.View.extend({
    initialize: function(args) {
      this.parent = args.parent;
      this.render();
    },
    render: function() {
      var self = this;
      L.Icon.Default.imagePath = '/pcatracking/images';
      var cloudmadeUrl = 'http://{s}.tile.cloudmade.com/BC9A493B41014CAABB98F0471D759707/997/256/{z}/{x}/{y}.png',
        cloudmadeAttribution = 'Map data &copy; 2011 OpenStreetMap contributors, Imagery &copy; 2011 CloudMade, Points &copy 2012 LINZ',
        cloudmade = L.tileLayer(cloudmadeUrl, {maxZoom: 17, attribution: cloudmadeAttribution}),
        latlng = L.latLng(33.89, 35.51);

      // remove existing markers
      if (typeof this.markers != 'undefined') {
        this.map.removeLayer(this.markers);
      }
      
      // build or rebuild markers
      this.markers = L.markerClusterGroup();
      _.each(this.parent.collection, function(location) {
  			var marker_content = '\
  			  <h4>'+location.pca_number+'</h4>\
          <table cellpadding="4" cellspacing="0" border="0">\
            <tr>\
              <td style="vertical-align:top; white-space:nowrap;">PCA title:</td>\
              <td style="vertical-align:top;">'+location.pca_title+'</td>\
            </tr>\
            <tr>\
              <td style="vertical-align:top; white-space:nowrap;">Gateway:</td>\
              <td style="vertical-align:top;">'+location.gateway_name+'</td>\
            </tr>\
            <tr>\
              <td style="vertical-align:top; white-space:nowrap;">Partner:</td>\
              <td style="vertical-align:top;">'+location.partner_name+'</td>\
            </tr>\
            <tr>\
              <td style="vertical-align:top; white-space:nowrap;">Sector:</td>\
              <td style="vertical-align:top;">'+location.sector_name+'</td>\
            </tr>\
          </table>\
  			';
  			var marker = L.marker(new L.LatLng(location.latitude, location.longitude), {});
  			marker.bindPopup(marker_content);
  			self.markers.addLayer(marker);        
      });

      // init map or redraw markers
      if (typeof this.map != 'undefined') {
        this.map.addLayer(this.markers);
      } else {
        this.map = L.map('map', {center: latlng, zoom: 9, layers: [cloudmade, this.markers]});
      }
    }
  });
  return mapView;
});
  