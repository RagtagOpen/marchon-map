mapboxgl.accessToken = document.getElementById('mapjs').getAttribute('data-token');
const geojson = pegasus('https://s3.amazonaws.com/ragtag-marchon/affiliates.json');

const app = new Vue({
  el: '#app',
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
      navigator.geolocation.getCurrentPosition((position) => {
        this.userLocation = position.coords;
      });
    }
  },

  mounted: function mounted() {
    this.map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/march-on/cj9nq97bw3oco2snohkuh423m',
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
      flyTo: false,
      country: 'us,ca',
    });
    this.map.addControl(this.geocoder);
    this.geocoder.on('result', _.throttle((r) => {
      if (r.result && r.result.center) {
        this.userLocation = {
          latitude: r.result.center[1],
          longitude: r.result.center[0],
        };
      }
    }, 100));
    this.map.on('load', () => {
      this.mapLoaded = true;
      // load GeoJSON, then pass to Mapbox
      // Mapbox won't share if it loads the data: https://github.com/mapbox/mapbox-gl-js/issues/1762
      geojson.then((data) => {
        this.map.addSource('marchon-geojson', { type: 'geojson', data });
        this.features = data.features;
        document.getElementById('affiliate').style.display = 'block';
      });
      this.map.addLayer({
        id: 'marchon',
        type: 'symbol',
        source: 'marchon-geojson',
        layout: {
          'icon-image': 'smallstar',
          'icon-allow-overlap': true,
          'text-allow-overlap': true,
        },
      });
      this.map.on('click', 'marchon', e => this.showFeature(e.features[0]));
      this.map.on('mousemove', 'marchon', _.throttle(e => this.showFeature(e.features[0]), 100));
      this.map.on('mouseenter', 'marchon', e => this.showPopup(e.features[0]));
      this.map.on('mouseleave', 'marchon', (e) => {
        if (e.features && e.features.length) {
          this.hidePopup(e.features[0]);
        }
      });
    });
    // TODO: not drawing all features (New England)
  },

  computed: {
    events: function events() {
      const now = moment();
      const ev = this.features.map((feature) => {
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
      if (!this.features.length) {
        return;
      }
      const loc = this.userLocation;
      const withDistance = this.features.map((feature) => {
        const coords = feature.geometry.coordinates;
        const distance = this.distance(loc.latitude, loc.longitude, coords[1], coords[0]);

        console.log(`${feature.properties.name} = ${distance}km`);

        return {
          feature,
          distance,
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
      { maxZoom: 15, padding: 100 });

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

      props.mailto = `mailto:${props.contactEmail}`;
      if (props.event) {
        props.eventMeta = this.events.find(ev => ev.location === props.location && !ev.past);
      }
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
