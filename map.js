const mapjs = document.getElementById('mapjs');
const geojson = pegasus('https://s3.amazonaws.com/ragtag-marchon/' + mapjs.getAttribute('data-filename'));
const countries = mapjs.getAttribute('data-countries') || 'us,ca';

mapboxgl.accessToken = mapjs.getAttribute('data-token');

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
      // load GeoJSON, then pass to Mapbox
      // Mapbox won't share if it loads the data: https://github.com/mapbox/mapbox-gl-js/issues/1762
      // TODO: IE11
      geojson.then(function(data) {
        const affiliate = {
          type: 'FeatureCollection',
          features: _.filter(data.features, function(feature) { return feature.properties.source === 'events' && feature.properties.affiliate; }),
        };
        const other = {
          type: 'FeatureCollection',
          features: _.filter(data.features, function(feature) { return feature.properties.source === 'events' && !feature.properties.affiliate; }),
        };

        _this.features = data.features;
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

        if (other.features.length) {
          _this.map.addSource('marchon-other-geojson', { type: 'geojson', data: other });
          _this.addLayer('marchon-other', 'marchon-other-geojson', 'star-15-red');
        }
        if (affiliate.features.length) {
          _this.map.addSource('marchon-affiliate-geojson', { type: 'geojson', data: affiliate });
          _this.addLayer('marchon-affiliate', 'marchon-affiliate-geojson', 'smallstar');
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
    events: function events() {
      const now = moment();
      const ev = this.features.map(function(feature) {
        const props = feature.properties;

        if (!props.eventDate) {
          return null;
        }
        const dt = moment(feature.properties.eventDate, 'MM/DD/YYYY');

        if (dt.isBefore(now)) {
          return null;
        }

        return {
          location: props.location,
          name: props.event,
          ymd: dt.format('YYYY-MM-DD'),
          weekday: dt.format('dddd'),
          month: dt.format('MMMM'),
          day: dt.format('D'),
          past: dt.isBefore(now),
          link: props.eventLink,
        };
      });

      return _.compact(ev);
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
    addLayer: function(layerId, source, icon) {
      const _this = this;

      this.map.addLayer({
        id: layerId,
        type: 'symbol',
        source: source,
        layout: {
          'icon-image': icon,
          'icon-allow-overlap': true,
          'text-allow-overlap': true,
        },
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
          distance: distaince,
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
          return ev.location === props.location && !ev.past;
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
  },
});
