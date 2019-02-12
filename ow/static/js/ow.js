
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

    // Some vars reused through the code
    var map;
    var gpx;
    var elevation;

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
            theme: "openworkouts-theme",
            useHeightIndicator: true, //if false a marker is drawn at map position
            interpolation: d3.curveLinear,
            elevationDiv: "#elevation",
            detachedView: true,
            responsiveView: true,
            gpxOptions: {
		async: true,
		marker_options: {
		    startIconUrl: null,
		    endIconUrl: null,
		    shadowUrl: null,
		},
		polyline_options: {
		    color: '#EE4056',
		    opacity: 0.75,
		    weight: 5,
		    lineCap: 'round'
		},
	    },
        });
        elevation.loadGPX(map, gpx_url);
        // var ele_container = elevation.addTo(map);
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
	    polyline_options: {
		color: '#EE4056',
		opacity: 0.75,
		weight: 5,
		lineCap: 'round'
	    },
        });

        gpx.on('loaded', function(e) {
	    map.fitBounds(e.target.getBounds());
	});

        if (elevation) {
            gpx.on("addline",function(e){
                elevation.addData(e.line);
            });
        };

        gpx.addTo(map);
    };

    var render = function render() {
        // create the map, add elevation, load gpx (only if needed, as the
        // elevation plugin already loads the gpx data)
        create_map(latitude, longitude, zoom);
        if (elevation) {
            add_elevation_chart();
        }
        else {
            load_gpx(gpx_url);
        }
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
        var chart = d3.select(chart_selector),
            margin = {top: 17, right: 0, bottom: 20, left: 0},

            width = +chart.attr("width") - margin.left - margin.right,
            height = +chart.attr("height") - margin.top - margin.bottom,
            g = chart.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")"),
            x = d3.scaleBand().rangeRound([0, width]).padding(0.1),
            y = d3.scaleLinear().rangeRound([height, 0]);

        d3.json(url, {credentials: "same-origin"}).then(function (data) {
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
                    /*
                      Get the value for the current bar, then get the maximum
                      value to be displayed in the bar, which is used to
                      calculate the proper position of the label for this bar,
                      relatively to its height (1% above the bar)
                     */
                    var max = y.domain()[1];
                    return y(d.distance + y.domain()[1] * 0.02);
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


owjs.year_chart = function(spec) {

    "use strict";

    // parameters provided when creating an "instance" of the chart
    var chart_selector = spec.chart_selector,
        filters_selector = spec.filters_selector,
        switcher_selector = spec.switcher_selector,
        is_active_class = spec.is_active_class,
        is_active_selector = '.' + is_active_class,
        urls = spec.urls,
        current_month = spec.current_month,
        current_week = spec.current_week,
        y_axis_labels = spec.y_axis_labels,
        filter_by = spec.filter_by,
        url = spec.url;

    // Helpers
    function select_x_axis_label(d) {
        /* Given a value, return the label associated with it */
        return d3.select('.x-axis-b')
    	    .selectAll('text')
    	    .filter(function(x) { return x == d.name; });
    };

    function get_y_value(d, filter_by) {
        return Number(d[filter_by]);
    };

    function get_y_axis_label(filter_by) {
        return y_axis_labels[filter_by];
    };

    function get_name_for_x(d) {
        if (d.week == undefined || d.week == 0) {
            return d.name;
        }
        else {
            return d.id.split('-')[2];
        }
    }

    // Methods
    var filters_setup = function filters_setup() {
        $(filters_selector).on('click', function(e) {
            e.preventDefault();
            $(filters_selector + is_active_selector).removeClass(is_active_class);
            /* $(this).removeClass('is-active'); */
            filter_by = $(this).attr('class').split('-')[1]
            $(this).addClass(is_active_class);
            var chart = d3.select(chart_selector);
            chart.selectAll("*").remove();
            render(filter_by, url);

        });
    };

    var switcher_setup = function switcher_setup() {
        $(switcher_selector).on('click', function(e) {
            e.preventDefault();
            $(switcher_selector + is_active_selector).removeClass(is_active_class);
            url = $(this).attr('class').split('-')[1]
            $(this).addClass(is_active_class);
            var chart = d3.select(chart_selector);
            chart.selectAll("*").remove();
            render(filter_by, url);
        });
    };

    var render = function render(filter_by, url) {
        /*
          Build a d3 bar chart, populated with data from the given url.
        */
        var chart = d3.select(chart_selector),
            margin = {top: 20, right: 20, bottom: 30, left: 50},
            width = +chart.attr("width") - margin.left - margin.right,
            height = +chart.attr("height") - margin.top - margin.bottom,
            g = chart.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")"),
            x = d3.scaleBand().rangeRound([0, width]).padding(0.1),
            y = d3.scaleLinear().rangeRound([height, 0]);

        d3.json(urls[url], {credentials: "same-origin"}).then(function (data) {
	    x.domain(data.map(function (d) {
                return get_name_for_x(d);
	        // return d.name;
	    }));

	    y.domain([0, d3.max(data, function (d) {
                return get_y_value(d, filter_by);
	    })]);

	    g.append("g")
                .attr('class', 'x-axis-b')
	        .attr("transform", "translate(0," + height + ")")
                .call(d3.axisBottom(x))

            g.append("g")
	        .call(d3.axisLeft(y))
	        .append("text")
	        .attr("fill", "#000")
	        .attr("transform", "rotate(-90)")
	        .attr("y", 6)
	        .attr("dy", "0.71em")
	        .attr("text-anchor", "end")
	        .text(get_y_axis_label(filter_by));

	    g.selectAll(".bar")
	        .data(data)
	        .enter().append("rect")
                .attr("class", function(d) {
                    var sel_week = current_month + '-' + current_week;
                    if (d.id == current_month || d.id == sel_week){
                        /* Bar for the currently selected month or week */
                        select_x_axis_label(d).attr('style', "font-weight: bold;");
                        return 'bar current';
                    }
                    else {
                        if (!current_week && d.id.indexOf(current_month) >=0 ) {
                            /*
                               User selected a month, then switched to weekly
                               view, we do highlight all the bars for weeks in
                               that month
                            */
                            select_x_axis_label(d).attr('style', "font-weight: bold;");
                            return 'bar current';
                        }
                        else {
                            /* Non-selected bar */
                            return 'bar';
                        }

                    }
                })
	        .attr("x", function (d) {
		    return x(get_name_for_x(d));
	        })
	        .attr("y", function (d) {
		    return y(get_y_value(d, filter_by));
	        })
	        .attr("width", x.bandwidth())
	        .attr("height", function (d) {
		    return height - y(get_y_value(d, filter_by));
	        })
                .on('mouseover', function(d) {
                    if (d.id != current_month){
                        select_x_axis_label(d).attr('style', "font-weight: bold;");
                    }
  		})
  		.on('mouseout', function(d) {
                    if (d.id != current_month){
        	        select_x_axis_label(d).attr('style', "font-weight: regular;");
                    }
                })
                .on('click', function(d) {
                    window.location.href = d.url;
                });

            if (url == 'monthly') {
                g.selectAll(".text")
                    .data(data)
                    .enter()
                    .append("text")
                    .attr("class","label")
	            .attr("x", function (d) {
		        return x(get_name_for_x(d)) + x.bandwidth()/2;
	            })
	            .attr("y", function (d) {
                        /*
                          Get the value for the current bar, then get the maximum
                          value to be displayed in the bar, which is used to
                          calculate the proper position of the label for this bar,
                          relatively to its height (1% above the bar)
                        */
                        var value = get_y_value(d, filter_by);
                        var max = y.domain()[1];
                        return y(value + y.domain()[1] * 0.01);
	            })
                    .text(function(d) {
                        var value = get_y_value(d, filter_by)
                        if ( value > 0) {
                            return value;
                        }
                    });
            }

            if (url == 'weekly') {
                g.selectAll(".tick")
                    .each(function (d, i) {
                        /*
                          Remove from the x-axis tickets those without letters
                          on them (useful for the weekly chart)
                        */
                        if (d !== parseInt(d, 10)) {
                            if(!d.match(/[a-z]/i)) {
                                this.remove();
                            }
                        }
                    });
            }
        });
    };

    var that = {}
    that.filters_setup = filters_setup;
    that.switcher_setup = switcher_setup;
    that.render = render;
    return that

};


owjs.map_shots = function(spec) {

    "use strict";

    var img_selector = spec.img_selector;

    var run = function run(){
        $(img_selector).each(function(){
            var img = $(this);
            var a = $(this).parent();
            var url = a.attr('href') + 'map-shot';
            var jqxhr = $.getJSON(url, function(info) {
                img.fadeOut('fast', function () {
                    img.attr('src', info['url']);
                    img.fadeIn('fast');
                });
                img.removeClass('js-needs-map');
            });
        });
    };

    var that = {}
    that.run = run;
    return that

};
