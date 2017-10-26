mapboxgl.accessToken = document.getElementById('mapjs').getAttribute('data-token');

var map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/march-on/cj95y50am1fbj2rqhogye1lu5',
  center: [-95, 40],
  zoom: 4
});
