mapboxgl.accessToken = document.getElementById('mapjs').getAttribute('data-token');

const app = new Vue({
  el: '#app',
  data: {
    activeGroup: null,
    map: null,
  },

  mounted: function created() {
    this.map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/march-on/cj95y50am1fbj2rqhogye1lu5',
      center: [-95, 40],
      zoom: 3,
    });
    this.map.on('load', () => {
      this.map.on('click', e => this.showDetails(e));
      this.map.on('mousemove', 'marchon-sheet', _.throttle(e => this.showDetails(e), 100));
    });
  },

  methods: {
    showDetails: function showDetails(e) {
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ['marchon-sheet'],
      });

      if (!features.length) {
        return;
      }

      const props = features[0].properties;

      props.mailto = `mailto:${props['contact email']}`;
      props.contactName = props['contact name'];
      this.activeGroup = props;
    },
    // TODO: highlight active
    /*
    const popup = new mapboxgl.Popup({ offset: [0, -15] })
      .setLngLat(feature.geometry.coordinates)
      .setHTML('<h3>' + feature.properties.name + '</h3>')
      .setLngLat(feature.geometry.coordinates)
      .addTo(this.map);
    },
    */
  },
});

/*
map.on('mousemove', 'marchon-sheet', _.throttle(function(e) {
  console.log('mousemove', e.point);
}, 100));

*/
