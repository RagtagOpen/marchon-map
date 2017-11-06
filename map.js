mapboxgl.accessToken = document.getElementById('mapjs').getAttribute('data-token');

const app = new Vue({
  el: '#app',
  data: {
    activeGroup: null,
    map: null,
    popup: {},
    userLocation: null,
    mapLoaded: false,
    userMarker: null,
  },

  created: function created() {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition((position) => {
        this.userLocation = position.coords;
      });
    }
  },

  mounted: function mounted() {
    this.map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/march-on/cj95y50am1fbj2rqhogye1lu5',
      center: [-95, 40],
      zoom: 3,
    });
    this.map.addControl(new mapboxgl.NavigationControl(), 'bottom-right');
    this.popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
    });
    this.geocoder = new MapboxGeocoder({
      accessToken: mapboxgl.accessToken,
      country: 'us,ca',
    });
    this.map.addControl(this.geocoder);
    this.geocoder.on('result', (r) => {
      if (r.result && r.result.center) {
        this.userLocation = {
          latitude: r.result.center[1],
          longitude: r.result.center[0],
        };
      }
    });
    this.map.on('load', () => {
      this.mapLoaded = true;
      this.map.on('click', 'marchon-sheet', e => this.showFeature(e.features[0]));
      this.map.on('mousemove', 'marchon-sheet', _.throttle(e => this.showFeature(e.features[0]), 100));
      this.map.on('mouseenter', 'marchon-sheet', e => this.showPopup(e.features[0]));
      this.map.on('mouseleave', 'marchon-sheet', e => this.hidePopup(e.features[0]));
    });
  },

  watch: {
    mapLoaded: function mapLoaded() {
      if (this.userLocation) {
        this.zoomToClosest();
      }
    },

    userLocation: function userLocation() {
      if (this.mapLoaded) {
        this.zoomToClosest();
      }
    },
  },

  methods: {
    zoomToClosest() {
      const features = this.map.queryRenderedFeatures({ layers: ['marchon-sheet'] });
      const loc = this.userLocation;
      const withDistance = features.map((feature) => {
        const coords = feature.geometry.coordinates;

        return {
          feature,
          distance: this.distance(loc.latitude, loc.longitude, coords[1], coords[0]),
        };
      });
      const closest = _.minBy(withDistance, d => d.distance);
      const featureLoc = closest.feature.geometry.coordinates; // [lng, lat]

      this.map.fitBounds([
        // sw
        [Math.min(loc.longitude, featureLoc[0]), Math.min(loc.latitude, featureLoc[1])],
        // ne
        [Math.max(loc.longitude, featureLoc[0]), Math.max(loc.latitude, featureLoc[1])],
      ],
      { maxZoom: 15, padding: 70 });

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

    deg2rad: deg => deg * (Math.PI / 180),

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

      props.mailto = `mailto:${props['contact email']}`;
      props.contactName = props['contact name'];
      this.activeGroup = props;
    },

    showPopup: function showPopup(feature) {
      this.popup
        .setLngLat(feature.geometry.coordinates)
        .setHTML(`<b>${feature.properties.name}</b>`)
        .addTo(this.map);
    },

    hidePopup: function hidePopup() {
      this.popup.remove();
    },
  },
});
