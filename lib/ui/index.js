
let MeterRender = {};
(function(MeterRender){

    /**
     * Event handler for refreshing the table with the new kWh rate based on what's in the textbox.
     * @param {Event} event The event that triggered the request.
     * @returns {void}
     */
    MeterRender.onKwhChange = function onKwhChange(event) {
        let kwh = $('#kwh').val();
        let tbody = $('#mytable tbody');
        let rows = tbody.find('tr');
        rows.each((i, r) => {
            let row = $(r);
            let consumption = parseFloat(row.find('td').eq(2).text());
            row.find('td').eq(3).text('$' + (consumption * kwh).toFixed(2));
        });
    };

    /**
     * Draw a table of the monthly aggregate of consumption from the meter reads.
     * The meter reads will come with a day and a meter read. This function will
     * group them by month and show the consumption in a monthly listing.
     * @param {Object} meterReads Meter read data from server.
     * @returns {void}
     */
    MeterRender.drawTable = function drawTable(meterReads) {
        var table = $('#mytable');
        table.empty();
        let months = meterReads.value.reduce((m, x) => {
            // get the month as 2 digits always
            let d = ((d) => `${d.getFullYear()}-${('0'+d.getMonth()).slice(-2)}`)(new Date(x[0]));
            console.log(d);
            if ( typeof m[d] === "undefined" ) m[d] = 0;
            if ( typeof x[1] !== "number")
                console.log("!!!" + x[1]);
            m[d] += x[1];
            return m;
        }, {});
        let monthKeys = Object.keys(months);
        monthKeys.sort();
        var thead = $('<thead>');
        var tr = $('<tr><th>Year</th><th>Month</th><th>Consumption</th></tr>')
        var kwh = $('<input>')
          .attr('type', 'number')
          .attr('id', 'kwh')
          .attr('name', 'kwh')
          .attr('placeholder', 'kWh')
          .attr('step', 0.01)
          .val(0.13)
          .on('change', MeterRender.onKwhChange);
        var th = $('<th>').addClass('kwh').append(kwh);
        tr.append(th);
        thead.append(tr);
        var tbody = $('<tbody>');
        monthKeys.forEach((k) => {
            let date = k.split('-');
            let row = $('<tr>');
            row.append($(`<td></td>`).text(date[0]));
            row.append($(`<td></td>`).text(parseInt(date[1]) + 1));
            row.append($(`<td></td>`).text(months[k].toFixed(2) + ' kWh'));
            row.append($(`<td></td>`).text('$' + (months[k] * kwh.val()).toFixed(2)));
            tbody.append(row);
        });

        table.append(thead);
        table.append(tbody);
        console.log('Done populating table of meter reads.')
        console.log(meterReads);
    }


    /**
     * Google handler for drawing the chart.
     * @param {Object} meterReads Meter read data from server.
     * @returns {void}
     */
    MeterRender.drawChart = function drawChart(meterReads) {
        var data = new google.visualization.DataTable();
        data.addColumn('number', 'Date');
        data.addColumn('number', 'Reading');
        let reads = [...meterReads.value];
        reads.unshift(['Date', 'Reading']);
        var data = google.visualization.arrayToDataTable(reads);
        var options = {
            title: 'SmartMeter Texas Meter Reads',
            legend: { position: 'bottom' }
        };
        var chart = new google.visualization.LineChart(document.getElementById('mychart'));
        chart.draw(data, options);
    };

    /**
     * Request the meter reads from the server.
     * Sample response from the server looks like:
     * {
     *      error: false,
     *      status: 200,
     *      value: [
     *          [
     *              "2022-01-01",
     *              00.000
     *          ]
     *      }
     *  }
     * 
     * @param {Event} event The event that triggered the request.
     * @returns {void}
     */
    MeterRender.requestMetrics = function requestMetrics(event) {
        let fdate = encodeURI( $('#fdate').val() ), tdate = encodeURI( $('#tdate').val() );
        $.ajax({
            url: `/api/meterReads?fdate=${fdate}&tdate=${tdate}`,
        }).done(meterReads => {
            MeterRender.drawChart(meterReads);
            MeterRender.drawTable(meterReads);
        });
    };

    /**
     * On load event handler.
     * @param {Event} event The event that triggered the request.
     * @returns {void}
     */
    MeterRender.onLoad = function onLoad(event) {
        let fdate = $('#fdate'), tdate = $('#tdate');
        let sixmonths = new Date( Date.now() - (86400 * 1000 * 365) );
        let yday = new Date(Date.now() - 86400000);
        let dtopts = {
            changeMonth: true,
            changeYear: true,
            dateFormat: "yy-mm-dd"
        };
        fdate.datepicker(dtopts);
        tdate.datepicker(dtopts);

        fdate.val(`${sixmonths.getFullYear()}-${sixmonths.getMonth()+1}-${sixmonths.getDate()}`);
        tdate.val(`${yday.getFullYear()}-${yday.getMonth()+1}-${yday.getDate()}`);

        fdate.change(MeterRender.requestMetrics)
        tdate.change(MeterRender.requestMetrics)
    };

    google.charts.load('current', {'packages': ['corechart']});
    google.charts.setOnLoadCallback(MeterRender.requestMetrics);
    return MeterRender;
})(MeterRender);
window.MeterRenderer = MeterRender;

$(document).ready(MeterRender.onLoad);
