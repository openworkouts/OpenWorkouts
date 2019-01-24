
/*

  OpenWorkouts Javascript code

*/


// Namespace
var owjs = {};


owjs.map = function(spec) {

    "use strict";

    // parameters provided when creating an "instance" of a map
    var map_id = spec.map_id;
    var latitude = spec.latitude;
    var longitude = spec.longitude;
    var zoom = spec.zoom;
    var gpx_url = spec.gpx_url;
    var start_icon = spec.start_icon;
    var end_icon = spec.end_icon;
    var shadow = spec.shadow;
    var elevation = spec.elevation;
    var zoom_control = spec.zoom_control;

    // OpenStreetMap urls and references
    var openstreetmap_url = 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    var openstreetmap_attr = 'Map data &copy; <a href="http://www.osm.org">OpenStreetMap</a>';

    // Some constants reused through the code
    var map;
    var gpx;
    var elevation;
    var ow_charts;

    var create_map = function create_map(latitude, longitude, zoom) {
        /* Create a Leaflet map, set center point and add tiles */
        map = L.map(map_id, {zoomControl: zoom_control});
        map.setView([latitude, longitude], zoom);
        var tile_layer = L.tileLayer(openstreetmap_url, {
            attribution: openstreetmap_attr
        });
        tile_layer.addTo(map);
    };

    var add_elevation_chart = function add_elevation_chart() {
        /*
           Add the elevation chart support to the map.
           This has to be called *after* create_map and *before* load_gpx.
        */
        elevation = L.control.elevation({
            position: "bottomright",
            theme: "steelblue-theme", //default: lime-theme
            width: 600,
            height: 125,
            margins: {
                top: 10,
                right: 20,
                bottom: 30,
                left: 50
            },
            useHeightIndicator: true, //if false a marker is drawn at map position
            interpolation: "linear", //see https://github.com/mbostock/d3/wiki/SVG-Shapes#wiki-area_interpolate
            hoverNumber: {
                decimalsX: 3, //decimals on distance (always in km)
                decimalsY: 0, //deciamls on height (always in m)
                formatter: undefined //custom formatter function may be injected
            },
            xTicks: undefined, //number of ticks in x axis, calculated by default according to width
            yTicks: undefined, //number of ticks on y axis, calculated by default according to height
            collapsed: false    //collapsed mode, show chart on click or mouseover
        });

        var ele_container = elevation.addTo(map);
        /* document.getElementById('ow-analysis').appendChild(
            ele_container._container); */
    };

    var load_gpx = function load_gpx(gpx_url) {
        /*
          Load the gpx from the given url, add it to the map and feed it to the
          elevation chart
        */
        var gpx = new L.GPX(gpx_url, {
            async: true,
            marker_options: {
                startIconUrl: start_icon,
                endIconUrl: end_icon,
                shadowUrl: shadow,
            },
        });

        gpx.on('loaded', function(e) {
	    map.fitBounds(e.target.getBounds());
	});

        if (elevation) {
            gpx.on("addline",function(e){
                elevation.addData(e.line);
                // ow_charts.addData(e.line);
            });
        };

        gpx.addTo(map);
    };

    var render = function render() {
        // create the map, add elevation, load gpx
        create_map(latitude, longitude, zoom);
        if (elevation) {
            add_elevation_chart();
        }
        // add_ow_charts();
        load_gpx(gpx_url);
    };

    var that = {}
    that.render = render;
    return that

};


owjs.week_chart = function(spec) {

    "use strict";

    // parameters provided when creating an "instance" of the chart
    var chart_selector = spec.chart_selector,
        url = spec.url,
        current_day_name = spec.current_day_name

    // Helpers
    function select_x_axis_label(d) {
        /* Given a value, return the label associated with it */
        return d3.select('.x-axis')
    	    .selectAll('text')
    	    .filter(function(x) { return x == d.name; });
    }

    // Methods
    var render = function render() {
        /*
           Build a d3 bar chart, populated with data from the given url.
         */
        var chart = d3.select("svg"),
            margin = {top: 20, right: 20, bottom: 30, left: 50},
            width = +chart.attr("width") - margin.left - margin.right,
            height = +chart.attr("height") - margin.top - margin.bottom,
            g = chart.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")"),
            x = d3.scaleBand().rangeRound([0, width]).padding(0.1),
            y = d3.scaleLinear().rangeRound([height, 0]);

        d3.json(url).then(function (data) {
	    x.domain(data.map(function (d) {
	        return d.name;
	    }));

	    y.domain([0, d3.max(data, function (d) {
	        return Number(d.distance);
	    })]);

	    g.append("g")
                .attr('class', 'x-axis')
	        .attr("transform", "translate(0," + height + ")")
	        .call(d3.axisBottom(x))

	    g.selectAll(".bar")
	        .data(data)
	        .enter().append("rect")
                .attr("class", function(d) {
                    if (d.name == current_day_name){
                        select_x_axis_label(d).attr('style', "font-weight: bold;");
                        return 'bar current'
                    }
                    else {
                        return 'bar'
                    }
                })
	        .attr("x", function (d) {
		    return x(d.name);
	        })
	        .attr("y", function (d) {
		    return y(Number(d.distance));
	        })
	        .attr("width", x.bandwidth())
	        .attr("height", function (d) {
		    return height - y(Number(d.distance));
	        })
                .on('mouseover', function(d) {
                    if (d.name != current_day_name){
                        select_x_axis_label(d).attr('style', "font-weight: bold;");
                    }
  		})
  		.on('mouseout', function(d) {
                    if (d.name != current_day_name){
        	        select_x_axis_label(d).attr('style', "font-weight: regular;");
                    }
                });

            g.selectAll(".text")
                .data(data)
                .enter()
                .append("text")
                .attr("class","label")
	        .attr("x", function (d) {
		    return x(d.name) + x.bandwidth()/2;
	        })
	        .attr("y", function (d) {
                    return y(Number(d.distance) + 5);
	        })
                .text(function(d) {
                    if (Number(d.distance) > 0) {
                        return d.distance;
                    }
                });

        });
    };

    var that = {}
    that.render = render;
    return that

};
