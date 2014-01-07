/*
* view: mapView
*
* renders map page
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'mapView',
  'sectorFilterView',
  'rrp5OutputFilterView',
  'targetFilterView',
  'partnerOrganizationFilterView',
  'locationList'
], function($, _, Backbone, mapView, sectorFilterView, rrp5OutputFilterView, targetFilterView, partnerOrganizationFilterView, locationList) {
  var mapFilterView = Backbone.View.extend({
    initialize: function() {
      var self = this;
      this.collection = new locationList();
      this.filters = []; // placeholder for filtering arguments
      this.collection.fetch({
        success: function() {
          self.collection = self.collection.toJSON(); // we only want to deal with an array of items
          self.collection_original = self.collection;
          self.filterCollection();
          self.render();
        }
      });
    },
    refreshSelectors: function() {
      var sector_ids = _.pluck(_.where(this.filters, {
        type: "sector"
      }), 'id');

      // create target filter links on the basis of unselected sector_ids
      this.targetLinks.setSectorIDs(sector_ids);
      this.targetLinks.render();

      // create rrp5 output filter links on the basis of unselected sector_ids
      this.rrp5OutputLinks.setSectorIDs(sector_ids);
      this.rrp5OutputLinks.render();
    },
    filterCollection: function(filter) {
      // temporary variable for processing collection
      var coll;

      // inject or remove criteria from filter
      if (typeof filter === 'object') {

        // assign original collection to local collection var
        coll = this.collection_original;

        // we're removing a filter
        if (filter.checked) { 

          // removing .checked for clarity
          filter = { 
            "type": filter.type,
            "id": filter.id
          };

          // remove this item from this.filter
          this.filters = _.filter(this.filters, function(filter_instance) {
            return !_.isEqual(filter_instance, filter);
          });

        // we're adding a filter  
        } else { 

          // we can use the previously filtered array
          coll = this.collection;

          // removing checked for clarity
          this.filters.push({ 
            "type": filter.type,
            "id": filter.id
          });
        }
      } else {

        // assign original collection to local collection var
        coll = this.collection_original;
      }
      
      // apply filters
      _.each(this.filters, function(filter_instance) {
        coll = _.filter(coll, function(item) {
          return parseInt(eval("item."+filter_instance.type+"_id")) != filter_instance.id;
        });
      });

      // ensure we do not have duplicate points and copy temporary object over this.collection
      // call this.render elsewhere
//      this.collection = _.uniq(coll, function(item) { return item.latitude+"|"+item.longitude; });
      this.collection = coll;
    },
    events: {
      "click #sectors-toggle": "sectorToggleHandler",
      "click #rrp5-toggle": "RRP5ToggleHandler",
      "click #target-toggle": "TargetToggleHandler"
    },
    TargetToggleHandler: function(e) {
      var self = this;
      $('.target-box').prop('checked', !$('.target-box').prop('checked'));
      if ($('.target-box').prop('checked')) { // remove all targets from this.filter array
        this.filters = _.filter(this.filters, function(filter_instance) {
          return filter_instance.type != 'target'
        });        
      } else {
        $('.target-box').each(function(target) {
          self.filters.push({
            "type": "target",
            "id": this.name
          });
        });
      }
      this.filterCollection();
      this.map.render();
      e.preventDefault();
    },
    RRP5ToggleHandler: function(e) {
      var self = this;
      $('.rrp5-box').prop('checked', !$('.rrp5-box').prop('checked'));
      if ($('.rrp5-box').prop('checked')) { // remove all rrp5 outputs from this.filter array
        this.filters = _.filter(this.filters, function(filter_instance) {
          return filter_instance.type != 'rrp5_output'
        });        
      } else {
        $('.rrp5-box').each(function(rrp5) {
          self.filters.push({
            "type": "rrp5_output",
            "id": this.name
          });
        });
      }
      this.filterCollection();
      this.map.render();
      e.preventDefault();
    },
    sectorToggleHandler: function(e) {
      var self = this;
      $('.sector-box').prop('checked', !$('.sector-box').prop('checked'));
      if ($('.sector-box').prop('checked')) { // remove all sectors from this.filter array
        this.filters = _.filter(this.filters, function(filter_instance) {
          return filter_instance.type != 'sector'
        });        
      } else {
        $('.sector-box').each(function(sector) {
          self.filters.push({
            "type": "sector",
            "id": this.name
          });
        });
      }
      this.filterCollection();
      this.refreshSelectors();
      this.map.render();
      e.preventDefault();
    },
    template: _.template('\
      <div id="map-filter" class="col-md-3">\
        <h3>PCA filter tools</h3>\
        <div class="panel-group" id="accordion">\
\
          <div class="panel panel-default">\
            <div class="panel-heading">\
              <h4 class="panel-title">\
                <a data-toggle="collapse" href="#collapseOne">\
                  Sector\
                </a>\
                <button id="sectors-toggle" type="button" class="btn-xs btn-default" style="float:right;">toggle all</button>\
              </h4>\
            </div>\
            <div id="collapseOne" class="panel-collapse collapse in">\
              <div class="panel-body" id="sector-list">\
                sector list goes here\
              </div>\
            </div>\
          </div>\
\
          <div class="panel panel-default">\
            <div class="panel-heading">\
              <h4 class="panel-title">\
                <a data-toggle="collapse" href="#collapseThree">\
                  RRP5\
                </a>\
                <button id="rrp5-toggle" type="button" class="btn-xs btn-default" style="float:right;">toggle all</button>\
              </h4>\
            </div>\
            <div id="collapseThree" class="panel-collapse collapse">\
              <div class="panel-body" id="rrp5-output-list">\
                RRP5 list goes here\
              </div>\
            </div>\
          </div>\
\
          <div class="panel panel-default">\
            <div class="panel-heading">\
              <h4 class="panel-title">\
                <a data-toggle="collapse" href="#collapseFour">\
                  Indicator\
                </a>\
                <button id="target-toggle" type="button" class="btn-xs btn-default" style="float:right;">toggle all</button>\
              </h4>\
            </div>\
            <div id="collapseFour" class="panel-collapse collapse">\
              <div class="panel-body" id="target-list">\
                indicator list goes here\
              </div>\
            </div>\
          </div>\
\
          <hr />\
\
          <div class="panel panel-default">\
            <div class="panel-heading">\
              <h4 class="panel-title">\
                <a data-toggle="collapse" href="#collapseFive">\
                  Partner Organization\
                </a>\
              </h4>\
            </div>\
            <div id="collapseFive" class="panel-collapse collapse">\
              <div class="panel-body" id="partner-organization-list">\
                indicator list goes here\
              </div>\
            </div>\
          </div>\
\
        </div>\
      </div>\
      <div id="map-column" class="col-md-9">\
        <div id="map"></div>\
      </div>\
    '),
    render: function() {
      var self = this;
      this.$el.html(this.template());

      // create sector filter links
      this.sectorLinks = new sectorFilterView({
        el: $('#sector-list'),
        parent: this
      });

      // create rrp5_output filter links
      this.rrp5OutputLinks = new rrp5OutputFilterView({
        el: $('#rrp5-output-list'),
        parent: this
      });

      // create target filter links
      this.targetLinks = new targetFilterView({
        el: $('#target-list'),
        parent: this
      });

      // create partner organization filter links
      this.partnerOrganizationLinks = new partnerOrganizationFilterView({
        el: $('#partner-organization-list'),
        parent: this
      });

      // create map
      this.map = new mapView({
        el: $('#map'),
        parent: this
      });
    }
  });
  return mapFilterView;
});
  