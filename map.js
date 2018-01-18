const mapjs = document.getElementById('mapjs');
// pegasus for loading json data in parallel with other scripts.
// For testing, you may want to  create a testdata.json file, and
// use that instead. Beware of aggressive caching by chrome.
const geojson = pegasus('https://s3.amazonaws.com/ragtag-marchon/' + mapjs.getAttribute('data-filename'));
// const geojson = pegasus('/testdata.json');
const countries = mapjs.getAttribute('data-countries') || 'us,ca';
mapboxgl.accessToken = mapjs.getAttribute('data-token');

// for the layer filter, we have a vue component, which is managing
// a mapbox control which we define (https://www.mapbox.com/mapbox-gl-js/api/#icontrol)

// this is the vue component - it is passed the layers, and it creates
// checkbox for each layer. We model the checks with an array of
// strings, and when a box changes, we emit 'layer-change', which is
// caught by the parent vue app, and processes the hiding and showing
Vue.component('ragtag-layerfilter', {
  props: ['layers'],
  template: '#layerfilter-template',
  data: function() {
    return {
      // I would *really* like to figure out how to generate this
      // initial list of checkedLayers from the layers that are
      // passed into us, but I am just learning vue, and so far
      // have failed. - Marion Newlevant
      // Note that we get a javascript error if any of these layers
      // don't actually exist.
      checkedLayers: [
        'marchon-affiliate-true',
        'marchon-affiliate-false',
        'marchon-source-actionnetwork',
      ],
    }
  },
  methods: {
    showHideLayers: function() {
      this.$emit('layer-change', this.checkedLayers);
    }
  },
});

// this is the mapbox control - it grabs the existing vue component
// and uses that.
function LayerFilterControl() {}
LayerFilterControl.prototype.onAdd = function(map) {
  this._map = map;
  this._container = document.getElementById('layerFilterControl');
  return this._container;
};
LayerFilterControl.prototype.onRemove = function() {};

const app = new Vue({
  el: '#mapApp',
  data: {
    activeGroup: null,
    map: null,
    popup: {},
    userLocation: null,

    mapLoaded: false,
    userMarker: null,
    features: [],
    mapLayers: [], // data about all of the map layers
  },

  created: function created() {
    if ('geolocation' in navigator) {
      const _this = this;

      navigator.geolocation.getCurrentPosition(function(position) {
        _this.userLocation = position.coords;
        _this.locationSrc = 'browser';
      });
    }
  },

  mounted: function mounted() {
    document.getElementById('mapApp').style.display = 'block';
    const _this = this;

    this.map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/march-on/cj9nq97bw3oco2snohkuh423m',
      center: [-95, 40],
      zoom: 3,
    });
    this.map.addControl(new mapboxgl.NavigationControl(), 'bottom-right');
    if (document.getElementById('layerFilterControl')) {
      this.map.addControl(new LayerFilterControl(), 'top-left');
    }
    this.popup = new mapboxgl.Popup({
      closeButton: true,
      closeOnClick: true,
    });
    this.geocoder = new MapboxGeocoder({
      accessToken: mapboxgl.accessToken,
      flyTo: false,
      country: countries,
    });
    this.map.addControl(this.geocoder);
    this.geocoder.on('result', _.throttle(function(r) {
      if (r.result && r.result.center) {
        _this.userLocation = {
          latitude: r.result.center[1],
          longitude: r.result.center[0],
        };
        _this.locationSrc = 'search';
      }
    }, 100));
    this.map.on('load', function() {
      _this.mapLoaded = true;
      // load GeoJSON, then pass to Mapbox (pegasus loading magic)
      // Mapbox won't share if it loads the data: https://github.com/mapbox/mapbox-gl-js/issues/1762
      geojson.then(function(data) {
        _this.features = data.features;
        // don't check for events on affiliate map; use all
        const features = document.getElementById('affiliate') ? _this.features : _this.futureFeatures;
        // sort out our features into what will be our map layers
        const affiliateTrue = {
          type: 'FeatureCollection',
          features: _.filter(features, function(feature) { return feature.properties.source === 'events' && feature.properties.affiliate; }),
        };
        const affiliateFalse = {
          type: 'FeatureCollection',
          features: _.filter(features, function(feature) { return feature.properties.source === 'events' && !feature.properties.affiliate; }),
        };
        const sourceActionNetwork = {
          type: 'FeatureCollection',
          features: _.filter(features, function(feature) { return feature.properties.source === 'actionnetwork'; }),
        };

        if (document.getElementById('affiliate')) {
          document.getElementById('affiliate').style.display = 'block';
        }
        // US + southern Canada bounding box
        const lat = [55, 24.52];
        const lng = [-66.95, -124.77];

        _this.map.fitBounds([
          [_.min(lng), _.min(lat)], // sw
          [_.max(lng), _.max(lat)], // ne
        ], { padding: 10 });

        // add the map layers to the map, and also to the vue mapLayers
        // data. Not currently using initiallyChecked.
        if (affiliateFalse.features.length) {
          _this.map.addSource('marchon-affiliate-false-geojson', { type: 'geojson', data: affiliateFalse });
          _this.addLayer('marchon-affiliate-false', 'marchon-affiliate-false-geojson', { 'icon-image': 'star-15-red' });
          _this.mapLayers.push({
            layerId: 'marchon-affiliate-false',
            label: 'Non Affiliates',
            icon: 'star-15-red.svg',
            initiallyChecked: true,
          });
        }
        if (sourceActionNetwork.features.length) {
          _this.map.addSource('marchon-source-actionnetwork-geojson', { type: 'geojson', data: sourceActionNetwork });
          _this.addLayer('marchon-source-actionnetwork', 'marchon-source-actionnetwork-geojson',
            { 'icon-image': 'house', 'icon-size': 0.7 });
          _this.mapLayers.push({
            layerId: 'marchon-source-actionnetwork',
            label: 'House Parties',
            icon: 'house.svg',
            initiallyChecked: true,
          });
        }
        if (affiliateTrue.features.length) {
          _this.map.addSource('marchon-affiliate-true-geojson', { type: 'geojson', data: affiliateTrue });
          _this.addLayer('marchon-affiliate-true', 'marchon-affiliate-true-geojson', { 'icon-image': 'smallstar' });
          _this.mapLayers.push({
            layerId: 'marchon-affiliate-true',
            label: 'Affiliates',
            icon: 'smallstar.svg',
            initiallyChecked: true,
          });
        }
      });

      setTimeout(function() {
        const el = document.getElementsByClassName('mapboxgl-ctrl-attrib');

        if (el && el.length) {
          el[0].innerHTML = 'by <a style="text-decoration: underline" target="_blank" href="https://ragtag.org">Ragtag.org</a>&nbsp;&nbsp; ' +
            el[0].innerHTML;
          console.log('attribution updated');
        }
      }, 200);
    });
  },

  computed: {
    // the features that are in the future or the recent past (the ones we display).
    // this is where we filter out the old stuff that doesn't show up anywhere on the
    // map.
    futureFeatures: function futureFeatures() {
      const now = moment().subtract(0, 'days'); // recently passed dates are still 'current' (adjust this number to keep more/less past events)
      const ff = this.features.map(function(feature) {
        const props = feature.properties;

        if (!props.eventDate) {
          return null;
        }
        const dt = moment(feature.properties.eventDate, 'MM/DD/YYYY');

        if (dt.isBefore(now)) {
          return null;
        }

        return feature;
      });
      return _.compact(ff);
    },
    // the events. This is a processed version of the futureFeatures, displayed on the
    // popup.
    events: function events() {
      return this.futureFeatures.map(function(feature) {
        const props = feature.properties;

        const dt = moment(feature.properties.eventDate, 'MM/DD/YYYY');

        return {
          location: props.location,
          name: props.event,
          ymd: dt.format('YYYY-MM-DD'),
          weekday: dt.format('dddd'),
          month: dt.format('MMMM'),
          day: dt.format('D'),
          link: props.eventLink,
        };
      });
    },

    sortedUpcomingEvents: function sortedEvents() {
      return _.sortBy(this.events, ['ymd', 'name']);
    },
  },

  watch: {
    mapLoaded: function mapLoaded() {
      if (this.userLocation) {
        this.highlightClosest();
      }
      this.highlightSearch();
    },

    activeGroup: function activeGroup() {
      this.highlightSearch();
    },

    userLocation: function userLocation() {
      // geolocation takes a bit; don't set popup to closest if
      // user has already clicked one
      if (this.mapLoaded && (this.locationSrc === 'search' || !this.popupLocation)) {
        this.highlightClosest();
      }
    },
  },

  methods: {
    inIframe: function() {
      try {
        return window.self !== window.top;
      } catch (e) {
        return true;
      }
    },

    addLayer: function(layerId, source, layout) {
      const _this = this;
      const layoutProps = {
          'visibility': 'visible',
          'icon-allow-overlap': true,
          'text-allow-overlap': true,
      };

      this.map.addLayer({
        id: layerId,
        type: 'symbol',
        source: source,
        layout: Object.assign(layout, layoutProps),
      });
      this.map.on('click', layerId, function(e) {
        _this.showFeature(e.features[0]);
        _this.showPopup(e.features[0]);
      });
      this.map.on('mousemove', layerId, _.throttle(function(e) {
        _this.showFeature(e.features[0]);
      }, 100));
      this.map.on('mouseenter', layerId, function(e) {
        _this.showPopup(e.features[0]);
      });
      this.map.on('mouseleave', layerId, function(e) {
        if (e.features && e.features.length) {
          _this.hidePopup(e.features[0]);
        }
      });
    },

    highlightSearch: function() {
      const control = document.getElementsByClassName('mapboxgl-ctrl-geocoder');

      if (!control) {
        return;
      }

      const el = control[0];

      if (this.activeGroup) {
        el.className = el.className.replace('highlight', '');

        const arrow = document.getElementById('arrowMarker');

        if (arrow) {
          el.removeChild(arrow);
        }
      } else {
        const arrow = document.createElement('div');

        el.className += ' highlight';
        arrow.className = 'arrow-marker';
        arrow.id = 'arrowMarker';
        arrow.innerHTML = '<i class="fa fa-chevron-left"></i>';
        el.insertBefore(arrow, el.childNodes[0]);
      }
    },

    highlightClosest: function() {
      const _this = this;

      if (!this.features.length) {
        return;
      }
      const loc = this.userLocation;
      const withDistance = this.features.map(function(feature) {
        const coords = feature.geometry.coordinates;
        const distance = _this.distance(loc.latitude, loc.longitude, coords[1], coords[0]);

        return {
          feature: feature,
          distance: distance,
        };
      });
      const closest = _.minBy(withDistance, function(d) { return d.distance; });

      if (!this.userMarker) {
        const el = document.getElementById('userMarker');

        el.style.display = 'block';
        this.userMarker = new mapboxgl.Marker(el)
          .setLngLat([loc.longitude, loc.latitude])
          .addTo(this.map);
      } else {
        this.userMarker.setLngLat([loc.longitude, loc.latitude]);
      }
      this.showFeature(closest.feature);
      this.showPopup(closest.feature);
    },

    deg2rad: function(deg) { return deg * (Math.PI / 180); },

    distance: function distance(lat1, lon1, lat2, lon2) {
      // distance in km
      const dLat = this.deg2rad(lat2 - lat1);
      const dLon = this.deg2rad(lon2 - lon1);
      const a = (Math.sin(dLat / 2) * Math.sin(dLat / 2)) +
          (Math.cos(this.deg2rad(lat1)) * Math.cos(this.deg2rad(lat2)) *
           Math.sin(dLon / 2) * Math.sin(dLon / 2));

      return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    },

    showFeature: function showFeature(feature) {
      const props = feature.properties;

      props.mailto = 'mailto:' + props.contactEmail;
      if (props.eventDate) {
        props.eventMeta = _.find(this.events, function(ev) {
          return ev.location === props.location;
        });
      }
      this.activeGroup = props;
    },

    showPopup: function showPopup(feature) {
      const _this = this;

      console.log('show popup for ', feature.properties.location);
      if (this.popup) {
        this.popup.remove();
      }
      // draw popup immediately with name
      this.popup
        .setLngLat(feature.geometry.coordinates)
        .setHTML('<div id="popupContent"><b>' + feature.properties.name + '</b></div>')
        .addTo(this.map);
      this.popupLocation = feature.properties.location;
      // update html when it's ready
      this.$nextTick(function popup() {
        // popup.setHTML doesn't update properly
        _this.popup.remove();
        _this.popup
          .setLngLat(feature.geometry.coordinates)
          .setHTML(document.getElementById('affiliateContent').innerHTML)
          .addTo(_this.map);
      });
    },

    hidePopup: function hidePopup() {
      this.popup.remove();
      this.popupLocation = null;
    },

    layerDisplayChange: function layerDisplayChange(layersToShow) {
      // hide all the layers
      for (var i = this.mapLayers.length - 1; i >= 0; i--) {
        this.map.setLayoutProperty(this.mapLayers[i].layerId, 'visibility', 'none');
      }
      // show the ones we want to show
      for (var i = layersToShow.length - 1; i >= 0; i--) {
        this.map.setLayoutProperty(layersToShow[i], 'visibility', 'visible');
      }
    }
  },
});
