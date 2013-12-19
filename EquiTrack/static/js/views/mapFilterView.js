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
    filterCollection: function(filter) {
      
      console.log(filter);

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
          if (parseInt(eval("item."+filter_instance.type+"_id")) == filter_instance.id) {
            return false;
          } else return true;
        });
      });

      // ensure we do not have duplicate points and copy temporary object over this.collection
      // call this.render elsewhere
//      this.collection = _.uniq(coll, function(item) { return item.latitude+"|"+item.longitude; });
      this.collection = coll;
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
              </h4>\
            </div>\
            <div id="collapseFour" class="panel-collapse collapse">\
              <div class="panel-body" id="target-list">\
                indicator list goes here\
              </div>\
            </div>\
          </div>\
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
  