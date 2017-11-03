mapboxgl.accessToken = document.getElementById('mapjs').getAttribute('data-token');

const app = new Vue({
  el: '#app',
  data: {
    activeGroup: null,
    map: null,
    popup: {},
  },

  mounted: function created() {
    this.map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/march-on/cj95y50am1fbj2rqhogye1lu5',
      center: [-95, 40],
      zoom: 3,
    });
    this.map.addControl(new mapboxgl.NavigationControl());
    this.popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
    });
    this.map.on('load', () => {
      this.map.on('click', 'marchon-sheet', e => this.showDetails(e));
      this.map.on('mousemove', 'marchon-sheet', _.throttle(e => this.showDetails(e), 100));
      this.map.on('mouseenter', 'marchon-sheet', e => this.showPopup(e));
      this.map.on('mouseleave', 'marchon-sheet', e => this.hidePopup(e));
    });
  },

  methods: {
    showDetails: function showDetails(e) {
      if (!e.features || !e.features.length) {
        return;
      }

      const feature = e.features[0];
      const props = feature.properties;

      props.mailto = `mailto:${props['contact email']}`;
      props.contactName = props['contact name'];
      this.activeGroup = props;
    },

    showPopup: function showPopup(e) {
      if (!e.features || !e.features.length) {
        return;
      }

      const feature = e.features[0];

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

/*
map.on('mousemove', 'marchon-sheet', _.throttle(function(e) {
  console.log('mousemove', e.point);
}, 100));

*/
